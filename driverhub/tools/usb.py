# -*- coding: utf-8 -*-
"""Banco de IDs USB (VID/PID) para nomear dispositivos sem rede."""
from __future__ import annotations

import os
from typing import Dict, Tuple

_VENDORS: Dict[str, str] = {
    "046D": "Logitech", "045E": "Microsoft", "0BDA": "Realtek",
    "1D6B": "Linux Foundation", "8087": "Intel", "0A5C": "Broadcom",
    "04F2": "Chicony", "13D3": "IMC Networks", "05AC": "Apple",
    "0951": "Kingston", "0781": "SanDisk", "0C45": "Microdia",
    "0461": "Primax", "04D9": "Holtek", "1BCF": "SunplusIT",
    "0489": "Foxconn", "0CF3": "Qualcomm Atheros", "2357": "TP-Link",
    "0E8D": "MediaTek", "2717": "Xiaomi", "18D1": "Google",
    "05C6": "Qualcomm", "2C7C": "Mozilla", "258A": "Quectel",
}

_DEVICES: Dict[str, Dict[str, str]] = {
    "046D": {"C539": "G502 Gaming Mouse", "C332": "Webcam C920",
             "C547": "Unifying Receiver", "0A0A": "Keyboard G213"},
    "045E": {"0039": "IntelliMouse", "0825": "Camera LifeCam HD",
             "093A": "Wireless Headset", "07B8": "Presenter"},
    "0BDA": {"B00C": "Bluetooth 5.0 Adapter", "8152": "RTL8152 GbE",
             "0179": "Card Reader"},
    "04F2": {"B64A": "Integrated Camera", "B654": "Integrated Webcam HD"},
    "13D3": {"5674": "Integrated IR Camera", "5663": "Integrated Camera"},
    "05AC": {"024F": "Keyboard (Alu)", "0291": "Magic Mouse 2"},
    "0781": {"5583": "SanDisk Ultra USB", "55AA": "Cruzer"},
    "0CF3": {"E005": "Qualcomm WiFi/BT", "9375": "Atheros BT"},
    "2357": {"0106": "WiFi Adapter", "0137": "USB 3.0 Hub 4-port"},
    "2717": {"FF48": "Redmi USB", "FF50": "Mi 10"},
    "18D1": {"4EE1": "Pixel 2", "4EE7": "Nexus/Pixel"},
}


def vendor_name(vid: str) -> str:
    v = (vid or "").upper().zfill(4)
    return _VENDORS.get(v, f"Fabricante {v}")


def device_name(vid: str, pid: str) -> str:
    v = (vid or "").upper().zfill(4)
    p = (pid or "").upper().zfill(4)
    table = _DEVICES.get(v, {})
    return table.get(p, f"{vendor_name(v)} (PID {p})")


def lookup(vid: str, pid: str) -> Tuple[str, str]:
    return vendor_name(vid), device_name(vid, pid)


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
        devs = data.get("devices", {})
        if isinstance(vendors, dict):
            _VENDORS.update({k.upper(): v for k, v in vendors.items()})
        if isinstance(devs, dict):
            for v, table in devs.items():
                if isinstance(table, dict):
                    _DEVICES.setdefault(v.upper(), {}).update(
                        {k.upper(): vv for k, vv in table.items()})
    except Exception:
        pass


_load_external()