# -*- coding: utf-8 -*-
"""Sondas udevadm (Linux) para propriedades e banco de dados do udev.

Nenhuma função lança exceção: falhas retornam ``ok=False`` com lista vazia.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command


def udevadm_info(devpath: str) -> Dict[str, Any]:
    """Consulta propriedades de um device path via ``udevadm info``."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "udevadm disponível apenas no Linux.",
                "data": {}}
    res = run_command(["udevadm", "info", "--query", "property",
                       "--path", devpath], 30)
    props: Dict[str, str] = {}
    for line in res["data"].splitlines():
        key, _, value = line.partition("=")
        if key.strip():
            props[key.strip()] = value.strip()
    return {"ok": bool(props), "detail": res["detail"], "data": props}


def udevadm_properties() -> Dict[str, Any]:
    """Despeja todo o banco de dispositivos via ``udevadm info --export-db``."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "udevadm disponível apenas no Linux.",
                "data": []}
    res = run_command(["udevadm", "info", "--export-db"], 60)
    devices = _parse_export_db(res["data"])
    return {"ok": bool(devices),
            "detail": f"{len(devices)} dispositivos no banco do udev",
            "data": devices}


def _parse_export_db(text: str) -> List[Dict[str, Any]]:
    """Interpreta linhas ``P:``, ``N:``, ``S:``, ``E: KEY=value``."""
    devices: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in text.splitlines():
        if not line:
            continue
        tag, _, rest = line.partition(":")
        tag = tag.strip()
        rest = rest.strip()
        if tag == "P":
            if current:
                devices.append(current)
            current = {"path": rest, "symlinks": [], "properties": {}}
        elif not current:
            continue
        elif tag == "N":
            current["name"] = rest
        elif tag == "S":
            current["symlinks"].append(rest)
        elif tag == "E":
            key, _, value = rest.partition("=")
            current["properties"][key.strip()] = value.strip()
    if current:
        devices.append(current)
    return devices


def _run_db_probe() -> Result:
    res = udevadm_properties()
    return Result(res["ok"], res["detail"], res["data"], "udevadm.db")


register(Probe("udevadm.db", "Banco de propriedades udev (export-db)",
               _run_db_probe, priority=45))