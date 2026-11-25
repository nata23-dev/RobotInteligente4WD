"""Catálogo privado; perfiles experimentales, sin promesa de calibración física."""

import copy
import json
from pathlib import Path
from app.config import ROOT
from app import vision_config

LOCAL = ROOT / "vision_profiles.local.json"
TUNING = (
    "hsv",
    "interval_meta",
    "digital",
    "filters",
    "search_roi",
    "tracking",
    "open_kernel",
    "close_kernel",
    "min_area",
    "max_area_ratio",
    "tracking_radius",
    "lost_frames",
    "crop_margin",
)


def expanded(base):
    v = copy.deepcopy(base)
    v["hsv"] = {
        "rojo": [[0, 55, 35, 15, 255, 255], [165, 55, 35, 179, 255, 255]],
        "verde": [[35, 45, 35, 89, 255, 255]],
        "azul": [[90, 45, 35, 135, 255, 255]],
    }
    v["interval_meta"] = vision_config.defaults()["interval_meta"]
    v["tracking"]["confirm_frames"] = 3
    v["profile_name"] = "Ampliado experimental"
    return v


class Profiles:
    def __init__(self, original, path=LOCAL):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {
                "Original": {
                    "protected": True,
                    "tuning": {k: copy.deepcopy(original[k]) for k in TUNING},
                },
                "Ampliado experimental": {
                    "protected": True,
                    "tuning": {k: copy.deepcopy(expanded(original)[k]) for k in TUNING},
                },
            }
        for name in self.data:
            self.select(name, original)

    def select(self, name, base):
        if name not in self.data:
            raise ValueError("Perfil inexistente")
        result = copy.deepcopy(base)
        result.update(copy.deepcopy(self.data[name]["tuning"]))
        result["profile_name"] = name
        vision_config.validate(result, vision_config.dataset_defaults())
        return result

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.path)

    def put(self, name, vision):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64:
            raise ValueError("Nombre de perfil requerido (1–64)")
        if name in self.data and self.data[name]["protected"]:
            raise ValueError(
                "El perfil original/experimental protegido no se sobrescribe; duplíquelo"
            )
        vision_config.validate(vision, vision_config.dataset_defaults())
        self.data[name] = {
            "protected": False,
            "tuning": {k: copy.deepcopy(vision[k]) for k in TUNING},
        }
        self.save()

    def delete(self, name):
        if name not in self.data or self.data[name]["protected"]:
            raise ValueError("No se elimina un perfil protegido")
        del self.data[name]
        self.save()

    def rename(self, old, new):
        if (
            old not in self.data
            or self.data[old]["protected"]
            or new in self.data
            or not isinstance(new, str)
            or not 1 <= len(new.strip()) <= 64
        ):
            raise ValueError("Renombrado de perfil inválido")
        self.data[new] = self.data.pop(old)
        self.save()
