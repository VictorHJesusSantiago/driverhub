# -*- coding: utf-8 -*-
"""Banco de IDs PCI (vendor/device) para nomear dispositivos sem rede.

Carrega ``data/pci_ids.json`` quando presente; usa um subconjunto embutido
dos fabricantes mais comuns como fallback.
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

_VENDORS: Dict[str, str] = {
    "10DE": "NVIDIA", "8086": "Intel", "1022": "AMD", "1002": "AMD/ATI",
    "10EC": "Realtek", "14E4": "Broadcom", "168C": "Qualcomm Atheros",
    "8087": "Intel", "8088": "Intel", "1D6B": "Linux Foundation",
    "1106": "VIA Technologies", "1B21": "ASMedia", "144D": "Samsung",
    "15B7": "SanDisk", "1179": "Toshiba", "1C5C": "SK hynix", "1344": "Micron",
    "1AF5": "? (Micro-Star)", "103C": "HP", "1028": "Dell", "1043": "ASUSTeK",
    "1462": "MSI", "1458": "Gigabyte", "1D05": "Razer", "1B1C": "Corsair",
    "1131": "Philips", "15AD": "VMware", "10DE": "NVIDIA", "13D3": "IMC Networks",
    "8087": "Intel", "0A5C": "Broadcom", "104C": "Texas Instruments",
}

_DEVICES: Dict[str, Dict[str, str]] = {
    "10DE": {"1E84": "GeForce RTX 2070 SUPER", "1F08": "GeForce RTX 2060",
             "2487": "GeForce RTX 3060", "25A0": "GeForce RTX 3060 Laptop",
             "2927": "GeForce RTX 4060 Laptop", "2886": "GeForce RTX 5060",
             "23B7": "Tegra X1"},
    "8086": {"9A49": "UHD Graphics", "A3A0": "Comet Lake PCH", "A3AF": "Comet Lake SATA",
             "9BC8": "Z490 Chipset", "4DE0": "Raptor Lake SATA", "12AF": "WiFi 6 AX210"},
    "1002": {"1638": "Cezanne Radeon Vega", "73DF": "Radeon RX 6700 XT",
             "164E": "Rembrandt Radeon"},
    "1022": {"1630": "VanGogh SMBus", "14B5": "Cezanne SMBus", "1648": "Rembrandt SMBus"},
    "10EC": {"8168": "RTL8111/8168 PCIe GbE", "8136": "RTL810xE PCIe Fast Ethernet",
             "8229": "RTL8822CE Wi-Fi", "8852": "RTL8852AE Wi-Fi"},
    "14E4": {"43A0": "BCM43602 Wi-Fi", "4353": "BCM4313 Wi-Fi", "1686": "NetXtreme"},
    "144D": {"A808": "NVMe SSD", "A804": "PM981/NVMe SSD"},
    "15B7": {"5009": "WD Black NVMe", "5003": "WD Blue SN550"},
    "1B21": {"1142": "ASM1142 USB 3.1", "0612": "ASM1062 SATA"},
}


def vendor_name(vendor: str) -> str:
    v = (vendor or "").upper().zfill(4)
    return _VENDORS.get(v, f"Vendor {v}")


def device_name(vendor: str, device: str) -> str:
    v = (vendor or "").upper().zfill(4)
    d = (device or "").upper().zfill(4)
    table = _DEVICES.get(v, {})
    return table.get(d, f"{vendor_name(v)} (DEV {d})")


def lookup(vendor: str, device: str) -> Tuple[str, str]:
    """Retorna (vendor, device) nomeados."""
    return vendor_name(vendor), device_name(vendor, device)


def _load_external() -> None:
    try:
        from ..tools import paths
        external = os.path.join(paths.data_dir(), "pci_ids.json")
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