"""Audita fuentes e historial sin imprimir ni guardar valores de credenciales.

Complementa Gitleaks con credenciales del robot presentes únicamente en archivos
locales ignorados. No obtiene tokens de Git/GitHub ni consulta servicios de red.
"""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {
    ".venv",
    ".runtime",
    ".tools",
    "referencias_locales",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
}
SECRET_NAME = re.compile(r"password|passwd|api_?key|secret|token", re.I)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def private_path(name):
    path = Path(name)
    if path.name == ".gitkeep":
        return False
    if any(part in PRIVATE_PARTS for part in path.parts):
        return True
    if path.name in (
        "config.local.json",
        "ui.local.json",
        "vision_profiles.local.json",
        "secrets.h",
        "arduino_secrets.h",
    ):
        return True
    if path.name.startswith(".env") and path.name not in (
        ".env.example",
        ".env.template",
    ):
        return True
    return path.suffix.lower() in (
        ".zip",
        ".pem",
        ".key",
        ".p12",
        ".pfx",
        ".bin",
        ".elf",
    ) or any(
        name.startswith(p)
        for p in (
            "logs/",
            "evidencias/",
            "dataset/images/",
            "dataset/derived/",
            "dataset/metadata/",
            "models/",
        )
    )


def known_local_values():
    """Solo memoria: se excluyen SSID, URLs y parámetros que no son secretos."""
    values = set()
    local = ROOT / "config.local.json"
    if local.exists():
        config = json.loads(local.read_text(encoding="utf-8-sig"))
        for key, value in config.items():
            if SECRET_NAME.search(key) and isinstance(value, str) and len(value) >= 8:
                values.add(value)
    reference = ROOT / "referencias_locales"
    sources = list((ROOT / ".tools" / "backups").glob("*.ino"))
    if reference.exists():
        sources.extend(reference.rglob("*.ino"))
        for path in reference.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue

            def visit(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if (
                            SECRET_NAME.search(key)
                            and isinstance(value, str)
                            and len(value) >= 8
                        ):
                            values.add(value)
                        visit(value)
                elif isinstance(obj, list):
                    for value in obj:
                        visit(value)

            visit(data)
    for path in sources:
        source = path.read_text(encoding="utf-8-sig")
        for name, value in re.findall(
            r'const\s+char\s*\*\s*(\w+)\s*=\s*"([^"\r\n]*)"', source
        ):
            if SECRET_NAME.search(name) and len(value) >= 8:
                values.add(value)
    variants = set()
    for value in values:
        raw = value.encode("utf-8")
        variants.update(
            (
                raw,
                value.encode("utf-16-le"),
                quote(value, safe="").encode(),
                base64.b64encode(raw),
            )
        )
    return variants


def audit(refs=None):
    values = known_local_values()
    problems = []
    scanned = set()
    objects = (
        git("rev-list", "--objects", *(refs or ["--all"])).decode("utf-8").splitlines()
    )
    commits = git("rev-list", *(refs or ["--all"])).decode().splitlines()

    def inspect(data, filename, scope):
        if any(secret in data for secret in values):
            # Sin snippet, valor, fingerprint o hash de la credencial.
            lines = data.splitlines()
            locations = [
                i
                for i, line in enumerate(lines, 1)
                if any(secret in line for secret in values)
            ]
            problems.append(
                {
                    "file": filename,
                    "type": "credencial local conocida",
                    "scope": scope,
                    "lines": locations,
                    "resolution": "pendiente",
                }
            )

    for commit in commits:
        for name in (
            git("ls-tree", "-r", "--name-only", commit).decode("utf-8").splitlines()
        ):
            if private_path(name):
                problems.append(
                    {
                        "file": name,
                        "type": "ruta privada en historial",
                        "scope": commit[:12],
                        "resolution": "pendiente",
                    }
                )
    for line in objects:
        oid, _, name = line.partition(" ")
        kind = git("cat-file", "-t", oid).strip()
        if kind == b"blob" and oid not in scanned:
            inspect(git("cat-file", "blob", oid), name, "historial")
            scanned.add(oid)
        elif kind in (b"commit", b"tag"):
            inspect(
                git("cat-file", kind.decode(), oid), name or oid[:12], "metadatos Git"
            )
    index = git("ls-files", "--stage", "-z").decode("utf-8").split("\0")
    for entry in filter(None, index):
        meta, name = entry.split("\t", 1)
        oid = meta.split()[1]
        if private_path(name):
            problems.append(
                {
                    "file": name,
                    "type": "ruta privada en índice",
                    "scope": "index",
                    "resolution": "pendiente",
                }
            )
        inspect(git("cat-file", "blob", oid), name, "index")
    files = (
        git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        .decode("utf-8")
        .split("\0")
    )
    for name in filter(None, files):
        path = ROOT / name
        if path.is_file():
            inspect(path.read_bytes(), name, "árbol de trabajo")
            if private_path(name):
                problems.append(
                    {
                        "file": name,
                        "type": "archivo privado publicable",
                        "scope": "worktree",
                        "resolution": "pendiente",
                    }
                )
    return {
        "success": not problems,
        "commits_scanned": len(commits),
        "unique_blobs_scanned": len(scanned),
        "scope": refs or ["todas las referencias locales"],
        "findings": problems,
        "limitations": "Detecta valores locales conocidos y rutas privadas; complementar con Gitleaks y revisión humana. No inspecciona píxeles, secretos desconocidos o dispositivos.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref", action="append", help="Referencia a auditar; por defecto todas"
    )
    parser.add_argument("--report", type=Path, help="Informe sin valores de secretos")
    args = parser.parse_args()
    result = audit(args.ref)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
