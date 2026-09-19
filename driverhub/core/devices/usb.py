# -*- coding: utf-8 -*-
"""Coletor de dispositivos USB: hubs, adaptadores, pendrives e periféricos."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

USB_HINTS = ("usb", "hub")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in raw:
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if "usb" not in hw and "usb" not in name and not any(h in name for h in ("hub",)):
            continue
        kind = "usb"
        if "hub" in name:
            kind = "usb"
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"usb:{len(out)}"),
            name=str(d.get("name") or "Dispositivo USB"),
            vendor=str(d.get("vendor") or ""),
            kind=kind,
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
            detail=str(d.get("detail") or ""),
        ))
        out.append(dev.to_dict())
    return out