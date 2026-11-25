"""Revisión persistente y división reproducible por sesiones y duplicados."""

import csv
import hashlib
import json
from pathlib import Path
import random
import cv2
from dataset.storage import consistent, safe_path, commit

STATES = ("sin_revisar", "aceptada", "rechazada")


def originals(root):
    root = Path(root).resolve()
    with consistent(root):
        path = root / "metadata/manifest.csv"
        if not path.exists():
            return []
        found = {}
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                try:
                    p = safe_path(root, row.get("image", ""))
                except ValueError:
                    continue
                if row.get("source") == "camara_real" and p.is_file():
                    found.setdefault(row["image"], row)
        return list(found.values())


def review(root):
    root = Path(root)
    with consistent(root):
        path = root / "metadata/vision_v2.jsonl"
        records = (
            {
                r["original"]: r
                for r in (
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            }
            if path.exists()
            else {}
        )
        decisions = root / "metadata/reviews.json"
        states = (
            json.loads(decisions.read_text(encoding="utf-8"))
            if decisions.exists()
            else {}
        )
        manifest = root / "metadata/manifest.csv"
        if manifest.exists():
            with manifest.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    if row.get("source") != "camara_real":
                        continue
                    try:
                        safe_path(root, row["image"])
                    except ValueError:
                        continue
                    records.setdefault(
                        row["image"],
                        dict(
                            row,
                            original=row["image"],
                            id=Path(row["image"]).stem,
                            quality={
                                "warnings": ["Original anterior sin evaluación v2"]
                            },
                            crop=None,
                            roi=None,
                        ),
                    )
        for name, r in records.items():
            r["file_exists"] = safe_path(root, name).is_file()
            r["review"] = states.get(name, {}).get(
                "state", r.get("review", "sin_revisar")
            )
        return list(records.values())


def set_review(root, original, state):
    if state not in STATES:
        raise ValueError("Revisión: sin_revisar, aceptada o rechazada")
    root = Path(root)
    with consistent(root):
        records = {r["original"]: r for r in review(root)}
        if original not in records or not safe_path(root, original).is_file():
            raise ValueError("Original inexistente o no registrado")
        path = root / "metadata/reviews.json"
        decisions = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        )
        from datetime import datetime, timezone

        decisions[original] = {
            "state": state,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        }
        files = {
            "metadata/reviews.json": json.dumps(
                decisions, ensure_ascii=False, indent=2
            ).encode("utf-8")
        }
        if (root / "metadata/split_sessions.json").exists():
            files["metadata/split_sessions.json"] = json.dumps(
                {"valid": False, "reason": "Revisión modificada; regenerar división"}
            ).encode("utf-8")
        commit(root, files)


def image_digest(path):
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        return None
    return hashlib.sha256(image.tobytes() + str(image.shape).encode()).hexdigest()


