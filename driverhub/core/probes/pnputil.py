# -*- coding: utf-8 -*-
"""Sondas pnputil (Windows): dispositivos PnP e driver store.

Nenhuma função lança exceção; falhas retornam ``ok=False`` com a saída
bruta em ``detail`` quando útil.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command


def pnputil_enum_devices() -> Dict[str, Any]:
    """Enumera dispositivos PnP presentes/ausentes via ``pnputil /enum-devices``."""
    if not sys.platform.startswith("win"):
        return {"ok": False, "detail": "pnputil disponível apenas no Windows.",
                "data": []}
    res = run_command(["pnputil", "/enum-devices"], 120)
    if not res["ok"] or not res["data"].strip():
        legacy = run_command(["pnputil", "/devices"], 120)
        if legacy["data"].strip():
            res = legacy
    devices = _parse_blocks(res["data"])
    return {"ok": bool(devices),
            "detail": f"{len(devices)} dispositivos PnP",
            "data": devices, "raw": res["data"]}


def pnputil_enum_drivers() -> Dict[str, Any]:
    """Enumera os pacotes de driver do Driver Store via ``pnputil /enum-drivers``."""
    if not sys.platform.startswith("win"):
        return {"ok": False, "detail": "pnputil disponível apenas no Windows.",
                "data": []}
    res = run_command(["pnputil", "/enum-drivers"], 120)
    drivers = _parse_blocks(res["data"])
    return {"ok": bool(drivers),
            "detail": f"{len(drivers)} pacotes de driver no Driver Store",
            "data": drivers, "raw": res["data"]}


def _parse_blocks(text: str) -> List[Dict[str, str]]:
    """Divide a saída em blocos separados por linha em branco e extrai rótulos.

    Linhas no formato ``Rótulo: valor`` (pnputil separa com tabuladores).
    O primeiro termo é preservado em ``label``.
    """
    if not text:
        return []
    blocks: List[Dict[str, str]] = []
    for raw_block in re.split(r"\n\s*\n", text):
        entry: Dict[str, str] = {}
        for line in raw_block.splitlines():
            line = line.strip("\r\n\t ")
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
            else:
                key, value = line, ""
            key = key.strip()
            if key:
                if "label" not in entry:
                    entry["label"] = key
                entry.setdefault(key, value.strip())
        if entry:
            blocks.append(entry)
    return blocks


def _run_devices_probe() -> Result:
    res = pnputil_enum_devices()
    return Result(res["ok"], res["detail"], res["data"], "pnputil.devices")


def _run_drivers_probe() -> Result:
    res = pnputil_enum_drivers()
    return Result(res["ok"], res["detail"], res["data"], "pnputil.drivers")


register(Probe("pnputil.devices", "Dispositivos PnP via pnputil",
               _run_devices_probe, priority=20))
register(Probe("pnputil.drivers", "Pacotes do Driver Store via pnputil",
               _run_drivers_probe, priority=50))