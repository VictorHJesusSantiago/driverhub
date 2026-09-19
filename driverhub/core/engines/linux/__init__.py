# -*- coding: utf-8 -*-
"""Motor de drivers do Linux (kmod / DKMS / fwupd)."""
from __future__ import annotations

from typing import Any

__all__ = ["LinuxEngine"]


def __getattr__(name: str) -> Any:
    """Reexportação preguiçosa de :class:`LinuxEngine` (PEP 562)."""
    if name == "LinuxEngine":
        from .base import LinuxEngine  # lazy
        return LinuxEngine
    raise AttributeError(f"módulo {__name__!r} não tem atributo {name!r}")