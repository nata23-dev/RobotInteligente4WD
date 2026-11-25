"""Comunicaciones con simulador/mocks y HTTP loopback; nunca hardware físico."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import requests
from app.config import defaults
from app.application import Application
from app.models import Command
from control.command_dispatcher import Dispatcher
from control.communication import RETRY_DELAYS
from hardware.bridge import HTTPBridge
from hardware.protocol import APIError
from hardware.simulator import Simulator
from hardware.telemetry import RecentRequests
from scripts.diagnose_communications import diagnose, local_address
from tests.test_dispatcher import until


class FaultBridge:
    def __init__(self, sim):
        self.sim = sim
        self.down = False
        self.failures = {}
        self.block = {}
        self.calls = []
        self.closed = 0

    def request(self, action, params=None):
        self.calls.append(action)
        if self.down or self.failures.get(action, 0):
            self.failures[action] = max(0, self.failures.get(action, 0) - 1)
            raise APIError("communication_lost", category="connection")
        if action in self.block:
            entered, release = self.block[action]
            entered.set()
            release.wait(2)
        return self.sim.request(action, params)

    def close(self):
        self.closed += 1


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulator()
        self.bridge = FaultBridge(self.sim)
        self.reader = FaultBridge(self.sim)
        self.d = Dispatcher(self.bridge, self.sim, defaults(), self.reader)
        self.d.safety.mode = "manual"
        self.d.safety.touch()

    def tearDown(self):
        self.d.close()

    def verify(self):
        return self.d._execute(self.d.safety.generation, Command("verify"))

    def disconnect(self):
        self.d._failure(APIError("communication_lost"))
        if self.d.stop_thread:
            self.d.stop_thread.join(1)

    def recover(self):
        self.d.next_retry = 0
        self.d._recover()

    def test_no_startup_probes_and_initial_states(self):
        self.d._recover()
        self.assertEqual(self.bridge.calls, [])
        self.assertEqual(self.reader.calls, [])
        self.assertEqual(self.d.communication_snapshot()["state"], "Sin verificar")
        self.assertEqual(self.d.communication_snapshot()["remote_state"], "Desconocido")

    def test_worker_automatically_recovers_without_operator_or_extra_worker(self):
        self.d.start()
        self.d.submit(Command("verify")).result(1)
        worker = self.d.worker
        self.bridge.failures["state"] = 1
        until(lambda: self.d.communication_snapshot()["reconnections"] == 1, timeout=3)
        self.assertTrue(self.d.safety.connected)
        self.assertFalse(self.d.safety.session)
        self.assertIs(self.d.worker, worker)
        self.assertNotIn("arm", self.bridge.calls + self.reader.calls)

    def test_isolated_failure_recovers_disarmed_without_rearm(self):
        self.verify()
        self.disconnect()
        self.assertFalse(self.d.safety.connected)
        self.assertFalse(self.d.safety.session)
        self.recover()
        self.assertTrue(self.d.safety.connected)
        self.assertFalse(self.d.safety.session)
        self.assertEqual(self.reader.calls, ["health", "state"])
        self.assertEqual(self.d.communication_snapshot()["reconnections"], 1)
        self.assertNotIn("arm", self.bridge.calls + self.reader.calls)
        self.assertFalse(self.sim.armed)
        self.d.safety.touch()
        self.d._execute(self.d.safety.generation, Command("arm"))
        self.assertTrue(self.d.safety.session)  # Solo un armado explícito nuevo.

    def test_backoff_consecutive_failures_bounded_no_queue(self):
        self.assertEqual(RETRY_DELAYS, (0.5, 1.0, 2.0, 3.0))
        self.verify()
        self.reader.down = True
        self.disconnect()
        for expected in (1.0, 2.0, 3.0, 3.0):
            self.recover()
            if self.d.stop_thread:
                self.d.stop_thread.join(1)
            remaining = self.d.next_retry - time.monotonic()
            self.assertGreater(remaining, expected - 0.2)
            self.assertLessEqual(remaining, expected)
            self.assertTrue(self.d.queue.empty())
        before = len(self.reader.calls)
        for _ in range(100):
            self.d._recover()
        self.assertEqual(len(self.reader.calls), before)
        self.reader.down = False
        self.recover()
        self.assertTrue(self.d.safety.connected)

    def test_armed_firmware_after_reconnect_requests_stop(self):
        self.verify()
        self.disconnect()
        self.sim.armed = True
        self.sim.session = 19
        self.sim.heartbeat_at = time.monotonic()
        self.recover()
        self.assertFalse(self.d.safety.connected)
        self.d.stop_thread.join(1)
        self.assertFalse(self.sim.armed)
        self.recover()
        self.assertTrue(self.d.safety.connected)
        self.assertFalse(self.d.safety.session)
        self.assertNotIn("arm", self.reader.calls)

    def test_stop_unconfirmed_keeps_remote_unknown(self):
        self.verify()
        self.sim.online = False
        self.disconnect()
        self.assertFalse(self.d.safety.connected)
        self.assertEqual(self.d.communication_snapshot()["stop_state"], "No confirmado")
        self.assertEqual(self.d.communication_snapshot()["remote_state"], "Desconocido")
        self.recover()
        self.assertFalse(self.d.safety.session)
        self.assertFalse(self.d.safety.connected)

    def test_failure_armed_invalidates_pending_no_movement_replay(self):
        self.verify()
        self.d._execute(self.d.safety.generation, Command("arm"))
        futures = [
            self.d.submit(Command("drive", dict(fl=1, fr=1, rl=1, rr=1, ms=150)))
            for _ in range(3)
        ]
        self.disconnect()
        self.assertFalse(self.d.safety.session)
        self.assertTrue(all(f.cancelled() for f in futures))
        self.recover()
        self.assertFalse(self.d.safety.session)
        self.assertFalse(self.sim.armed)
        self.assertNotIn("drive", self.bridge.calls + self.reader.calls)

    def test_slow_state_is_not_fresh_at_receipt(self):
        original = self.reader.request

        def slow(action, params=None):
            if action == "state":
                time.sleep(0.78)
            return original(action, params)

        self.d.recovery_enabled = True
        with patch.object(self.reader, "request", slow):
            self.recover()
        self.assertFalse(self.d.safety.connected)
        self.assertEqual(
            self.d.communication_snapshot()["last_failure"], "stale_response"
        )

    def test_read_timestamp_is_request_start(self):
        original = self.bridge.request
        observed = []

        def delay(action, params=None):
            if action == "state":
                observed.append(time.monotonic())
                time.sleep(0.08)
                observed.append(time.monotonic())
            return original(action, params)

        with patch.object(self.bridge, "request", delay):
            self.verify()
        self.assertLessEqual(self.d.state_confirmed_at, observed[0])
        self.assertLess(self.d.state_confirmed_at, observed[1])

    def test_late_health_response_after_generation_change_discarded(self):
        entered = threading.Event()
        release = threading.Event()
        errors = []
        self.reader.block["health"] = (entered, release)
        gen = self.d.safety.generation

        def run():
            try:
                self.d._verify(gen, True)
            except PermissionError as exc:
                errors.append(type(exc).__name__)

        thread = threading.Thread(target=run)
        thread.start()
        self.assertTrue(entered.wait(1))
        self.d.suspend_recovery()
        release.set()
        thread.join(1)
        self.assertFalse(self.d.safety.connected)
        self.assertEqual(errors, ["PermissionError"])
        self.assertNotIn("state", self.reader.calls)
        self.d.next_retry = 0
        self.d._recover()
        self.assertEqual(self.reader.calls, ["health"])

    def test_invalid_auth_and_version_never_enable_motion(self):
        self.d.recovery_enabled = True
        with patch.object(
            self.reader, "request", side_effect=APIError("unauthorized", 403)
        ):
            self.recover()
        self.assertEqual(
            self.d.communication_snapshot()["last_failure"], "authentication"
        )
        if self.d.stop_thread:
            self.d.stop_thread.join(1)
        with patch.object(
            self.reader,
            "request",
            return_value={
                "ok": True,
                "firmware": "other",
                "version": "9",
                "api_version": 9,
            },
        ):
            self.recover()
        self.assertFalse(self.d.safety.connected)
        self.assertFalse(self.d.safety.session)
        self.assertEqual(self.d.communication_snapshot()["last_failure"], "protocol")

    def test_armed_loop_prioritizes_heartbeat_and_skips_telemetry(self):
        self.d.start()
        self.d.submit(Command("verify")).result(1)
        self.d.safety.touch()
        self.d.submit(Command("arm")).result(1)
        self.bridge.calls.clear()
        deadline = time.monotonic() + 0.82
        while time.monotonic() < deadline:
            self.d.safety.touch()
            time.sleep(0.02)
        self.assertGreaterEqual(self.bridge.calls.count("heartbeat"), 2)
        self.assertNotIn("state", self.bridge.calls)
        self.assertTrue(self.d.safety.session)

    def test_unconfirmed_heartbeat_deadline_stops_even_if_ui_healthy(self):
        self.d.start()
        self.d.submit(Command("verify")).result(1)
        self.d.safety.touch()
        self.d.submit(Command("arm")).result(1)
        entered = threading.Event()
        release = threading.Event()
        self.bridge.block["heartbeat"] = (entered, release)
        try:
            deadline = time.monotonic() + 1.2
            while self.d.safety.session and time.monotonic() < deadline:
                self.d.safety.touch()
                time.sleep(0.02)
            self.assertFalse(self.d.safety.session)
            until(lambda: not self.sim.armed, timeout=0.5)
        finally:
            release.set()

    def test_read_wait_does_not_block_prioritized_stop(self):
        self.verify()
        self.disconnect()
        entered = threading.Event()
        release = threading.Event()
        self.reader.block["state"] = (entered, release)
        self.d.next_retry = 0
        thread = threading.Thread(target=self.d._recover)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            start = time.monotonic()
            self.d.stop()
            self.d.stop_thread.join(0.4)
            self.assertFalse(self.d.stop_thread.is_alive())
            self.assertLess(time.monotonic() - start, 0.4)
        finally:
            release.set()
            thread.join(1)
        self.assertFalse(self.d.safety.connected)

    def test_close_during_reconnection_no_duplicate_worker(self):
        self.verify()
        self.disconnect()
        self.d.retry_delays = (0.01, 0.02, 0.03, 0.03)
        entered = threading.Event()
        release = threading.Event()
        self.reader.block["health"] = (entered, release)
        self.d.next_retry = 0
        self.d.start()
        self.assertTrue(entered.wait(1))
        worker = self.d.worker
        closer = threading.Thread(target=self.d.close)
        closer.start()
        until(self.d.closed.is_set)
        release.set()
        closer.join(2)
        self.assertFalse(closer.is_alive())
        self.assertFalse(worker.is_alive())
        self.assertIs(worker, self.d.worker)
        self.assertFalse(self.d.safety.session)
        self.assertNotIn("state", self.reader.calls)


class MetricsAndProfilesTests(unittest.TestCase):
    def test_unexpected_worker_failure_latches_closed_without_sensitive_log(self):
        sim = Simulator()
        bridge = FaultBridge(sim)
        d = Dispatcher(bridge, sim, defaults())
        d.safety.connected = True
        d.recovery_enabled = True
        try:
            with patch.object(
                bridge, "request", side_effect=RuntimeError("fixture-private-header")
            ), self.assertLogs("control.command_dispatcher", level="ERROR") as logs:
                d.start()
                until(d.closed.is_set)
            self.assertFalse(d.safety.connected)
            self.assertFalse(d.safety.session)
            self.assertEqual(d.communication_snapshot()["remote_state"], "Desconocido")
            self.assertNotIn("fixture-private-header", " ".join(logs.output))
        finally:
            d.close()

    def test_http_error_body_is_not_exposed_or_trusted(self):
        c = defaults()
        c.update(robot_url="http://127.0.0.1:1", api_key="fixture-sin-valor-real")
        bridge = HTTPBridge(c)

        class Response:
            status_code = 503
            payload = None

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def json(self):
                return self.payload

        response = Response()
        try:
            for payload in (
                {"error": "fixture-secreto-del-servidor"},
                {"error": ["objeto", "inesperado"]},
                ["error"],
            ):
                response.payload = payload
                with patch.object(
                    bridge.session, "request", return_value=response
                ), self.assertRaises(APIError) as caught:
                    bridge.request("state")
                self.assertEqual(caught.exception.error, "http_error")
                self.assertNotIn("fixture-secreto", str(caught.exception))
        finally:
            bridge.close()

    def test_timeout_roles_readonly_and_private_config_unchanged(self):
        c = defaults()
        c.update(timeout_s=0.3, robot_url="http://127.0.0.1:1")
        original = c.copy()
        profiles = {
            role: HTTPBridge(c, role)
            for role in ("control", "stop", "heartbeat", "recovery", "diagnostic")
        }
        try:
            self.assertEqual(profiles["control"].timeouts, (0.3, 0.3))
            self.assertEqual(profiles["stop"].timeouts, (0.3, 0.3))
            self.assertEqual(profiles["heartbeat"].timeouts, (0.15, 0.15))
            self.assertEqual(profiles["recovery"].timeouts, (0.3, 1.0))
            with self.assertRaises(ValueError):
                profiles["recovery"].request("stop")
            self.assertEqual(c, original)
        finally:
            for bridge in profiles.values():
                bridge.close()

    def test_recent_window_errors_and_consecutive_reset(self):
        m = RecentRequests(window_s=60)
        with patch("hardware.telemetry.time.monotonic", return_value=100):
            m.record(99.9, False, "read_timeout")
            self.assertEqual(m.snapshot()["consecutive_errors"], 1)
        with patch("hardware.telemetry.time.monotonic", return_value=101):
            m.record(100.9, True)
        with patch("hardware.telemetry.time.monotonic", return_value=162):
            result = m.snapshot()
            self.assertEqual(result["errors"], 0)
            self.assertIsNone(result["p95"])
            self.assertEqual(result["failure_total"], 1)
            self.assertEqual(result["consecutive_errors"], 0)

    def test_transport_error_categories_sanitized(self):
        c = defaults()
        c.update(robot_url="http://127.0.0.1:1234", api_key="fixture-prueba-sin-valor")
        b = HTTPBridge(c)
        try:
            for exc, kind in [
                (requests.ConnectTimeout("secret-header"), "connect_timeout"),
                (requests.ReadTimeout("secret-header"), "read_timeout"),
                (requests.ConnectionError("secret-header"), "connection"),
            ]:
                with patch.object(
                    b.session, "request", side_effect=exc
                ), self.assertRaises(APIError) as caught:
                    b.request("state")
                self.assertEqual(caught.exception.category, kind)
                self.assertNotIn("secret-header", str(caught.exception))
            self.assertEqual(b.metrics()["errors"], 3)
        finally:
            b.close()


class LoopbackDiagnosticTests(unittest.TestCase):
    def test_cli_health_writes_json_and_keeps_credentials_private(self):
        import io
        import contextlib
        from scripts import diagnose_communications as cli

        headers = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                headers.append(self.headers.get("X-Robot-Key"))
                data = json.dumps(
                    {
                        "ok": True,
                        "firmware": "Robot4WD",
                        "version": "1.0.0",
                        "api_version": 1,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "diagnostico.json"
                c = defaults()
                c["api_key"] = "fixture-sin-valor-real"
                output = io.StringIO()
                args = [
                    "diagnose_communications.py",
                    "--address",
                    f"http://127.0.0.1:{server.server_port}",
                    "--count",
                    "2",
                    "--interval",
                    ".05",
                    "--endpoint",
                    "health",
                    "--output",
                    str(target),
                ]
                with patch.object(cli, "load", return_value=c), patch(
                    "sys.argv", args
                ), contextlib.redirect_stdout(output):
                    cli.main()
                data = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(data["summary"]["success_total"], 2)
                self.assertEqual(headers, [None, None])
                self.assertNotIn(
                    c["api_key"], target.read_text(encoding="utf-8") + output.getvalue()
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_200_queries_three_nonconsecutive_errors_and_recovery(self):
        sim = Simulator()
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                calls.append(self.path)
                index = len(calls)
                if index in (1, 44, 73):
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                payload = json.dumps(sim.request("state")).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        class NoWait:
            def is_set(self):
                return False

            def wait(self, seconds):
                return False

        try:
            c = defaults()
            c["api_key"] = "fixture-prueba-sin-valor"
            report = diagnose(
                c,
                f"http://127.0.0.1:{server.server_port}",
                200,
                0.05,
                0.3,
                "state",
                NoWait(),
            )
            self.assertEqual(len(calls), 200)
            self.assertEqual(
                [r["query"] for r in report["results"] if not r["ok"]], [1, 44, 73]
            )
            self.assertEqual(report["summary"]["success_total"], 197)
            self.assertEqual(report["summary"]["failure_total"], 3)
            self.assertEqual(len(report["outages_s"]), 3)
            self.assertTrue(all(report["results"][i]["ok"] for i in (1, 44, 73)))
            encoded = json.dumps(report)
            self.assertNotIn(c["api_key"], encoded)
            self.assertNotIn("X-Robot-Key", encoded)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_diagnostic_rejects_public_target_and_mutations(self):
        for address in (
            "https://127.0.0.1",
            "http://8.8.8.8",
            "http://user:pass@127.0.0.1",
            "http://127.0.0.1/api/arm",
        ):
            with self.assertRaises(ValueError):
                local_address(address)
        with self.assertRaises(ValueError):
            diagnose(defaults(), "127.0.0.1", 1, 0.1, 0.3, "arm")


class ApplicationRecoveryTests(unittest.TestCase):
    def test_export_saves_sanitized_communication_diagnostics(self):
        c = defaults()
        c["api_key"] = "fixture-credencial-no-publicar"
        with patch("app.application.load", return_value=c):
            app = Application(True)
        try:
            with tempfile.TemporaryDirectory() as directory, patch(
                "app.application.ROOT", Path(directory)
            ):
                app.export_logs()
                until(lambda: bool(list(Path(directory).rglob("comunicaciones.json"))))
                target = next(Path(directory).rglob("comunicaciones.json"))
                # Esperar el evento de finalización, no solo la creación del archivo.
                until(
                    lambda: any(
                        kind == "info" and "Registros exportados" in str(payload)
                        for kind, payload in list(app.events.queue)
                    )
                )
                data = target.read_text(encoding="utf-8")
                report = json.loads(data)
                self.assertIn("reconnections", report)
                self.assertIn("stop_state", report)
                self.assertNotIn(c["api_key"], data)
                self.assertNotIn("X-Robot-Key", data)
        finally:
            app.close()

    def test_control_outage_keeps_fresh_camera_and_recovery_disarmed(self):
        import gc
        from app.models import Frame
        from ui.main_window import MainWindow
        from tests.vision_fixtures import scene
        from tests.test_ui_redesign import pump

        gc.collect()
        with tempfile.TemporaryDirectory() as directory:
            c = defaults()
            c["dataset_dir"] = directory
            with patch("app.application.load", return_value=c):
                app = Application(True)
            window = MainWindow(app)
            try:
                app.dispatcher.submit(Command("verify")).result(1)
                app.dispatcher._failure(APIError("communication_lost"))
                if app.dispatcher.stop_thread:
                    app.dispatcher.stop_thread.join(1)
                app.camera.latest = Frame(
                    1, time.monotonic(), scene(), 12, "fixture_comms", "fixture_prueba"
                )
                window.auto.update_video(app.camera.snapshot())
                self.assertIsNotNone(window.auto.video.photo)
                self.assertFalse(app.dispatcher.safety.connected)
                app.dispatcher.next_retry = 0
                app.dispatcher._recover()
                self.assertTrue(app.dispatcher.safety.connected)
                self.assertFalse(app.dispatcher.safety.session)
                app.camera.latest = Frame(
                    2, time.monotonic(), scene(), 12, "fixture_comms", "fixture_prueba"
                )
                window.auto.update_video(app.camera.snapshot())
                self.assertIsNotNone(window.auto.video.photo)
            finally:
                app.close()
                window.destroy()
                gc.collect()

    def test_reconfigure_cancels_old_recovery_and_capture_remains_blocked(self):
        with patch("app.application.load", return_value=defaults()):
            app = Application(True)
        old = app.dispatcher
        reader = FaultBridge(old.bridge)
        old.recovery_bridge = reader
        entered = threading.Event()
        release = threading.Event()
        try:
            old.submit(Command("verify")).result(1)
            old._failure(APIError("communication_lost"))
            if old.stop_thread:
                old.stop_thread.join(1)
            reader.block["health"] = (entered, release)
            old.next_retry = 0
            self.assertTrue(entered.wait(1))
            app.config["simulation"] = False
            with self.assertRaises(PermissionError):
                app.capture_guard()
            app.config["simulation"] = True
            with patch("app.application.save"):
                app.update_config(defaults())
                self.assertTrue(old.recovery_suspended.is_set())
                release.set()
                until(lambda: not app.reconfiguring)
            self.assertIsNot(app.dispatcher, old)
            self.assertFalse(old.worker.is_alive())
            self.assertFalse(app.dispatcher.safety.connected)
            self.assertFalse(app.dispatcher.safety.session)
            self.assertFalse(app.dispatcher.recovery_enabled)
            self.assertNotIn("state", reader.calls)
        finally:
            release.set()
            app.close()
