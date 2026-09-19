# -*- coding: utf-8 -*-
"""Formatadores de tamanho (bytes) e duração."""
from __future__ import annotations

from typing import Optional


def human_bytes(n: Optional[float], binary: bool = True) -> str:
    if n is None:
        return "—"
    n = float(n)
    base = 1024.0 if binary else 1000.0
    units = (["B", "KiB", "MiB", "GiB", "TiB", "PiB"] if binary
             else ["B", "kB", "MB", "GB", "TB", "PB"])
    for unit in units:
        if abs(n) < base or unit == units[-1]:
            return f"{n:,.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= base
    return f"{n:,.1f} {units[-1]}"


def human_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}min {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}min"


def human_percent(current: float, total: float) -> str:
    if total <= 0:
        return "0%"
    return f"{min(100.0, current * 100.0 / total):.0f}%"