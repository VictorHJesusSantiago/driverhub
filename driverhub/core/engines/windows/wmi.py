# -*- coding: utf-8 -*-
"""Consultas WMI via ``wmic``/PowerShell ``Get-CimInstance``.

Traz a tabela de classes WMI mais usadas para hardware, consulta por classe
e uma varredura conveniente dos objetos Win32 mais comuns. As consultas
nunca lançam exceção e devolvem listas vazias em qualquer falha.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any, Dict, List

#: Tabela de nomes de classes WMI comuns (alias -> classe real).
WMI_CLASSES: Dict[str, str] = {
    "bios": "Win32_BIOS",
    "system": "Win32_ComputerSystem",
    "processor": "Win32_Processor",
    "video": "Win32_VideoController",
    "sound": "Win32_SoundDevice",
    "pnp": "Win32_PnPEntity",
    "disk": "Win32_DiskDrive",
    "network": "Win32_NetworkAdapter",
    "usb": "Win32_USBControllerDevice",
    "battery": "Win32_Battery",
    "printer": "Win32_Printer",
    "device": "Win32_PnPEntity",
}

#: Lista canônica de objetos Win32 consultados por :func:`win32_objects`.
WMI_OBJECTS: List[str] = [
    "Win32_BIOS", "Win32_ComputerSystem", "Win32_Processor",
    "Win32_VideoController", "Win32_SoundDevice", "Win32_PnPEntity",
    "Win32_DiskDrive", "Win32_NetworkAdapter", "Win32_USBControllerDevice",
    "Win32_Battery", "Win32_Printer",
]


def _resolve(class_name: str) -> str:
    """Resolve alias WMI para nome de classe real."""
    if not class_name:
        return ""
    key = class_name.strip().lower()
    if key in WMI_CLASSES:
        return WMI_CLASSES[key]
    if class_name.startswith("Win32_"):
        return class_name
    return f"Win32_{class_name}"


def _run_powershell(script: str, timeout: int = 60) -> str:
    from . import powershell  # lazy
    return powershell.powershell(script, timeout=timeout)


def query(class_name: str, timeout: int = 60) -> List[Dict[str, Any]]:
    """Consulta uma classe WMI (alias ou ``Win32_*``) e retorna lista de dicts.

    Usa PowerShell ``Get-CimInstance`` com JSON; se indisponível, tenta
    ``wmic``. Nunca lança.
    """
    wmi_class = _resolve(class_name)
    if not wmi_class:
        return []
    script = (
        f"Get-CimInstance -ClassName {wmi_class} -ErrorAction SilentlyContinue "
        "| Select-Object * -ExcludeProperty CimClass,CimInstanceProperties," +
        "CimSystemProperties | ConvertTo-Json -Compress -Depth 3"
    )
    out = _run_powershell(script, timeout=timeout)
    parsed = _parse_json_list(out)
    if parsed:
        return parsed
    return _query_wmic(wmi_class, timeout=timeout)


def _parse_json_list(out: str) -> List[Dict[str, Any]]:
    if not out:
        return []
    import json  # lazy
    try:
        data = json.loads(out)
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _query_wmic(wmi_class: str, timeout: int = 60) -> List[Dict[str, Any]]:
    exe = shutil.which("wmic") or shutil.which("wmic.exe")
    if not exe:
        return []
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([exe, wmi_class, "get", "/value"],
                              timeout=timeout, text=True,
                              errors="replace", **kwargs)
        return _parse_wmic(proc.stdout or "")
    except Exception:
        return []


def _parse_wmic(out: str) -> List[Dict[str, Any]]:
    """Converte saída ``wmic ... get /value`` em lista de dicts."""
    rows: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        line = line.strip()
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            current[key.strip()] = value.strip()
    if current:
        rows.append(current)
    return rows


def win32_objects() -> List[Dict[str, Any]]:
    """Varre objetos Win32 comuns e retorna o que foi coletado.

    Cada item inclui a classe WMI e os atributos obtidos. Nunca lança.
    """
    result: List[Dict[str, Any]] = []
    for wmi_class in WMI_OBJECTS:
        items = query(wmi_class, timeout=30)
        for item in items:
            item.setdefault("wmi_class", wmi_class)
            item.setdefault("source", "windows:wmi")
            result.append(item)
    return result


def table() -> Dict[str, str]:
    """Retorna a tabela alias -> classe WMI (apenas dados)."""
    return dict(WMI_CLASSES)