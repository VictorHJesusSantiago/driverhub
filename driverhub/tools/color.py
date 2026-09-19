# -*- coding: utf-8 -*-
"""Cores ANSI no terminal com fallback quando rich não estiver disponível."""
from __future__ import annotations

import os
import sys

_USE_ANSI = hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.name != "nt"


def ansi(code: str, text: str) -> str:
    if not _USE_ANSI:
        return text
    return f"\033[{code}m{text}\033[0m"


def red(s: str) -> str:
    return ansi("31", s)


def green(s: str) -> str:
    return ansi("32", s)


def yellow(s: str) -> str:
    return ansi("33", s)


def blue(s: str) -> str:
    return ansi("34", s)


def magenta(s: str) -> str:
    return ansi("35", s)


def cyan(s: str) -> str:
    return ansi("36", s)


def dim(s: str) -> str:
    return ansi("2", s)


def bold(s: str) -> str:
    return ansi("1", s)


def status_ok(s: str = "OK") -> str:
    return green(f"[{s}]")


def status_fail(s: str = "FALHA") -> str:
    return red(f"[{s}]")


def status_warn(s: str = "ATENÇÃO") -> str:
    return yellow(f"[{s}]")