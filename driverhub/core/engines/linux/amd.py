# -*- coding: utf-8 -*-
"""Helpers do driver AMD/AMDGPU no Linux (Mesa + amdgpu).

Verifica se a stack AMD está instalada, tenta obter a versão e sugere
instalação conforme a distribuição. Traz uma tabela de microarquiteturas
(vega, rdna1, rdna2, rdna3) para identificação de GPUs.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List

#: Microarquiteturas AMD com códigos e geração.
MICROARCHITECTURES: List[Dict[str, Any]] = [
    {"name": "Vega", "code": "gfx900", "generation": 5,
     "gpus": ["Vega 56", "Vega 64", "Radeon VII"]},
    {"name": "RDNA 1", "code": "gfx1010", "generation": 6,
     "gpus": ["RX 5500", "RX 5600", "RX 5700"]},
    {"name": "RDNA 2", "code": "gfx1030", "generation": 7,
     "gpus": ["RX 6000", "RX 6700", "RX 6800", "RX 6900"]},
    {"name": "RDNA 3", "code": "gfx1100", "generation": 8,
     "gpus": ["RX 7600", "RX 7700", "RX 7800", "RX 7900"]},
]

_INSTALL_HINTS: Dict[str, Dict[str, str]] = {
    "apt": {"package": "mesa", "note": "Debian/Ubuntu: mesa + linux-firmware"},
    "dnf": {"package": "mesa-dri-drivers",
            "note": "Fedora/RHEL: mesa-dri-drivers + kernel-firmware"},
    "yum": {"package": "mesa-dri-drivers", "note": "RHEL/CentOS: mesa"},
    "pacman": {"package": "mesa", "note": "Arch/Manjaro: mesa + xf86-video-amdgpu"},
    "zypper": {"package": "Mesa", "note": "openSUSE: Mesa + kernel-firmware-amdgpu"},
}


def _run(args: List[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def installed() -> Dict[str, Any]:
    """Verifica se a stack AMD (amdgpu/mesa) está presente."""
    probes: Dict[str, bool] = {
        "module_amdgpu": _module_loaded("amdgpu"),
        "sysfs_amdgpu": os.path.isdir("/sys/class/drm/card0/device/driver"),
        "lspci_amd": "advanced micro devices" in _run(["lspci"])
                     or "amd" in _run(["lspci"]).lower()[:2000],
        "vulkan_radeon": _has_icd("radeon"),
    }
    ok = any(probes.values()) and "true" in str(probes.get("module_amdgpu")
            or probes.get("lspci_amd"))
    detected = probes["module_amdgpu"] or probes["lspci_amd"]
    return {"ok": detected, "installed": detected, "probes": probes,
            "detail": "Stack AMD detectada." if detected else
                      "Stack AMD não detectada."}


def _module_loaded(module: str) -> bool:
    from . import lsmod  # lazy
    try:
        return module in lsmod.loaded_modules()
    except Exception:
        return False


def _has_icd(vendor: str) -> bool:
    for folder in ("/usr/share/vulkan/icd.d", "/etc/vulkan/icd.d"):
        if os.path.isdir(folder):
            try:
                for f in os.listdir(folder):
                    if vendor in f.lower():
                        return True
            except Exception:
                continue
    return False


def version() -> Dict[str, Any]:
    """Versão da stack AMD: modinfo amdgpu ou pacote Mesa.

    Retorna dict com ``version`` e ``source`` (pode vir vazio).
    """
    modinfo_version = _modinfo_field("amdgpu", "version")
    if modinfo_version:
        return {"ok": True, "version": modinfo_version,
                "source": "modinfo:amdgpu",
                "detail": f"amdgpu versão {modinfo_version}"}

    renderer = _run(["glxinfo", "-B"]) if shutil.which("glxinfo") else ""
    match = re.search(r"OpenGL version string:\s*([^\n]+)", renderer)
    if match:
        return {"ok": True, "version": match.group(1).strip(),
                "source": "glxinfo",
                "detail": "Versão OpenGL Mesa: " + match.group(1).strip()}
    return {"ok": False, "version": "", "source": "",
            "detail": "Não foi possível obter a versão AMD/Mesa."}


def _modinfo_field(module: str, field: str) -> str:
    if not shutil.which("modinfo"):
        return ""
    out = _run(["modinfo", module])
    for line in (out or "").splitlines():
        if line.lower().startswith(field + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def install_hint(dist: str = "") -> Dict[str, Any]:
    """Sugere o pacote AMD/Mesa apropriado para ``dist`` (id_like ou "")."""
    from .base import detect_distro  # lazy

    if not dist:
        info = detect_distro()
        candidates = [info.get("id", "")] + info.get("id_like", [])
        dist = " ".join(candidates)

    dist_lower = dist.lower()
    pm = ""
    if any(k in dist_lower for k in ("debian", "ubuntu", "pop", "mint")):
        pm, chosen = "apt", _INSTALL_HINTS["apt"]
    elif any(k in dist_lower for k in ("fedora", "rhel", "centos", "rocky")):
        pm, chosen = "dnf", _INSTALL_HINTS["dnf"]
    elif any(k in dist_lower for k in ("arch", "manjaro")):
        pm, chosen = "pacman", _INSTALL_HINTS["pacman"]
    elif any(k in dist_lower for k in ("suse", "opensuse")):
        pm, chosen = "zypper", _INSTALL_HINTS["zypper"]
    else:
        from .base import detect_package_manager  # lazy
        pm = detect_package_manager()
        chosen = _INSTALL_HINTS.get(pm, {"package": "mesa", "note": "Use mesa do seu SO."})

    return {"ok": bool(pm), "pm": pm, "package": chosen["package"],
            "note": chosen["note"],
            "detail": f"Instale via {pm or 'seu gerenciador'}: "
                      f"{chosen['package']} — {chosen['note']}"}


def detect_microarchitecture(gpu_name: str = "") -> Dict[str, Any]:
    """Tenta identificar a microarquitetura de uma GPU AMD (pelo nome)."""
    low = (gpu_name or "").lower()
    for arch in MICROARCHITECTURES:
        for gpu in arch["gpus"]:
            if gpu.lower() in low:
                return {"ok": True, "architecture": arch["name"],
                        "code": arch["code"], "generation": arch["generation"],
                        "detail": f"GPU {gpu_name} é {arch['name']} ({arch['code']})."}
    return {"ok": False, "architecture": "", "code": "", "generation": 0,
            "detail": "Microarquitetura não identificada."}


def architectures() -> List[str]:
    """Nomes das microarquiteturas AMD conhecidas."""
    return [arch["name"] for arch in MICROARCHITECTURES]