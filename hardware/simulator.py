"""Modelo local de API 1. No representa sensores ni resultados físicos."""
import math
import secrets
import threading
import time
from hardware.protocol import APIError, SEQUENCED, validate_command


class Simulator:
    def __init__(self, key='simulacion-local', clock=time.monotonic):
        self.key, self.clock = key, clock
        self.lock = threading.RLock()
        self.online = True
        self.armed = False
        self.maintenance = False
        self.challenge = self._token()
        self.session = self.seq = 0
        self.reason = 'boot'
        self.heartbeat_at = 0.0
        self.motor_until = 0.0
        self.motor_stopped = clock() - 1
        self.directions = [0] * 4
        self.angle = {'garra': 60, 'base': 75}
        self.target = self.angle.copy()
        self.attached = {'garra': False, 'base': False}
        self.settle_until = {'garra': 0., 'base': 0.}
        self.last_step = clock()
        self.history = []
        self.samples = []
        self.errors = 0

    @staticmethod
    def _token():
        return secrets.randbelow(0xfffffffe) + 1

    def _stop(self, reason):
        if self.motor_until:
            self.motor_stopped = self.clock()
        self.motor_until = 0
        self.directions = [0] * 4
        self.target = self.angle.copy()
        self.armed = False
        self.session = self.seq = 0
        previous = self.challenge
        while self.challenge == previous:
            self.challenge = self._token()
        self.reason = reason

    def _tick(self):
        now = self.clock()
        if self.motor_until and now >= self.motor_until:
            self.motor_stopped = self.motor_until
            self.motor_until = 0
            self.directions = [0] * 4
        if self.armed and now - self.heartbeat_at >= 1.2:
            self._stop('heartbeat_timeout')
        if self.armed and not self.motor_until:
            steps = int((now - self.last_step + 1e-9) / .065)
            if steps:
                first = self.last_step + .065
                for name in self.angle:
                    eligible = max(first, self.settle_until[name])
                    count = max(0, int((now - eligible + 1e-9) / .065) + 1)
                    delta = self.target[name] - self.angle[name]
                    if self.attached[name] and delta and count:
                        needed = math.ceil(abs(delta) / 2)
                        self.angle[name] += (1 if delta > 0 else -1) * min(abs(delta), count * 2)
                        if count >= needed:
                            self.settle_until[name] = eligible + (needed - 1) * .065 + .2
                self.last_step = now

    def busy(self):
        return any(self.attached[n] and (self.angle[n] != self.target[n] or
                   self.clock() < self.settle_until[n]) for n in self.angle)

    def _state(self):
        return {'ok': True, 'api_version': 1, 'armed': self.armed,
                'maintenance': self.maintenance, 'reason': self.reason,
                'challenge': self.challenge, 'last_seq': self.seq,
                'motor_activo': bool(self.motor_until), 'directions': self.directions.copy(),
                'motor_remaining_ms': max(0, int((self.motor_until - self.clock()) * 1000)),
                'garra': self.angle['garra'], 'base': self.angle['base'],
                'garra_objetivo': self.target['garra'], 'base_objetivo': self.target['base'],
                'servo_garra_activo': self.attached['garra'], 'servo_base_activo': self.attached['base'],
                'brazo_ocupado': self.busy(), 'sta_connected': True,
                'sta_ip': 'SIMULACIÓN', 'diag_ip': 'SIMULACIÓN',
                'heartbeat_remaining_ms': max(0, int((1.2 - self.clock() + self.heartbeat_at) * 1000)) if self.armed else 0}

    def request(self, action, params=None, key=None):
        start = time.monotonic()
        try:
            with self.lock:
                if not self.online:
                    self.errors += 1
                    raise APIError('communication_lost')
                p = params or {}
                self._tick()
                if action not in ('health', 'stop') and (self.key if key is None else key) != self.key:
                    raise APIError('unauthorized', 403)
                try:
                    validate_command(action, p)
                except ValueError as exc:
                    raise APIError('invalid_parameters', 400) from exc
                self.history.append((action, p.copy()))
                self.history = self.history[-1000:]
                if action == 'health':
                    return {'ok': True, 'firmware': 'Robot4WD', 'version': '1.0.0', 'api_version': 1, 'sta_connected': True}
                if action == 'state':
                    return self._state()
                if action == 'stop':
                    self._stop('stop_requested')
                    return {'ok': True, 'armed': False}
                if action == 'arm':
                    if self.armed or self.maintenance or self.motor_until:
                        raise APIError('cannot_arm', 409)
                    if p['challenge'] != self.challenge:
                        raise APIError('invalid_challenge', 409)
                    self.armed = True
                    self.session = self._token()
                    self.challenge = self._token()
                    self.seq = 0
                    self.heartbeat_at = self.clock()
                    self.reason = 'armed'
                    return {'ok': True, 'session': self.session, 'lease_ms': 1200}
                if action == 'release':
                    if self.armed or self.motor_until or self.maintenance:
                        raise APIError('stop_before_release', 409)
                    n = p['nombre']
                    self.attached[n] = False
                    self.target[n] = self.angle[n]
                    self.settle_until[n] = 0
                    return {'ok': True}
                if action in SEQUENCED:
                    if not self.armed or self.maintenance:
                        raise APIError('not_armed', 409)
                    if p['session'] != self.session:
                        raise APIError('invalid_session', 409)
                    if p['seq'] <= self.seq:
                        raise APIError('old_sequence', 409)
                    self.seq = p['seq']  # Interlocks también consumen secuencia.
                if action == 'heartbeat':
                    self.heartbeat_at = self.clock()
                elif action == 'drive':
                    if self.motor_until or self.busy() or self.clock() - self.motor_stopped < .05:
                        raise APIError('actuators_busy', 409)
                    self.directions = [p[k] for k in ('fl', 'fr', 'rl', 'rr')]
                    self.motor_until = self.clock() + p['ms'] / 1000
                elif action == 'enable':
                    n = p['nombre']
                    if not self.attached[n]:
                        if self.motor_until or self.busy():
                            raise APIError('actuators_busy', 409)
                        self.attached[n] = True
                        self.angle[n] = self.target[n] = 60 if n == 'garra' else 75
                        self.settle_until[n] = self.clock() + .8
                elif action == 'servo':
                    n = p['nombre']
                    if not self.attached[n]:
                        raise APIError('servo_not_enabled', 409)
                    if self.motor_until or self.busy():
                        raise APIError('actuators_busy', 409)
                    self.target[n] = p['grado']
                    self.last_step = self.clock()
                return {'ok': True}
        finally:
            with self.lock:
                self.samples.append((time.monotonic() - start) * 1000)
                self.samples = self.samples[-500:]

    def metrics(self):
        import numpy as np
        with self.lock:
            v = self.samples.copy()
            return {'p50': float(np.percentile(v, 50)) if v else None,
                    'p95': float(np.percentile(v, 95)) if v else None,
                    'last': v[-1] if v else None, 'errors': self.errors}

    def close(self):
        pass
