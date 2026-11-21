"""Journalisation simple sur la sortie standard."""
from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s : %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)


def get(name: str) -> logging.Logger:
    return logging.getLogger(f"tamtam.{name}")
