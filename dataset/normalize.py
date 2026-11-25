"""Derivados no destructivos, por archivo y transformación explícita/trazable."""

import copy
from datetime import datetime, timezone
import hashlib
import json
import time
import uuid
import cv2
from app.models import Frame
from ai.perception import Perception
from ai.transforms import crop_bounds
from dataset.capture import DatasetCapture
from dataset.storage import consistent, safe_path, commit
from dataset.tools import review


def records(root):
    path = safe_path(root, "metadata/normalizations.jsonl")
    items = (
        [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
        if path.exists()
        else []
    )
    decisions = safe_path(root, "metadata/reviews.json")
    states = (
        json.loads(decisions.read_text(encoding="utf-8")) if decisions.exists() else {}
    )
    for item in items:
        item["review"] = states.get(item["normalized"], {}).get(
            "state", item.get("review", "sin_revisar")
        )
    return items


def set_derivative_review(root, normalized, state):
    from dataset.tools import STATES

    if state not in STATES:
        raise ValueError("Revisión inválida")
    with consistent(root):
        if (
            not any(r["normalized"] == normalized for r in records(root))
            or not safe_path(root, normalized).is_file()
        ):
            raise ValueError("Derivado no registrado")
        path = safe_path(root, "metadata/reviews.json")
        states = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        states[normalized] = {
            "state": state,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        }
        files = {
            "metadata/reviews.json": json.dumps(
                states, ensure_ascii=False, indent=2
            ).encode("utf-8")
        }
        DatasetCapture(root)._invalidate_split(files)
        commit(root, files)


def derive(root, original, config, rotation=None):
    with consistent(root):
        record = next((r for r in review(root) if r["original"] == original), None)
        if not record:
            raise ValueError("Original no registrado")
        path = safe_path(root, original)
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError("Original no decodificable")
        explicit = rotation is not None
        profile = copy.deepcopy(config["vision"])
        stored = record.get("transform")
        if rotation is None:
            if not stored or stored.get("rotation") not in (0, 90, 180, 270):
                raise ValueError("Orientación desconocida: revisión manual obligatoria")
            rotation = stored["rotation"]
            profile.update(
                {
                    k: stored[k]
                    for k in ("flip_horizontal", "flip_vertical")
                    if k in stored
                }
            )
        if type(rotation) is not int or rotation not in (0, 90, 180, 270):
            raise ValueError("Rotación inválida")
        profile["rotation"] = rotation
        result = Perception(profile).process(
            Frame(
                0,
                time.monotonic(),
                image,
                0,
                "archivo_offline",
                record.get("source", "fixture_prueba"),
            )
        )
        identity = uuid.uuid4().hex
        name = f"derived/normalized/{identity}.png"
        encoder = DatasetCapture(root)
        files = {name: encoder._png(result.normalized)}
        item = {
            "schema_version": 1,
            "original": original,
            "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "normalized": name,
            "crop": None,
            "rotation": rotation,
            "flip_horizontal": profile["flip_horizontal"],
            "flip_vertical": profile["flip_vertical"],
            "orientation_origin": "confirmacion_operador" if explicit else "metadata",
            "profile_name": profile["profile_name"],
            "shape": record["shape"],
            "color": record["color"],
            "session": record["session"],
            "review": "sin_revisar",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "roi": None,
        }
        candidates = [
            o
            for o in result.observation.objects
            if o.color == record["color"]
            or (record["shape"] == "no_objetivo" and record["color"] == "sin_color")
        ]
        if len(candidates) == 1:
            bounds = crop_bounds(
                candidates[0].box, result.observation.dimensions, profile["crop_margin"]
            )
            x0, y0, x1, y1 = bounds
            crop = f"derived/normalized/{identity}_crop.png"
            files[crop] = encoder._png(result.normalized[y0:y1, x0:x1])
            item.update(crop=crop, roi=list(bounds))
        path_meta = safe_path(root, "metadata/normalizations.jsonl")
        old = path_meta.read_bytes() if path_meta.exists() else b""
        files["metadata/normalizations.jsonl"] = old + (
            json.dumps(item, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        encoder._invalidate_split(files)
        commit(root, files)
        return item
