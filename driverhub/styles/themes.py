# -*- coding: utf-8 -*-
"""Temas visuais para o terminal (cores ANSI por papel/estado)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

DARK: Dict[str, str] = {
    "accent": "#3f9bff", "accent2": "#6fc3ff",
    "ok": "green", "warn": "yellow", "error": "red", "info": "cyan",
    "muted": "dim", "title": "bold cyan", "table_header": "cyan",
}
LIGHT: Dict[str, str] = {
    "accent": "#1f6feb", "accent2": "#0969da",
    "ok": "green", "warn": "dark_orange", "error": "red", "info": "blue",
    "muted": "dim", "title": "bold blue", "table_header": "blue",
}
HIGHCONTRAST: Dict[str, str] = {
    "accent": "yellow", "accent2": "white",
    "ok": "bright_green", "warn": "bright_yellow", "error": "bright_red",
    "info": "bright_cyan", "muted": "dim", "title": "bold white",
    "table_header": "bright_cyan",
}

_THEMES: Dict[str, Dict[str, str]] = {
    "dark": DARK, "light": LIGHT, "highcontrast": HIGHCONTRAST,
}
_EXTRA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def _load_extra() -> None:
    try:
        for fn in os.listdir(_EXTRA_DIR):
            if fn.endswith(".json"):
                name = fn[:-5]
                with open(os.path.join(_EXTRA_DIR, fn), encoding="utf-8") as f:
                    _THEMES[name] = json.load(f)
    except Exception:
        pass


_load_extra()


def available() -> list[str]:
    return list(_THEMES.keys())


def get(name: str) -> Dict[str, str]:
    return _THEMES.get(name, DARK)


def ansi(name: str, role: str, default: str = "white") -> str:
    return _THEMES.get(name, DARK).get(role, default)