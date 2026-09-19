# -*- coding: utf-8 -*-
"""Sonda de IDs PCI: nomeia vendors e dispositivos sem depender de rede.

Tabela embutida dos fabricantes mais comuns; uma base externa opcional
``data/pci_ids.json`` (vendors/devices) é carregada por cima quando
presente. Nenhuma função lança exceção.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .base import Probe, Result, register

_VENDORS: Dict[str, str] = {
    "10DE": "NVIDIA", "8086": "Intel", "1002": "AMD/ATI", "1022": "AMD",
    "10EC": "Realtek", "14E4": "Broadcom", "144D": "Samsung", "15B7": "SanDisk",
    "1B21": "ASMedia", "168C": "Qualcomm Atheros", "8087": "Intel",
    "1D6B": "Linux Foundation", "1106": "VIA Technologies", "103C": "HP",
    "1028": "Dell", "1043": "ASUSTeK", "1462": "MSI", "1458": "Gigabyte",
    "15AD": "VMware", "104C": "Texas Instruments",
}

_DEVICES: Dict[str, Dict[str, str]] = {
    "10DE": {"1E84": "GeForce RTX 2070 SUPER", "1F08": "GeForce RTX 2060",
             "2487": "GeForce RTX 3060", "25A0": "GeForce RTX 3060 Laptop",
             "2927": "GeForce RTX 4060 Laptop", "2886": "GeForce RTX 5060",
             "23B7": "Tegra X1"},
    "8086": {"9A49": "UHD Graphics", "A3A0": "Comet Lake PCH",
             "A3AF": "Comet Lake SATA", "9BC8": "Z490 Chipset",
             "4DE0": "Raptor Lake SATA", "12AF": "WiFi 6 AX210",
             "9A09": "Wi-Fi 6 AX201"},
    "1002": {"1638": "Cezanne Radeon Vega", "73DF": "Radeon RX 6700 XT",
             "164E": "Rembrandt Radeon", "15BF": "Radeon RX 580"},
    "1022": {"1630": "VanGogh SMBus", "14B5": "Cezanne SMBus",
             "1648": "Rembrandt SMBus"},
    "10EC": {"8168": "RTL8111/8168 PCIe GbE", "8136": "RTL810xE Fast Ethernet",
             "8229": "RTL8822CE Wi-Fi", "8852": "RTL8852AE Wi-Fi"},
    "14E4": {"43A0": "BCM43602 Wi-Fi", "4353": "BCM4313 Wi-Fi",
             "1686": "NetXtreme"},
    "144D": {"A808": "NVMe SSD", "A804": "PM981/NVMe SSD"},
    "15B7": {"5009": "WD Black NVMe", "5003": "WD Blue SN550"},
    "1B21": {"1142": "ASM1142 USB 3.1", "0612": "ASM1062 SATA"},
}


def pci_vendor_name(vid: str) -> str:
    """Nome do fabricante para um vendor ID (hex). Nunca lança."""
    vendor = (vid or "").upper().zfill(4)
    return _VENDORS.get(vendor, f"Fabricante PCI {vendor}")


def pci_device_name(vid: str, pid: str) -> str:
    """Nome do dispositivo PCI para vendor/device (hex). Nunca lança."""
    vendor = (vid or "").upper().zfill(4)
    device = (pid or "").upper().zfill(4)
    table = _DEVICES.get(vendor, {})
    return table.get(device, f"{pci_vendor_name(vendor)} (PCI {device})")


def pci_lookup(vid: str, pid: str) -> Tuple[str, str]:
    """Retorna (vendor, device) nomeados."""
    return pci_vendor_name(vid), pci_device_name(vid, pid)


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
                  f"{data['vendors']} fabricantes e {data['devices']} dispositivos PCI",
                  data, "pci.database")


register(Probe("pci.database", "Base de IDs PCI disponível",
               _run_db_probe, priority=95))