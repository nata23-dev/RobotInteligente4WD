"""Contrato de máquina de estados futura."""
from enum import Enum


class Stage(str, Enum):
    UNAVAILABLE = 'Pendiente de implementación y validación'
    IDLE = 'Inactivo'
    FAULT = 'Falla'
