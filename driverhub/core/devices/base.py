# -*- coding: utf-8 -*-
"""Base dos coletores de dispositivos.

Um coletor: dada a lista bruta de dispositivos (PnP/módulos) e o inventário de
plataforma, devolve uma lista de dispositivos ``dict`` padronizados:
  {id, name, vendor, kind, hwid, status, driver, detail, meta}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Device:
    id: str
    name: str
    vendor: str = ""
    kind: str = "other"
    hwid: str = ""
    status: str = "ok"
    driver: str = ""
    detail: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "vendor": self.vendor,
            "kind": self.kind, "hwid": self.hwid, "status": self.status,
            "driver": self.driver, "detail": self.detail, "meta": self.meta,
        }


class DeviceCollector:
    """Contrato mínimo que um coletor de categoria implementa."""

    key = "other"
    label = "Outros"

    def collect(self, raw: List[Dict[str, Any]],
                inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError


def class_of(hwid: str) -> str:
    """Infere a categoria (kind) a partir do hardware ID quando possível."""
    h = (hwid or "").lower()
    if "pci" in h:
        if "ahci" in h or "nvme" in h or "scsi" in h or "raid" in h or "sata" in h:
            return "storage"
        if "hdaudio" in h or "hd_audio" in h or "audio" in h:
            return "audio"
        if "net" in h or "ethernet" in h or "wlan" in h or "wifi" in h:
            return "network"
        if "usb" in h:
            return "usb"
        if "camera" in h:
            return "camera"
        if "bluetooth" in h:
            return "bluetooth"
        return "pci"
    if "usb" in h:
        if "camera" in h or "webcam" in h:
            return "camera"
        if "hid" in h or "keyboard" in h or "mouse" in h or "touchpad" in h:
            return "input"
        if "bluetooth" in h or "bt" in h:
            return "bluetooth"
        if "printer" in h:
            return "printer"
        return "usb"
    return "other"


def _norm(d: Dict[str, Any], key: str, default: str = "") -> str:
    return str(d.get(key) or default).strip()


def base_device(d: Dict[str, Any], kind: Optional[str] = None) -> Device:
    name = _norm(d, "name")
    hwid = _norm(d, "hwid") or _norm(d, "device_id") or _norm(d, "instance_id")
    return Device(
        id=_norm(d, "id") or hwid or name,
        name=name or "Dispositivo desconhecido",
        vendor=_norm(d, "vendor"),
        kind=kind or class_of(hwid) or _norm(d, "kind") or "other",
        hwid=hwid,
        status=_norm(d, "status") or "ok",
        driver=_norm(d, "driver") or _norm(d, "driver_version"),
        detail=_norm(d, "detail"),
        meta=dict(d.get("meta") or {}),
    )


def enrich_from_ids(device: Device) -> Device:
    """Nomeia vendor/dispositivo pela base de IDs PCI/USB quando a categoria for vazia."""
    if device.vendor:
        return device
    from ...tools import pci, usb, strings
    software_d = None  # 'DEV' precheck
    if device.hwid and any(t in device.hwid.upper() for t in ("VEN", "DEV", "VID", "PID")):
        v, d = strings.extract_hex_pairs(device.hwid)
        if v and d:
            if "USB" in device.hwid.upper():
                dv, dn = usb.lookup(v, d)
            else:
                dv, dn = pci.lookup(v, d)
            device.vendor = dv
            if device.name in ("", "Dispositivo desconhecido"):
                device.name = dn
    return device