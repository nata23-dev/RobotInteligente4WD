"""Preferencias exclusivamente visuales; no alteran el contrato JSON de control."""

import json
from pathlib import Path
from app.config import ROOT, integer

PATH = ROOT / "ui.local.json"


def load_goal(path=PATH):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))["images_per_class"]
        integer(value, 1, 100000, "Meta de imágenes")
        return value
    except (OSError, ValueError, KeyError, TypeError):
        return 150


def save_goal(value, path=PATH):
    integer(value, 1, 100000, "Meta de imágenes")
    target = Path(path)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps({"images_per_class": value}) + "\n", encoding="utf-8")
    temp.replace(target)
