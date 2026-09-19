# -*- coding: utf-8 -*-
"""Motor de drivers do macOS (kext / system_profiler)."""
from __future__ import annotations

from typing import Any

__all__ = ["MacOSEngine"]


def __getattr__(name: str) -> Any:
    """Reexportação preguiçosa de :class:`MacOSEngine` (PEP 562)."""
    if name == "MacOSEngine":
        from .base import MacOSEngine  # lazy
        return MacOSEngine
    raise AttributeError(f"módulo {__name__!r} não tem atributo {name!r}")