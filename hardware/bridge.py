"""Transporte HTTP sin reintentos ni redirecciones de órdenes."""
from collections import deque
from time import monotonic
import threading
import requests
import numpy as np
from hardware.protocol import APIError, ROUTES, validate_command


class HTTPBridge:
    def __init__(self, config):
        self.url = config['robot_url'].rstrip('/')
        self.key = config['api_key']
        self.timeout = config['timeout_s']
        self.session = requests.Session()
        self.session.trust_env = False
        self.samples = deque(maxlen=500)
        self.errors = 0
        self.metrics_lock = threading.Lock()

    def request(self, action, params=None):
        params = params or {}
        validate_command(action, params)
        if not self.url:
            raise APIError('robot_url_required')
        if action not in ('health', 'stop') and not self.key:
            raise APIError('api_key_required')
        method, path = ROUTES[action]
        headers = {'Accept': 'application/json'}
        if action not in ('health', 'stop'):
            headers['X-Robot-Key'] = self.key
        start = monotonic()
        try:
            with self.session.request(method, self.url + path, headers=headers,
                                      data=params if method == 'POST' else None,
                                      timeout=(self.timeout, self.timeout), allow_redirects=False) as response:
                if not 200 <= response.status_code < 300:
                    # Nunca incluir URL, clave, cuerpo ni excepciones requests en logs.
                    try:
                        error = response.json().get('error', 'http_error')
                    except ValueError:
                        error = 'non_json_error'
                    safe = error if isinstance(error, str) and error.replace('_', '').isalnum() else 'http_error'
                    raise APIError(safe, response.status_code)
                try:
                    result = response.json()
                except ValueError as exc:
                    raise APIError('invalid_json') from exc
                if not isinstance(result, dict) or result.get('ok') is not True:
                    raise APIError('invalid_response')
                return result
        except requests.RequestException as exc:
            with self.metrics_lock:
                self.errors += 1
            raise APIError('communication_lost') from exc
        except APIError:
            with self.metrics_lock:
                self.errors += 1
            raise
        finally:
            with self.metrics_lock:
                self.samples.append((monotonic() - start) * 1000)

    def metrics(self):
        with self.metrics_lock:
            values = list(self.samples)
            return {'p50': float(np.percentile(values, 50)) if values else None,
                    'p95': float(np.percentile(values, 95)) if values else None,
                    'last': values[-1] if values else None, 'errors': self.errors}

    def close(self):
        self.session.close()
