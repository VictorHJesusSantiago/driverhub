# -*- coding: utf-8 -*-
"""Motor de drivers do Windows (pnputil / DISM / WMI)."""
from __future__ import annotations

from typing import Any

__all__ = ["WindowsEngine"]


def __getattr__(name: str) -> Any:
    """Reexportação preguiçosa de :class:`WindowsEngine` (PEP 562)."""
    if name == "WindowsEngine":
        from .base import WindowsEngine  # lazy
        return WindowsEngine
    raise AttributeError(f"módulo {__name__!r} não tem atributo {name!r}")