def split_sessions(root, seed=42):
    root = Path(root)
    with consistent(root):
        reviews = {r["original"]: r for r in review(root)}
        manifest = root / "metadata/manifest.csv"
        if manifest.exists():
            with manifest.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    if (
                        row.get("source") == "camara_real"
                        and reviews.get(row["image"], {}).get("review") != "rechazada"
                        and not safe_path(root, row["image"]).is_file()
                    ):
                        raise ValueError("Falta original registrado: " + row["image"])
        rows = [
            r for r in originals(root) if reviews[r["image"]]["review"] != "rechazada"
        ]
        sessions = sorted({r["session"] for r in rows})
        if len(sessions) < 3:
            raise ValueError(
                "Se requieren al menos tres sesiones reales independientes; no se dividirán ráfagas"
            )
        parent = {s: s for s in sessions}

        def find(s):
            while parent[s] != s:
                s = parent[s]
            return s

        from dataset.normalize import records as normalized_records

        linked = {}
        for item in normalized_records(root):
            if item.get("review") == "rechazada":
                continue
            linked.setdefault(item["original"], []).append(item)
        hashes, derived = {}, {}
        warnings = [
            "Porcentajes aproximados por grupos completos; revisar balance y diversidad."
        ]
        for row in rows:
            name = row["image"]
            record = reviews[name]
            digest = image_digest(safe_path(root, name))
            row["sha256"] = digest
            if digest:
                if digest in hashes:
                    previous = hashes[digest]
                    if (
                        previous["shape"] != row["shape"]
                        or previous["color"] != row["color"]
                    ):
                        raise ValueError(
                            "Duplicado exacto con etiquetas humanas incompatibles; revisar antes de dividir"
                        )
                    parent[find(row["session"])] = find(previous["session"])
                else:
                    hashes[digest] = row
            elif record["review"] == "aceptada":
                raise ValueError("Imagen aceptada no decodificable; revisar archivo")
            else:
                warnings.append(
                    "Archivo legado sin revisar no decodificable: "
                    + name
                    + "; división solo de planificación, no apta para entrenar"
                )
            cp = record.get("crop")
            if cp and not safe_path(root, cp).is_file():
                raise ValueError("Falta archivo derivado: " + cp)
            if cp:
                crop_digest = image_digest(safe_path(root, cp))
                if crop_digest is None:
                    raise ValueError("Recorte no decodificable: " + cp)
                if crop_digest in hashes:
                    previous = hashes[crop_digest]
                    if (
                        previous["shape"] != row["shape"]
                        or previous["color"] != row["color"]
                    ):
                        raise ValueError(
                            "Recorte duplicado con etiquetas incompatibles"
                        )
                    parent[find(row["session"])] = find(previous["session"])
                else:
                    hashes[crop_digest] = row
            for item in linked.get(name, []):
                if (
                    hashlib.sha256(safe_path(root, name).read_bytes()).hexdigest()
                    != item["original_sha256"]
                ):
                    raise ValueError(
                        "Original modificado después de normalizar: " + name
                    )
                for relative in (item["normalized"], item.get("crop")):
                    if not relative:
                        continue
                    if not safe_path(root, relative).is_file():
                        raise ValueError("Falta derivado normalizado: " + relative)
                    dg = image_digest(safe_path(root, relative))
                    if dg is None:
                        raise ValueError("Derivado no decodificable: " + relative)
                    if dg in hashes:
                        previous = hashes[dg]
                        if (
                            previous["shape"] != row["shape"]
                            or previous["color"] != row["color"]
                        ):
                            raise ValueError("Derivado con etiquetas incompatibles")
                        parent[find(row["session"])] = find(previous["session"])
                    else:
                        hashes[dg] = row
            derived[name] = cp
        groups = {}
        for s in sessions:
            groups.setdefault(find(s), []).append(s)
        groups = list(groups.values())
        if len(groups) < 3:
            raise ValueError(
                "Duplicados enlazan sesiones: faltan tres grupos independientes para evitar fuga"
            )
        rng = random.Random(seed)
        assignment = None
        for _ in range(512):
            candidate = [list(g) for g in groups]
            rng.shuffle(candidate)
            ntest = max(1, round(len(candidate) * 0.15))
            nval = max(1, round(len(candidate) * 0.15))
            split = {
                s: (
                    "test"
                    if i < ntest
                    else "validation" if i < ntest + nval else "train"
                )
                for i, g in enumerate(candidate)
                for s in g
            }
            if all(
                {"cubo", "cilindro", "prisma_triangular"}
                <= {r["shape"] for r in rows if split[r["session"]] == subset}
                for subset in ("train", "validation", "test")
            ):
                assignment = split
                break
        if assignment is None:
            raise ValueError(
                "No se encontró división de sesiones/duplicados con las tres clases en cada conjunto"
            )
        items = [
            dict(
                original=r["image"],
                derived=derived[r["image"]],
                normalizations=linked.get(r["image"], []),
                session=r["session"],
                shape=r["shape"],
                color=r["color"],
                subset=assignment[r["session"]],
                sha256=r["sha256"],
                review=reviews[r["image"]]["review"],
                eligible_for_training=reviews[r["image"]]["review"] == "aceptada"
                and r["sha256"] is not None,
            )
            for r in rows
        ]
        summary = {}
        for subset in ("train", "validation", "test"):
            selected = [r for r in items if r["subset"] == subset]
            summary[subset] = {
                "total": len(selected),
                "shapes": {
                    k: sum(r["shape"] == k for r in selected)
                    for k in ("cubo", "cilindro", "prisma_triangular", "no_objetivo")
                },
                "colors": {
                    k: sum(r["color"] == k for r in selected)
                    for k in ("rojo", "verde", "azul", "sin_color")
                },
            }
        ready = all(r["eligible_for_training"] for r in items)
        if any(r["shape"] == "no_objetivo" for r in items) and any(
            not any(
                r["shape"] == "no_objetivo" and r["subset"] == subset for r in items
            )
            for subset in ("train", "validation", "test")
        ):
            ready = False
            warnings.append(
                "Negativos sin cobertura en los tres conjuntos; ampliar sesiones independientes"
            )
        if any(
            item.get("review") != "aceptada"
            for group in linked.values()
            for item in group
        ):
            ready = False
            warnings.append(
                "Nuevas normalizaciones pendientes de revisión individual; no habilitadas para entrenamiento"
            )
        if not ready:
            warnings.append(
                "Hay muestras sin revisar: esta división NO está habilitada para entrenamiento"
            )
        result = {
            "schema_version": 2,
            "valid": True,
            "training_ready": ready,
            "seed": seed,
            "ratios_proposed": [0.70, 0.15, 0.15],
            "sessions": assignment,
            "items": items,
            "summary": summary,
            "warnings": warnings,
        }
        commit(
            root,
            {
                "metadata/split_sessions.json": json.dumps(
                    result, ensure_ascii=False, indent=2
                ).encode("utf-8")
            },
        )
        return result
