# -*- coding: utf-8 -*-
"""Coletor genérico de dispositivos PCI: qualquer device PCI sem categoria."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, class_of, enrich_from_ids

PCI_CLASSES = ("pci", "pcie", "expres", "pci-express", "agp")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        hw = str(d.get("hwid") or "").lower()
        if "pci" not in hw and not any(c in hw for c in PCI_CLASSES):
            continue
        kind = class_of(hw)
        if kind not in ("pci", "other"):
            continue  # já tratado por outro coletor
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"pci:{len(out)}"),
            name=str(d.get("name") or "Dispositivo PCI"),
            vendor=str(d.get("vendor") or ""),
            kind="pci",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
            detail=str(d.get("detail") or ""),
        ))
        out.append(dev.to_dict())
    return out