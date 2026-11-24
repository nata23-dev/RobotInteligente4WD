"""Contrato de CNN futura; no carga TensorFlow durante la fase 01."""
from typing import Protocol
from app.models import Observation, Frame


class Classifier(Protocol):
    def predict(self, frame: Frame) -> Observation: ...


class PendingClassifier:
    available = False

    def predict(self, frame: Frame) -> Observation:
        raise NotImplementedError('CNN pendiente de entrenamiento y validación')
