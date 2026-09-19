# -*- coding: utf-8 -*-
"""Sonda de IDs USB: nomeia VID/PID sem depender de rede.

Tabela embutida dos fabricantes mais comuns; base externa opcional
``data/usb_ids.json`` (vendors/devices) carregada lazy quando presente.
Nenhuma função lança exceção.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .base import Probe, Result, register

_VENDORS: Dict[str, str] = {
    "046D": "Logitech", "045E": "Microsoft", "0BDA": "Realtek",
    "04F2": "Chicony", "13D3": "IMC Networks", "03F0": "HP",
    "8087": "Intel", "0A5C": "Broadcom", "0781": "SanDisk", "05AC": "Apple",
    "0951": "Kingston", "04E8": "Samsung", "2717": "Xiaomi", "18D1": "Google",
    "05C6": "Qualcomm", "2357": "TP-Link", "1D6B": "Linux Foundation",
    "0C45": "Microdia", "0461": "Primax", "04D9": "Holtek", "1BCF": "SunplusIT",
    "0489": "Foxconn", "0CF3": "Qualcomm Atheros", "0E8D": "MediaTek",
    "2C7C": "Mozilla", "258A": "Quectel",
}

_DEVICES: Dict[str, Dict[str, str]] = {
    "046D": {"C539": "Mouse G502", "C332": "Webcam C920",
             "C547": "Unifying Receiver", "0A0A": "Teclado G213"},
    "045E": {"0039": "IntelliMouse", "0825": "LifeCam HD",
             "093A": "Headset sem fio", "07B8": "Presenter"},
    "0BDA": {"B00C": "Adaptador Bluetooth 5.0", "8152": "RTL8152 GbE",
             "0179": "Leitor de cartão"},
    "04F2": {"B64A": "Câmera integrada", "B654": "Webcam HD integrada"},
    "13D3": {"5674": "Câmera IR integrada", "5663": "Câmera integrada"},
    "03F0": {"0321": "Hub USB HP", "025A": "Teclado HP"},
    "0781": {"5583": "SanDisk Ultra USB", "55AA": "Cruzer"},
    "2357": {"0106": "Adaptador Wi-Fi", "0137": "Hub USB 3.0 4-portas"},
    "2717": {"FF48": "Redmi USB", "FF50": "Xiaomi (Mi)"},
    "18D1": {"4EE1": "Pixel 2", "4EE7": "Nexus/Pixel"},
    "0CF3": {"E005": "Qualcomm WiFi/BT", "9375": "Atheros BT"},
}


def usb_vendor_name(vid: str) -> str:
    """Nome do fabricante para um vendor ID (hex). Nunca lança."""
    vendor = (vid or "").upper().zfill(4)
    return _VENDORS.get(vendor, f"Fabricante USB {vendor}")


def usb_device_name(vid: str, pid: str) -> str:
    """Nome do dispositivo USB para VID/PID (hex). Nunca lança."""
    vendor = (vid or "").upper().zfill(4)
    product = (pid or "").upper().zfill(4)
    table = _DEVICES.get(vendor, {})
    return table.get(product, f"{usb_vendor_name(vendor)} (PID {product})")


def usb_lookup(vid: str, pid: str) -> Tuple[str, str]:
    """Retorna (vendor, device) nomeados."""
    return usb_vendor_name(vid), usb_device_name(vid, pid)


def _load_external() -> None:
    try:
        from ..tools import paths
        external = os.path.join(paths.data_dir(), "usb_ids.json")
        if not os.path.isfile(external):
            return
        import json
        with open(external, encoding="utf-8") as f:
            data = json.load(f)
        vendors = data.get("vendors", {})
        devices = data.get("devices", {})
        if isinstance(vendors, dict):
            _VENDORS.update({k.upper(): v for k, v in vendors.items()})
        if isinstance(devices, dict):
            for vendor, table in devices.items():
                if isinstance(table, dict):
                    _DEVICES.setdefault(vendor.upper(), {}).update(
                        {k.upper(): v for k, v in table.items()})
    except Exception:  # noqa: BLE001
        pass


_load_external()


def _run_db_probe() -> Result:
    data = {"vendors": len(_VENDORS),
            "devices": sum(len(t) for t in _DEVICES.values())}
    return Result(True,
                  f"{data['vendors']} fabricantes e {data['devices']} dispositivos USB",
                  data, "usb.database")


register(Probe("usb.database", "Base de IDs USB disponível",
               _run_db_probe, priority=95))