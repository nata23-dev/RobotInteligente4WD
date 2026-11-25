"""Lectura de metadatos para la presentación; no cambia la captura existente."""

import csv
from pathlib import Path
from PIL import Image
from dataset.capture import SHAPES, COLORS


def dataset_summary(root):
    from dataset.storage import consistent

    with consistent(root):
        return _dataset_summary(root)


def _dataset_summary(root):
    root = Path(root).resolve()
    shapes = dict.fromkeys(SHAPES, 0)
    colors = dict.fromkeys(COLORS, 0)
    latest = None
    seen = set()
    combinations = {s: {c: 0 for c in COLORS} for s in SHAPES}
    negatives = 0
    manifest = root / "metadata" / "manifest.csv"
    if manifest.exists():
        with manifest.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                if (
                    row.get("source") == "camara_real"
                    and row.get("shape") == "no_objetivo"
                ):
                    negative = (root / row.get("image", "")).resolve()
                    if (
                        negative.is_relative_to(root)
                        and negative.is_file()
                        and negative not in seen
                    ):
                        seen.add(negative)
                        negatives += 1
                    continue
                if (
                    row.get("source") != "camara_real"
                    or row.get("shape") not in shapes
                    or row.get("color") not in colors
                ):
                    continue
                image = (root / row.get("image", "")).resolve()
                if (
                    not image.is_relative_to(root)
                    or image in seen
                    or not image.is_file()
                ):
                    continue
                seen.add(image)
                shapes[row["shape"]] += 1
                colors[row["color"]] += 1
                combinations[row["shape"]][row["color"]] += 1
                latest = image
    preview = None
    if latest:
        try:
            with Image.open(latest) as original:
                preview = original.copy()
            preview.thumbnail((120, 40))
        except OSError:
            pass
    return {
        "shapes": shapes,
        "colors": colors,
        "total": sum(shapes.values()),
        "latest": latest,
        "preview": preview,
        "root": root,
        "combinations": combinations,
        "negatives": negatives,
    }
