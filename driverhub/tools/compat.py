# -*- coding: utf-8 -*-
"""Compatibilidade entre plataformas (bibliotecas, binários, features)."""
from __future__ import annotations

import importlib.util
import sys

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"
IS_POSIX = IS_LINUX or IS_MACOS


def has_lib(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def has_bin(name: str) -> bool:
    from .shell import path_of
    return path_of(name) is not None


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def is_64bit() -> bool:
    import struct
    return struct.calcsize("P") == 8


def os_family() -> str:
    if IS_WINDOWS:
        return "windows"
    if IS_LINUX:
        return "linux"
    if IS_MACOS:
        return "macos"
    return "unknown"


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on", "sim")