# -*- coding: utf-8 -*-
"""Coletor de dispositivos Bluetooth."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if "bluetooth" not in name and "btusb" not in hw and "bth" not in hw:
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"bt:{len(out)}"),
            name=str(d.get("name") or "Adaptador Bluetooth"),
            vendor=str(d.get("vendor") or ""),
            kind="bluetooth",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out