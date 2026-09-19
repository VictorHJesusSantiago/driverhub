# -*- coding: utf-8 -*-
"""Coletor de armazenamento: NVMe/SATA/RAID/usb-drives e layouts de disco."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

STO_HINTS = ("nvme", "sata", "ahci", "rapid storage", "raid", "scsi", "sd host",
             "storage controller", "ssd", "sdbus", "pci\ven_144d")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        hw = str(d.get("hwid") or "").lower()
        if not any(h in name + " " + hw for h in STO_HINTS):
            continue
        dev = enrich_from_ids(Device(
            id=f"sto:{len(out)}",
            name=str(d.get("name") or "Controlador de armazenamento"),
            vendor=str(d.get("vendor") or ""),
            kind="storage",
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
        ))
        out.append(dev.to_dict())

    for i, disk in enumerate(inventory.get("disks") or []):
        out.append({"id": f"vol:{len(out)}",
                    "name": str(disk.get("mount") or disk.get("device") or "Volume"),
                    "vendor": "",
                    "kind": "storage",
                    "hwid": "",
                    "status": "ok",
                    "driver": str(disk.get("fstype") or ""),
                    "detail": f"{disk.get('total', 0)} bytes totais · {disk.get('device')}",
                    "meta": disk})
    return out