"""Transacciones recuperables de un escritor por destino, sin alterar originales previos."""

from contextlib import contextmanager
import json
from pathlib import Path
import threading
import uuid

_locks = {}
_registry_lock = threading.Lock()


def root_lock(root):
    with _registry_lock:
        return _locks.setdefault(str(Path(root).resolve()), threading.RLock())


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Ruta fuera del dataset")
    return path


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        with temp.open("wb") as stream:
            stream.write(data)
            stream.flush()
            import os

            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def recover(root):
    """Undo idempotente de transacciones sin commit, incluso tras reiniciar Python."""
    root = Path(root).resolve()
    with root_lock(root):
        folder = root / "metadata" / "transactions"
        if not folder.exists():
            return
        for journal in sorted(folder.glob("*.json")):
            record = json.loads(journal.read_text(encoding="utf-8"))
            tx = journal.parent / journal.stem
            if not (tx / "committed").exists():
                for name, backup in record["metadata"].items():
                    target = safe_path(root, name)
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        atomic_bytes(target, safe_path(root, backup).read_bytes())
                for name in record["created"]:
                    artifact = safe_path(root, name)
                    artifact.unlink(missing_ok=True)
                    artifact.with_name(artifact.name + ".tmp").unlink(missing_ok=True)
            # Quitar journal primero: un crash durante limpieza no repite undo
            # después de borrar backups. Los restos sin journal no son muestras.
            journal.unlink()
            for item in tx.iterdir():
                item.unlink()
            tx.rmdir()


def commit(root, files, guard=lambda: None):
    """files: ruta relativa -> bytes. Artefactos nuevos; CSV/JSONL reemplazados atómicamente."""
    root = Path(root).resolve()
    with root_lock(root):
        recover(root)
        identity = uuid.uuid4().hex
        directory = root / "metadata" / "transactions"
        tx = directory / identity
        tx.mkdir(parents=True)
        metadata, created = {}, []
        for index, name in enumerate(files):
            target = safe_path(root, name)
            if name in (
                "metadata/manifest.csv",
                "metadata/vision_v2.jsonl",
                "metadata/reviews.json",
                "metadata/split_sessions.json",
                "metadata/normalizations.jsonl",
            ):
                backup = tx / f"backup_{index}"
                if target.exists():
                    atomic_bytes(backup, target.read_bytes())
                    metadata[name] = backup.relative_to(root).as_posix()
                else:
                    metadata[name] = None
            else:
                if target.exists():
                    raise FileExistsError(
                        "No se sobrescriben originales o derivados existentes"
                    )
                created.append(name)
        journal = directory / (identity + ".json")
        atomic_bytes(
            journal,
            json.dumps({"metadata": metadata, "created": created}).encode("utf-8"),
        )
        try:
            for name, data in files.items():
                guard()
                atomic_bytes(safe_path(root, name), data)
            guard()
            atomic_bytes(tx / "committed", b"complete")
        except BaseException:
            recover(root)
            raise
        recover(root)


@contextmanager
def consistent(root):
    with root_lock(root):
        recover(root)
        yield
