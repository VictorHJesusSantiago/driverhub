# -*- coding: utf-8 -*-
"""Coletor de sensores: temperaturas, ventoinhas e voltagens."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    sensors = inventory.get("sensors") or {}
    temps = sensors.get("temperatures") or {}
    fans = sensors.get("fans") or {}
    for i, (key, deg) in enumerate(temps.items()):
        out.append(Device(
            id=f"sen:t{i}",
            name=f"Temperatura {key}",
            vendor="",
            kind="sensors",
            hwid="",
            status="ok" if deg < 85 else "warn",
            driver="",
            detail=f"{deg} °C",
            meta={"kind": "temperature", "key": key, "value": deg},
        ).to_dict())
    for i, (key, rpm) in enumerate(fans.items()):
        out.append(Device(
            id=f"sen:f{i}",
            name=f"Ventoinha {key}",
            vendor="",
            kind="sensors",
            hwid="",
            status="ok",
            driver="",
            detail=f"{rpm} RPM",
            meta={"kind": "fan", "key": key, "value": rpm},
        ).to_dict())
    return out