"""Interfaz para control difuso futuro; sin órdenes ficticias."""
from typing import Protocol
from app.models import Observation, Command


class FuzzyControl(Protocol):
    def decide(self, observation: Observation) -> Command: ...
