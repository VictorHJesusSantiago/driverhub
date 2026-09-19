# -*- coding: utf-8 -*-
"""Caminhos e diretórios do DriverHub."""
from __future__ import annotations

import os
from typing import Optional

from .. import constants as C


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def config_dir() -> str:
    return ensure_dir(C.config_dir())


def logs_path() -> str:
    return C.log_file()


def downloads_dir() -> str:
    return ensure_dir(os.path.join(config_dir(), "downloads"))


def backups_dir() -> str:
    return ensure_dir(C.backups_dir())


def data_dir() -> str:
    """Diretório de dados embarcados (catálogo, IDs PCI/USB, temas)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def safe_name(name: str, max_len: int = 80) -> str:
    keep = []
    for ch in str(name).strip():
        keep.append(ch if (ch.isalnum() or ch in " ._-()[]") else "_")
    out = "".join(keep)
    return out[:max_len] or "unnamed"


def relative_to_home(path: str) -> str:
    home = os.path.expanduser("~")
    try:
        return os.path.relpath(path, home)
    except Exception:
        return path