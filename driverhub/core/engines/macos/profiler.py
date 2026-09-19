# -*- coding: utf-8 -*-
"""``system_profiler`` no macOS: hardware, displays, PCI e rede.

helpers que executam ``system_profiler -detailLevel basic -json <tipo>``
quando possível, com fallback para texto. Nunca lançam exceção.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 120) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def system_profiler(category: str = "SPHardwareDataType",
                    detail_level: str = "basic") -> str:
    """Executa ``system_profiler -detailLevel <n> <category>``.

    Retorna o texto bruto ("" se o comando falhar / plataforma errada).
    """
    if not shutil.which("system_profiler"):
        return ""
    detail = detail_level if detail_level in ("mini", "basic", "full") else "basic"
    return _run(["system_profiler", f"-detailLevel {detail}".split(), category][:2]
                + [category.lstrip("SP").lstrip()], timeout=120)


def displays() -> List[Dict[str, Any]]:
    """Displays externos/embutidos (SPDisplaysDataType)."""
    out = system_profiler("SPDisplaysDataType")
    displays_list: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Chipset Model") or stripped.startswith("  Chipset Model"):
            if current:
                displays_list.append(current)
            current = {"name": stripped.split(":", 1)[1].strip(),
                       "source": "macos:system_profiler"}
        elif ":" in stripped and " " not in stripped[:5]:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
    if current:
        displays_list.append(current)
    return displays_list or [dict(name="(sem exibição detectada)")]


def pci_devices() -> List[Dict[str, Any]]:
    """Dispositivos PCI (SPPCIDataType) relevantes p/ drivers."""
    out = system_profiler("SPPCIDataType")
    devices: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("  ", "\t")) \
                and "Device Name" not in stripped and not stripped.startswith("PCI")\
                and ":" in stripped[:30]:
            if current:
                devices.append(current)
            current = {"name": stripped, "source": "macos:system_profiler"}
        elif ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
    if current:
        devices.append(current)
    return devices


def storage() -> List[Dict[str, Any]]:
    """Dispositivos de armazenamento (SPStorageDataType)."""
    out = system_profiler("SPStorageDataType")
    devices: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("  ", "\t")) and ":" in stripped[:60]:
            if current:
                devices.append(current)
            current = {"name": stripped, "source": "macos:system_profiler"}
        elif ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
    if current:
        devices.append(current)
    return devices


def ethernet() -> List[Dict[str, Any]]:
    """Interfaces de rede com hardware (SPNetworkDataType)."""
    out = system_profiler("SPNetworkDataType")
    ifs: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Hardware") or stripped.startswith("  Hardware"):
            key, _, value = stripped.partition(":")
            current["hardware"] = value.strip()
        elif stripped.startswith("Type"):
            key, _, value = stripped.partition(":")
            current["type"] = value.strip()
        elif stripped and not stripped.startswith(("  ", "\t")) and ":" in stripped[:40]:
            if current:
                ifs.append(current)
            current = {"name": stripped}
    if current:
        ifs.append(current)
    return ifs


def memory() -> Dict[str, Any]:
    """Resumo de memória via SPHardwareDataType"""
    out = system_profiler("SPHardwareDataType")
    return {"ok": bool(out), "type": "macos",
            "detail": out.splitlines()[0] if (out or "").splitlines() else ""}