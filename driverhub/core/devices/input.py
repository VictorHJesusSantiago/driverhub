# -*- coding: utf-8 -*-
"""Coletor de dispositivos de entrada: teclado, mouse, touchpad, HID."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

INPUT_HINTS = ("keyboard", "teclado", "mouse", "touchpad", "pointing", "hid",
               "hid\vid", "trackpad", "touch panel", "stylus")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in INPUT_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"inp:{len(out)}"),
            name=str(d.get("name") or "Dispositivo de entrada"),
            vendor=str(d.get("vendor") or ""),
            kind="input",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out