# -*- coding: utf-8 -*-
"""Sonda de dispositivos de entrada (Linux ``/proc/bus/input/devices``).

No Windows devolve uma lista vazia (sem sondas de entrada implementadas).
Os blocos ``N:``/``P:``/``H:``/``I:`` são normalizados em ``dict``.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .base import Probe, Result, register


def input_devices() -> List[Dict[str, Any]]:
    """Dispositivos de entrada registrados pelo kernel Linux. Nunca lança."""
    if not sys.platform.startswith("linux"):
        return []
    text = _read("/proc/bus/input/devices")
    if not text:
        return []
    devices: List[Dict[str, Any]] = []
    current: Dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                devices.append(_normalize(current))
                current = {}
            continue
        tag, _, value = line.partition(":")
        current[tag.strip()] = value.strip()
    if current:
        devices.append(_normalize(current))
    return devices


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:  # noqa: BLE001
        return ""


def _normalize(dev: Dict[str, str]) -> Dict[str, Any]:
    """Extrai campos ``Chave=valor`` das linhas N/P/S/I/H."""
    def field(tag: str, label: str) -> str:
        for part in dev.get(tag, "").split():
            if part.startswith(label + "="):
                return part.split("=", 1)[1]
        return ""

    return {
        "name": field("N", "Name"),
        "phys": field("P", "Phys"),
        "sysfs": field("S", "Sysfs"),
        "handlers": dev.get("H", "").replace("Handlers=", "").strip(),
        "bus": field("I", "Bus"),
        "vendor": field("I", "Vendor"),
        "product": field("I", "Product"),
        "version": field("I", "Version"),
        "raw": dict(dev),
    }


def _run_input_probe() -> Result:
    devices = input_devices()
    return Result(bool(devices),
                  f"{len(devices)} dispositivo(s) de entrada",
                  {"count": len(devices), "devices": devices}, "input.devices")


register(Probe("input.devices", "Dispositivos de entrada do kernel Linux",
               _run_input_probe, priority=55))