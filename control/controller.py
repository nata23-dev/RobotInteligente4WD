"""Arbitraje de modos; autonomía bloqueada durante fase 01."""
from app.models import Command


class Controller:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def tick(self):
        # Solo la aplicación principal sana puede renovar esta autorización temporal.
        self.dispatcher.safety.touch()

    def change_mode(self, mode):
        if mode not in ('manual', 'dataset', 'automatico'):
            raise ValueError('Modo desconocido')
        if mode != self.dispatcher.safety.mode:
            if self.dispatcher.safety.connected or self.dispatcher.safety.session or self.dispatcher.active:
                self.dispatcher.stop('Cambio de modo')
            else:
                self.dispatcher.safety.invalidate('Cambio de modo / desarmado')
            with self.dispatcher.safety.lock:
                self.dispatcher.safety.mode = mode

    def start_autonomous(self):
        raise NotImplementedError('Autonomía pendiente de implementación y validación')

    def drive(self, directions, ms):
        return self.dispatcher.submit(Command('drive', dict(zip(('fl', 'fr', 'rl', 'rr'), directions)) | {'ms': ms}))
