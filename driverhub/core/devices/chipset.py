# -*- coding: utf-8 -*-
"""Coletor de chipset: ponte PCI, SMBus e controladores da placa-mãe."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

CHIPSET_HINTS = ("chipset", "smbus", "south bridge", "north bridge", "pme",
                 "pci-bridge", "pci bridge", "isa bridge", "host bridge",
                 "pmc", "thermal zone", "lpc")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in CHIPSET_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"chip:{len(out)}"),
            name=str(d.get("name") or "Chipset"),
            vendor=str(d.get("vendor") or ""),
            kind="chipset",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
            detail=str(d.get("detail") or ""),
        ))
        out.append(dev.to_dict())
    return out