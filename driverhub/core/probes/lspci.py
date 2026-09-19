# -*- coding: utf-8 -*-
"""Sondas lspci (Linux): dispositivos PCI e nomes de classes.

``lspci_exec`` executa ``lspci -mmvnn`` (com fallbacks ``-mmnn``/``-mm``) e
``lspci_parse_mm`` estrutura a saída em registros com vendor/device.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

PCI_CLASSES: Dict[str, str] = {
    "00": "Dispositivo não-VGA", "01": "Controladora de armazenamento (SCSI/IDE)",
    "02": "Rede", "03": "Display/VGA", "04": "Multimídia", "05": "Memória",
    "06": "Bridge", "07": "Comunicação", "08": "Sistema genérico",
    "09": "Entrada", "0a": "Docking station", "0b": "Processador",
    "0c": "Serial", "0d": "Wireless", "0e": "I2O", "0f": "Satélite",
    "10": "Criptografia", "11": "Processamento de dados",
    "12": "Processamento de sinal", "13": "Não atribuída",
}


def lspci_exec() -> Dict[str, Any]:
    """Executa ``lspci -mmvnn`` e devolve a saída bruta."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "lspci disponível apenas no Linux.",
                "data": ""}
    from shutil import which as _which
    if not _which("lspci"):
        return {"ok": False, "detail": "binário lspci não encontrado.", "data": ""}
    res = run_command(["lspci", "-mmvnn"], 30)
    for flag in ("-mmnn", "-mm"):
        if not res["data"].strip():
            fallback = run_command(["lspci", flag], 30)
            if fallback["data"].strip():
                res = fallback
                break
    return {"ok": res["ok"] or bool(res["data"]), "detail": res["detail"],
            "data": res["data"]}


def lspci_parse_mm() -> Dict[str, Any]:
    """Executa e interpreta ``lspci -mmnn`` em registros estruturados."""
    result = lspci_exec()
    devices = _parse_mm(result["data"])
    return {"ok": bool(devices), "detail": f"{len(devices)} dispositivos PCI",
            "data": devices, "raw": result["data"]}


def _parse_mm(text: str) -> List[Dict[str, Any]]:
    """Interpreta registros ``-mm``: ``slot "classe" "vendor" "device" [id]``."""
    devices: List[Dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip() or line[:1].isspace():
            continue
        slot_match = re.match(r"\s*(\S+)\s", line)
        if not slot_match:
            continue
        slot = slot_match.group(1)
        quoted = re.findall(r"\"([^\"]*)\"", line)
        clean = re.sub(r"\"[^\"]*\"", "", line)
        ids = re.findall(r"\[([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})\]", clean)
        vid = ids[0][0].upper() if ids else ""
        pid = ids[0][1].upper() if ids else ""
        desc = quoted[0] if quoted else ""
        devices.append({
            "slot": slot,
            "class": desc,
            "class_name": _class_name(desc),
            "vendor": quoted[1] if len(quoted) > 1 else "",
            "device": quoted[2] if len(quoted) > 2 else "",
            "vid": vid, "pid": pid,
            "pci_id": f"{vid}:{pid}" if vid else "",
        })
    return devices


def _class_name(desc: str) -> str:
    low = desc.lower()
    if "vga" in low or "display" in low or "3d" in low:
        return "Display"
    if "bridge" in low:
        return "Bridge"
    if "ethernet" in low or "network" in low or "wi-fi" in low or "wlan" in low:
        return "Rede"
    if "audio" in low or "multimedia" in low:
        return "Multimídia"
    if "usb" in low or "sata" in low or "ahci" in low or "nvme" in low:
        return "Armazenamento/Serial"
    if "memory" in low or "ram" in low:
        return "Memória"
    return ""


def pci_class_name(class_id: str) -> str:
    """Nome de classe PCI pelo primeiro byte do class code (ex.: '03') ."""
    return PCI_CLASSES.get((class_id or "")[:2].lower(), "")


def _run_lspci_probe() -> Result:
    res = lspci_parse_mm()
    return Result(res["ok"], res["detail"], res["data"], "lspci.devices")


register(Probe("lspci.devices", "Dispositivos PCI via lspci -mmnn",
               _run_lspci_probe, priority=30))