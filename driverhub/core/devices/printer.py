# -*- coding: utf-8 -*-
"""Coletor de impressoras e multifuncionais."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

PRINT_HINTS = ("printer", "impressora", "monochrom", "multifunction", "scanner",
               "fax", "ploto", "printer port", "usbprint")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in PRINT_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"prn:{len(out)}"),
            name=str(d.get("name") or "Impressora"),
            vendor=str(d.get("vendor") or ""),
            kind="printer",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out