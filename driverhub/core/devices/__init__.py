# -*- coding: utf-8 -*-
"""Coletores de dispositivos por categoria de hardware."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .base import Device, DeviceCollector, base_device
from . import (audio, bios, bluetooth, camera, chipset, cpu, fingerprint, gpu,
               input, network, pci, power, printer, sensors, storage, usb)

COLLECTORS: Dict[str, Callable[[List[Dict[str, Any]], Dict[str, Any]],
                              List[Dict[str, Any]]]] = {
    "cpu": cpu.collect,
    "gpu": gpu.collect,
    "audio": audio.collect,
    "network": network.collect,
    "storage": storage.collect,
    "usb": usb.collect,
    "input": input.collect,
    "camera": camera.collect,
    "printer": printer.collect,
    "power": power.collect,
    "sensors": sensors.collect,
    "bios": bios.collect,
    "chipset": chipset.collect,
    "pci": pci.collect,
    "fingerprint": fingerprint.collect,
    "bluetooth": bluetooth.collect,
}

KINDS = tuple(COLLECTORS.keys())


def classify(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Roda todos os coletores e deduplica dispositivos."""
    seen: Dict[str, Dict[str, Any]] = {}
    for key, fn in COLLECTORS.items():
        for dev in fn(raw, inventory):
            dev["kind"] = key
            dedup_id = dev.get("id") or f"{key}:anon"
            if dedup_id not in seen:
                seen[dedup_id] = dev
    # Dispositivos restantes sem categoria
    for i, d in enumerate(raw):
        if not any(d.get("id") == v.get("id") for v in seen.values()):
            seen[f"raw:{i}"] = base_device(d).to_dict()
    return list(seen.values())