# -*- coding: utf-8 -*-
"""Motor de drivers nativo do macOS.

O gerenciamento de drivers no macOS é feito praticamente todo pelo sistema
(motoristas nativos da Apple). Aqui listamos extensions (kexts), pacotes de
drivers de terceiros e hardware. Nunca lança exceção.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .platform import _run


def kexts() -> List[Dict[str, Any]]:
    """Extensions do kernel atualmente carregadas (quando permitido pelo SIP)."""
    out = _run(["kextstat"], timeout=40)
    result: List[Dict[str, Any]] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        addr = parts[0]
        name = parts[5].split("/")[-1] if len(parts) > 5 else ""
        bundle = parts[5] if len(parts) > 5 else ""
        result.append({
            "id": name, "name": name, "version": parts[4] if len(parts) > 4 else "",
            "provider": "Apple/Third-party", "status": "loaded",
            "bundle": bundle, "address": addr, "source": "macos:kextstat",
        })
    return result


def installed_driver_pkgs() -> List[Dict[str, Any]]:
    """Pacotes de driver conhecidos instalados (KEXTs de terceiros)."""
    out = _run(["sh", "-c",
                "ls /Library/Extensions /System/Library/Extensions 2>/dev/null | "
                "grep -v '\\.\\|DS_Store'"], timeout=20)
    pkgs: List[Dict[str, Any]] = []
    for line in out.splitlines():
        name = line.strip()
        if name:
            pkgs.append({"id": name, "name": name, "provider": "Third-party",
                         "version": "", "status": "installed",
                         "source": "macos:kexts", "class": "kext"})
    return pkgs


def devices() -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for prof in ("SPHardwareDataType", "SPDisplaysDataType", "SPNetworkDataType",
                 "SPAudioDataType", "SPBluetoothDataType"):
        out = _run(["system_profiler", prof], timeout=60)
        name = ""
        for line in out.splitlines():
            if ":" in line and name == "":
                name = line.split(":", 1)[1].strip()
                break
        if name:
            result.append({"kind": "device", "name": name, "vendor": "Apple",
                           "driver_id": "", "driver_version": "", "status": "ok"})
    return result


def scan_devices_and_drivers() -> Dict[str, Any]:
    return {"devices": devices(), "drivers": installed_driver_pkgs()}