# -*- coding: utf-8 -*-
"""Sondas WMI/CIM do Windows via Get-CimInstance (com fallback wmic).

Nenhuma função lança exceção: falhas retornam estruturas vazias ou
``ok=False`` com mensagem descritiva.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

_CIM_CLASSES = (
    ("ComputerSystem", "Manufacturer,Model,SystemFamily,TotalPhysicalMemory,PCSystemType"),
    ("Processor", "Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed"),
    ("VideoController", "Name,AdapterCompatibility,DriverVersion,DriverDate"),
    ("DiskDrive", "Model,SerialNumber,Size,InterfaceType"),
    ("BIOS", "Manufacturer,SMBIOSBIOSVersion,ReleaseDate"),
    ("NetworkAdapter", "Name,MACAddress,NetEnabled,Speed"),
)


def cim_instances(class_name: str, props: str = "*") -> List[Dict[str, Any]]:
    """Lista instâncias de uma classe CIM via PowerShell; fallback wmic."""
    if not sys.platform.startswith("win"):
        return []
    out = _ps_query(class_name, props)
    if not out:
        out = _wmic_query(class_name, props)
    return _parse_list(out)


def _ps_query(class_name: str, props: str) -> str:
    script = (f"Get-CimInstance -ClassName {class_name} | "
              f"Select-Object -Property {props} | Format-List")
    res = run_command(["powershell", "-NoProfile", "-NonInteractive",
                       "-Command", script], 90)
    return res["data"]


def _wmic_query(class_name: str, props: str) -> str:
    res = run_command(["wmic", class_name, "get", props, "/value"], 90)
    return res["data"]


def _parse_list(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    items: List[Dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", text):
        entry: Dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
            elif "=" in line:
                key, _, value = line.partition("=")
            else:
                continue
            key = key.strip()
            if key and key not in entry:
                entry[key] = value.strip()
        if entry:
            items.append(entry)
    return items


def wmi_hardware() -> Dict[str, Any]:
    """Coleta um inventário WMI básico de classes CIM comuns."""
    inventory: Dict[str, Any] = {}
    for label, props in _CIM_CLASSES:
        inventory[label] = cim_instances(label, props)
    total = sum(1 for values in inventory.values() if values)
    return {"ok": total > 0,
            "detail": f"{total} classes CIM consultadas", "data": inventory}


def probe_registry() -> Dict[str, Any]:
    """Sonda rápida do nome de produto na chave de versão do Windows."""
    res = run_command([
        "reg", "query", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion",
        "/v", "ProductName"], 30)
    product = ""
    for line in res["data"].splitlines():
        if "ProductName" in line and "REG_" in line:
            product = line.split("REG_SZ", 1)[-1].strip()
            break
    return {"ok": res["ok"] or bool(product),
            "detail": f"Windows: {product or 'desconhecido'}",
            "data": {"product": product, "cmd_ok": res["ok"]}}


def _run_wmi_probe() -> Result:
    res = wmi_hardware()
    return Result(res["ok"], res["detail"], res["data"], "wmi.hardware")


def _run_reg_probe() -> Result:
    res = probe_registry()
    return Result(res["ok"], res["detail"], res["data"], "wmi.registry")


register(Probe("wmi.hardware", "Inventário WMI/CIM de hardware",
               _run_wmi_probe, priority=40))
register(Probe("wmi.registry", "Nome de produto do Windows via registro",
               _run_reg_probe, priority=90))