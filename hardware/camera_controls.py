"""Adaptación conservadora: ningún endpoint del equipo instalado está confirmado."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    name: str
    verified: bool = False
    evidence: str = 'Pendiente de verificar con cámara real y fuente instalada'


class CameraControls:
    def capabilities(self):
        return tuple(Capability(name) for name in ('resolution','jpeg_quality','brightness','contrast','saturation','exposure','white_balance','sharpness','focus'))

    def apply(self, name, value):
        raise NotImplementedError('Ajustes remotos bloqueados: no se ha verificado el firmware de ESP32-CAM')
