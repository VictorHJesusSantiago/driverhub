# -*- coding: utf-8 -*-
"""Coletor de áudio: isola dispositivos de som da lista bruta (PnP)."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, class_of, enrich_from_ids

AUDIO_HINTS = (
    "audio", "sound", "hdaudio", "hd audio", "codec", "speaker",
    "microphone", "output", "input audio",
)


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in AUDIO_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=f"audio:{len(out)}",
            name=str(d.get("name") or "Dispositivo de áudio"),
            vendor=str(d.get("vendor") or ""),
            kind="audio",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())
    return out