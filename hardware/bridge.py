"""Transporte HTTP sin reintentos ni redirecciones de órdenes."""

from collections import deque
from time import monotonic
import threading
import requests
import numpy as np
from hardware.protocol import APIError, ROUTES, validate_command
from hardware.telemetry import RecentRequests, error_kind


class HTTPBridge:
    def __init__(self, config, purpose="control"):
        self.url = config["robot_url"].rstrip("/")
        self.key = config["api_key"]
        self.timeout = config["timeout_s"]
        self.purpose = purpose
        self.timeouts = (
            (min(self.timeout, 0.3), 1.0)
            if purpose == "recovery"
            else (
                (min(self.timeout, 0.15), min(self.timeout, 0.15))
                if purpose == "heartbeat"
                else (self.timeout, self.timeout)
            )
        )
        self.telemetry = RecentRequests()
        self.session = requests.Session()
        self.session.trust_env = False
        self.samples = deque(maxlen=500)
        self.errors = 0
        self.metrics_lock = threading.Lock()

    def request(self, action, params=None):
        params = params or {}
        validate_command(action, params)
        if self.purpose in ("recovery", "diagnostic") and action not in (
            "health",
            "state",
        ):
            raise ValueError("Transporte de lectura: solo health/state")
        if not self.url:
            raise APIError("robot_url_required")
        if action not in ("health", "stop") and not self.key:
            raise APIError("api_key_required")
        method, path = ROUTES[action]
        headers = {"Accept": "application/json"}
        if action not in ("health", "stop"):
            headers["X-Robot-Key"] = self.key
        start = monotonic()
        ok, kind = False, None
        try:
            with self.session.request(
                method,
                self.url + path,
                headers=headers,
                data=params if method == "POST" else None,
                timeout=self.timeouts,
                allow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    # Nunca incluir URL, clave, cuerpo ni excepciones requests en logs.
                    try:
                        payload = response.json()
                        error = (
                            payload.get("error", "http_error")
                            if isinstance(payload, dict)
                            else "http_error"
                        )
                    except ValueError:
                        error = "non_json_error"
                    known = {
                        "unauthorized",
                        "actuators_busy",
                        "servo_not_enabled",
                        "not_armed",
                        "invalid_session",
                        "old_sequence",
                        "cannot_arm",
                        "invalid_challenge",
                        "stop_before_release",
                        "servo_attach_failed",
                    }
                    safe = (
                        error
                        if isinstance(error, str) and error in known
                        else "http_error"
                    )
                    raise APIError(safe, response.status_code)
                try:
                    result = response.json()
                except ValueError as exc:
                    raise APIError("invalid_json") from exc
                if not isinstance(result, dict) or result.get("ok") is not True:
                    raise APIError("invalid_response")
                ok = True
                return result
        except requests.RequestException as exc:
            with self.metrics_lock:
                self.errors += 1
            kind = (
                "connect_timeout"
                if isinstance(exc, requests.ConnectTimeout)
                else (
                    "read_timeout"
                    if isinstance(exc, requests.ReadTimeout)
                    else (
                        "connection"
                        if isinstance(exc, requests.ConnectionError)
                        else "transport"
                    )
                )
            )
            raise APIError("communication_lost", category=kind) from exc
        except APIError as exc:
            kind = error_kind(exc)
            with self.metrics_lock:
                self.errors += 1
            raise
        finally:
            self.telemetry.record(start, ok, kind)
            with self.metrics_lock:
                self.samples.append((monotonic() - start) * 1000)

    def metrics(self):
        return self.telemetry.snapshot()

    def close(self):
        self.session.close()
