# -*- coding: utf-8 -*-
"""Coletor de leitores de impressão digital."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

FP_HINTS = ("fingerprint", "impressão digital", "biometric", "biométrico",
            "elan wbf", "goodix", "synaptics wbd", "validity")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        if not any(h in name for h in FP_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"fp:{len(out)}"),
            name=str(d.get("name") or "Leitor de impressão digital"),
            vendor=str(d.get("vendor") or ""),
            kind="fingerprint",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out