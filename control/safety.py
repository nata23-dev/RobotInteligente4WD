"""Autorización local enclavada; el firmware conserva su propia autoridad."""
import threading
import time


class Safety:
    def __init__(self):
        self.lock = threading.RLock()
        self.connected = False
        self.session = 0
        self.generation = 0
        self.mode = 'automatico'
        self.status = 'Desarmado / conexión sin verificar'
        self.controller_at = 0.

    def touch(self):
        with self.lock:
            self.controller_at = time.monotonic()

    def invalidate(self, status):
        with self.lock:
            self.generation += 1
            self.session = 0
            self.status = status

    def require(self, owner, generation):
        if (not self.connected or not self.session or generation != self.generation
                or owner != self.mode or owner != 'manual'):
            raise PermissionError('Orden bloqueada: conexión, sesión o propietario no autorizado')

    def snapshot(self):
        with self.lock:
            return {'connected': self.connected, 'session_authorized': bool(self.session),
                    'generation': self.generation, 'mode': self.mode, 'safety': self.status}
