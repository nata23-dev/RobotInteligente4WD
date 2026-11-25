"""Originales y derivados con registro completo o recuperación explícita."""

import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import time
import uuid
import cv2
from dataset.storage import commit, consistent, root_lock

SHAPES = ("cubo", "cilindro", "prisma_triangular")
COLORS = ("rojo", "verde", "azul")
FIELDS = (
    "image",
    "shape",
    "color",
    "session",
    "captured_utc",
    "frame_id",
    "received_monotonic",
    "age_at_save_s",
    "width",
    "height",
    "source",
)


class DatasetCapture:
    def __init__(self, destination):
        self.root = Path(destination)
        self.lock = root_lock(self.root)
        with consistent(self.root):
            pass

    def _validate(self, frame, shape, color, session, max_age, source):
        if shape not in SHAPES or color not in COLORS:
            raise ValueError("Forma o color inválidos")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session):
            raise ValueError("Sesión: 1–64 letras ASCII, números, guion o guion bajo")
        if not 0 <= time.monotonic() - frame.received_at <= max_age:
            raise ValueError("Fotograma atrasado; capture uno nuevo")
        if source not in ("camara_real", "fixture_prueba"):
            raise ValueError("Fuente no reconocida")

    def _png(self, image):
        ok, data = cv2.imencode(".png", image)
        if not ok:
            raise OSError("No se pudo codificar PNG")
        return data.tobytes()

    def _manifest(self, name, frame, shape, color, session, source):
        path = self.root / "metadata/manifest.csv"
        previous = path.read_bytes() if path.exists() else b""
        if previous:
            header = next(csv.reader(io.StringIO(previous.decode("utf-8"))))
            if tuple(header) != FIELDS:
                raise ValueError("Manifiesto previo incompatible; no se modificó")
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if not previous:
            writer.writeheader()
        h, w = frame.image.shape[:2]
        writer.writerow(
            dict(
                zip(
                    FIELDS,
                    [
                        name,
                        shape,
                        color,
                        session,
                        datetime.now(timezone.utc).isoformat(),
                        frame.id,
                        frame.received_at,
                        time.monotonic() - frame.received_at,
                        w,
                        h,
                        source,
                    ],
                )
            )
        )
        if previous and not previous.endswith((b"\n", b"\r")):
            previous += b"\n"
        return previous + stream.getvalue().encode("utf-8")

    def _invalidate_split(self, files):
        if (self.root / "metadata/split_sessions.json").exists():
            files["metadata/split_sessions.json"] = json.dumps(
                {
                    "valid": False,
                    "reason": "Dataset o revisión cambió; preparar división nuevamente",
                }
            ).encode("utf-8")

    def save_record(self, frame, shape, color, session, config, guard=lambda: None):
        from ai.perception import Perception
        from ai.transforms import crop_bounds
        from dataset.quality import measure
        from dataset.tools import review

        max_age = config["frame_max_age_s"]
        self._validate(frame, shape, color, session, max_age, frame.source)
        guard()
        result = Perception(config["vision"]).process(frame)
        with consistent(self.root):
            previous = review(self.root)
            quality = measure(
                frame.image,
                config["dataset_options"],
                result.observation.objects,
                [r["quality"] for r in previous if r.get("quality")],
            )
            if quality["rejections"]:
                raise ValueError("; ".join(quality["rejections"]))
            identity = uuid.uuid4().hex
            name = f"images/{shape}/{session}/{identity}.png"
            record = {
                "schema_version": 2,
                "id": identity,
                "original": name,
                "frame_id": frame.id,
                "camera_generation": frame.generation,
                "source": frame.source,
                "shape": shape,
                "color": color,
                "session": session,
                "received_at": frame.received_at,
                "transform": config["vision"],
                "quality": quality,
                "review": "sin_revisar",
                "crop": None,
                "roi": None,
            }
            files = {name: self._png(frame.image)}
            candidates = [o for o in result.observation.objects if o.color == color]
            if len(candidates) == 1:
                target = candidates[0]
                x1, y1, x2, y2 = crop_bounds(
                    target.box,
                    result.observation.dimensions,
                    config["vision"]["crop_margin"],
                )
                cp = f"derived/{shape}/{session}/{identity}.png"
                files[cp] = self._png(result.normalized[y1:y2, x1:x2])
                record.update(crop=cp, roi=[x1, y1, x2, y2])
            else:
                quality["warnings"].append(
                    "Varias figuras del color etiquetado: seleccionar y revisar manualmente; recorte omitido"
                    if candidates
                    else "No hay candidato inequívoco del color etiquetado; recorte omitido"
                )
            files["metadata/manifest.csv"] = self._manifest(
                name, frame, shape, color, session, frame.source
            )
            sidecar = self.root / "metadata/vision_v2.jsonl"
            old = sidecar.read_bytes() if sidecar.exists() else b""
            if old and not old.endswith(b"\n"):
                old += b"\n"
            files["metadata/vision_v2.jsonl"] = old + (
                json.dumps(record, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            self._invalidate_split(files)

            def check():
                self._validate(frame, shape, color, session, max_age, frame.source)
                guard()

            commit(self.root, files, check)
            return self.root / name, record

    def save(self, frame, shape, color, session, max_age=0.8, source="camara_real"):
        self._validate(frame, shape, color, session, max_age, source)
        with consistent(self.root):
            name = f"images/{shape}/{session}/{uuid.uuid4().hex}.png"
            files = {
                name: self._png(frame.image),
                "metadata/manifest.csv": self._manifest(
                    name, frame, shape, color, session, source
                ),
            }
            self._invalidate_split(files)
            commit(
                self.root,
                files,
                lambda: self._validate(frame, shape, color, session, max_age, source),
            )
            return self.root / name

    def counts(self):
        from dataset.tools import originals

        result = dict.fromkeys(SHAPES, 0)
        for row in originals(self.root):
            if row.get("shape") in result:
                result[row["shape"]] += 1
        return result
