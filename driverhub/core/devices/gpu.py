# -*- coding: utf-8 -*-
"""Coletor de GPUs: unifica os dados de adaptadores de vídeo da plataforma."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, gpu in enumerate(inventory.get("gpu") or []):
        name = str(gpu.get("name") or "Placa de vídeo")
        vendor = str(gpu.get("vendor") or "")
        driver = str(gpu.get("driver_version") or "")
        dev = Device(
            id=f"gpu:{i}",
            name=name,
            vendor=vendor,
            kind="gpu",
            hwid=str(gpu.get("pci_id") or ""),
            status="ok",
            driver=driver,
            detail=(f"Driver: {driver}" if driver else "") + " " + str(gpu.get("driver_date") or ""),
            meta=gpu,
        )
        out.append(dev.to_dict())
    return out