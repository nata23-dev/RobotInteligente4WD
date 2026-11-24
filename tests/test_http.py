import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
from urllib.parse import parse_qs
from app.config import defaults
from hardware.bridge import HTTPBridge
from hardware.protocol import APIError


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        calls = self.calls
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): self.respond()
            def do_POST(self): self.respond()
            def respond(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode()
                calls.append((self.command, self.path, dict(self.headers), parse_qs(body)))
                status = 403 if self.path.endswith('/state') else 200
                data = {'ok': False, 'error': 'unauthorized'} if status == 403 else {'ok': True}
                payload = json.dumps(data).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        config = defaults()
        config.update(robot_url=f'http://127.0.0.1:{self.server.server_port}', api_key='fixture-test-no-secreto')
        self.bridge = HTTPBridge(config)

    def tearDown(self):
        self.bridge.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def test_drive_form_post_auth_and_no_query(self):
        p = {'session': 123, 'seq': 1, 'fl': -1, 'fr': 1, 'rl': -1, 'rr': 1, 'ms': 150}
        self.bridge.request('drive', p)
        method, path, headers, form = self.calls[0]
        self.assertEqual((method, path), ('POST', '/api/drive'))
        self.assertEqual(headers['X-Robot-Key'], 'fixture-test-no-secreto')
        self.assertEqual(headers['Content-Type'], 'application/x-www-form-urlencoded')
        self.assertEqual(form, {k: [str(v)] for k, v in p.items()})

    def test_public_health_and_stop(self):
        self.bridge.request('health')
        self.bridge.request('stop')
        self.assertEqual(self.calls[0][0:2], ('GET', '/api/health'))
        self.assertEqual(self.calls[1][0:2], ('POST', '/api/stop'))
        self.assertNotIn('X-Robot-Key', self.calls[1][2])

    def test_http_error_not_retried(self):
        with self.assertRaises(APIError) as ctx: self.bridge.request('state')
        self.assertEqual(ctx.exception.status, 403)
        self.assertEqual(len(self.calls), 1)

    def test_servo_and_release_forms(self):
        for action, p, path in [('enable', {'nombre': 'base', 'session': 3, 'seq': 2}, '/api/servo/enable'),
                                ('servo', {'nombre': 'garra', 'grado': 35, 'session': 3, 'seq': 3}, '/api/servo'),
                                ('release', {'nombre': 'base', 'confirm': 1}, '/api/release'),
                                ('arm', {'challenge': 99}, '/api/arm'),
                                ('heartbeat', {'session': 3, 'seq': 4}, '/api/heartbeat')]:
            self.bridge.request(action, p)
            self.assertEqual(self.calls[-1][0:2], ('POST', path))

    def test_invalid_never_sent(self):
        with self.assertRaises(ValueError): self.bridge.request('drive', {})
        self.assertEqual(self.calls, [])
