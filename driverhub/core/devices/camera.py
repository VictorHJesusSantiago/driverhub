# -*- coding: utf-8 -*-
"""Coletor de câmeras: webcams e dispositivos de captura de vídeo."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

CAM_HINTS = ("camera", "webcam", "web cam", "imaging", "image", "capture",
             "integrated camera", "3-ccd", "video device", "uxga")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in CAM_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=str(d.get("id") or f"cam:{len(out)}"),
            name=str(d.get("name") or "Câmera"),
            vendor=str(d.get("vendor") or ""),
            kind="camera",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out