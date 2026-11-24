"""Contratos compartidos; ningún valor desconocido se presenta como medición."""
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass(frozen=True)
class Frame:
    id: int
    received_at: float
    image: np.ndarray = field(repr=False, compare=False)
    fps: float = 0.0


@dataclass(frozen=True)
class Observation:
    frame_id: int | None = None
    shape: str | None = None
    color: str | None = None
    confidence: float | None = None
    alignment_error: float | None = None
    proximity: float | None = None
    stage: str = 'Pendiente de implementación'


@dataclass(frozen=True)
class Command:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    owner: str = 'manual'
