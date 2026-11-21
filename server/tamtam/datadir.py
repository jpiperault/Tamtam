"""Fichiers dans le dossier persistant (/data) : la documentation et les médias envoyés (dossier media/).

Toutes les données métier sont dans PostgreSQL. La documentation est recopiée à chaque démarrage depuis la version
livrée avec l'application (écriture atomique : fichier .tmp puis renommage), donc elle se recrée seule si elle manque.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import log

_log = log.get("data")
DOCS = ("guide.md",)


def _seed_dir() -> Path | None:
    here = Path(__file__).resolve().parent
    for c in (here / "seed_docs", here.parents[1] / "docs"):
        if (c / "guide.md").is_file():
            return c
    return None


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def docs_dir(data_dir: str) -> Path:
    return Path(data_dir) / "docs"


def ensure_docs(data_dir: str) -> bool:
    """Met la documentation à jour dans <data_dir>/docs. Ne bloque jamais le démarrage."""
    seed = _seed_dir()
    if seed is None:
        _log.warning("documentation livrée introuvable : rien à copier")
        return False
    try:
        for name in DOCS:
            src = (seed / name).read_bytes()
            dst = docs_dir(data_dir) / name
            if not dst.is_file() or dst.read_bytes() != src:
                write_atomic(dst, src)
                _log.info("documentation écrite : %s", dst)
        return True
    except OSError as exc:
        _log.warning("documentation non écrite dans %s : %s", data_dir, exc)
        return False


def read_doc(data_dir: str, name: str) -> str | None:
    if name not in DOCS:
        return None
    try:
        return (docs_dir(data_dir) / name).read_text("utf-8")
    except OSError:
        return None
