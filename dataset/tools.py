"""Revisión y división por sesiones completas, sin copiar ni aumentar originales."""

import csv
import json
from pathlib import Path
import random


def originals(root):
    root = Path(root).resolve()
    path = root / "metadata" / "manifest.csv"
    if not path.exists():
        return []
    found = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            p = (root / row.get("image", "")).resolve()
            if (
                row.get("source") != "camara_real"
                or not p.is_relative_to(root)
                or not p.is_file()
            ):
                continue
            found.setdefault(row["image"], row)
    return list(found.values())


def review(root):
    path = Path(root) / "metadata" / "vision_v2.jsonl"
    return (
        [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if path.exists()
        else []
    )


def split_sessions(root, seed=42):
    rows = originals(root)
    sessions = sorted({r["session"] for r in rows})
    if len(sessions) < 3:
        raise ValueError(
            "Se requieren al menos tres sesiones reales independientes; no se dividirán ráfagas"
        )
    random.Random(seed).shuffle(sessions)
    count = len(sessions)
    ntest = max(1, round(count * 0.15))
    nval = max(1, round(count * 0.15))
    assignment = {
        s: ("test" if i < ntest else "validation" if i < ntest + nval else "train")
        for i, s in enumerate(sessions)
    }
    result = {
        "schema_version": 1,
        "seed": seed,
        "ratios_proposed": [0.70, 0.15, 0.15],
        "sessions": assignment,
        "items": [],
        "warnings": [
            "Porcentajes aproximados por sesiones; revisar balance de clases y diversidad."
        ],
    }
    derivatives = {r["original"]: r.get("crop") for r in review(root) if r.get("crop")}
    for row in rows:
        result["items"].append(
            {
                "original": row["image"],
                "derived": derivatives.get(row["image"]),
                "session": row["session"],
                "shape": row["shape"],
                "subset": assignment[row["session"]],
            }
        )
    # Cada conjunto necesita ejemplos de las tres clases. Rechazar una división
    # no útil es preferible a repartir frames vecinos para forzar porcentajes.
    for subset in ("train", "validation", "test"):
        if {r["shape"] for r in result["items"] if r["subset"] == subset} != {
            "cubo",
            "cilindro",
            "prisma_triangular",
        }:
            raise ValueError(
                "Sesiones insuficientes para representar las tres clases en cada conjunto; capture sesiones balanceadas"
            )
    target = Path(root) / "metadata" / "split_sessions.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(target)
    return result
