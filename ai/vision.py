"""Infraestructura de percepción, sin detección ni navegación autónoma en fase 01."""
import queue
from typing import Protocol
from app.models import Frame, Observation


class Vision(Protocol):
    def process(self, frame: Frame) -> Observation: ...


class LatestObservation:
    """Buzón acotado para el trabajador de percepción de la fase siguiente."""
    def __init__(self):
        self.queue = queue.Queue(maxsize=1)

    def publish(self, observation):
        try:
            self.queue.get_nowait()
        except queue.Empty:
            pass
        self.queue.put_nowait(observation)
