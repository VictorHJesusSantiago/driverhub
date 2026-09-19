# -*- coding: utf-8 -*-
"""Coletor de energia/bateria: nível, carga, e política de energia."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    sensors = inventory.get("sensors") or {}
    batt = sensors.get("battery")
    if batt:
        dev = Device(
            id="power:battery",
            name="Bateria",
            vendor="",
            kind="power",
            hwid="",
            status="ok" if batt.get("plugged") else "discharging",
            driver="",
            detail=(f"{batt.get('percent')}% · "
                    f"{'carregando/na tomada' if batt.get('plugged') else 'em bateria'}"),
            meta=batt,
        )
        out.append(dev.to_dict())

    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        if any(h in name for h in ("battery", "bateria", "acpi\psr", "power ")):
            out.append({
                "id": str(d.get("id") or f"pow:{i}"),
                "name": str(d.get("name")),
                "vendor": str(d.get("vendor") or ""),
                "kind": "power",
                "hwid": str(d.get("hwid") or ""),
                "status": str(d.get("status") or "ok"),
                "driver": str(d.get("driver") or ""),
                "detail": str(d.get("detail") or ""),
                "meta": {},
            })
    return out