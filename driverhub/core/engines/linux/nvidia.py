# -*- coding: utf-8 -*-
"""Helpers do driver NVIDIA no Linux.

Verifica se o driver está instalado, obtém a versão via ``nvidia-smi`` e
sugere o pacote de instalação conforme a distribuição (apt/dnf/pacman...).
Nunca lança exceção.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List

#: Sugestão de pacote por distribuição/gerenciador.
_INSTALL_HINTS: Dict[str, Dict[str, str]] = {
    "apt": {"package": "nvidia-driver", "note": "Debian/Ubuntu: nvidia-driver"},
    "dnf": {"package": "akmod-nvidia", "note": "Fedora/RHEL: akmod-nvidia (RPM Fusion)"},
    "yum": {"package": "akmod-nvidia", "note": "RHEL/CentOS: akmod-nvidia"},
    "pacman": {"package": "nvidia", "note": "Arch/Manjaro: nvidia ou nvidia-dkms"},
    "zypper": {"package": "nvidia-driver-G06", "note": "openSUSE: nvidia-driver-G06"},
    "apk": {"package": "nvidia-driver", "note": "Alpine: nvidia-driver"},
    "emerge": {"package": "x11-drivers/nvidia-drivers",
               "note": "Gentoo: x11-drivers/nvidia-drivers"},
}


def _run(args: List[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def driver_installed() -> Dict[str, Any]:
    """Verifica se o driver NVIDIA está instalado/em uso."""
    probes: Dict[str, bool] = {
        "nvidia-smi": bool(shutil.which("nvidia-smi")),
        "sysfs_proc": os.path.isdir("/proc/driver/nvidia"),
        "sysfs_class": os.path.isdir("/sys/class/drm") and _has_nvidia_card(),
        "module": _module_loaded("nvidia"),
    }
    installed = any(probes.values())
    return {"ok": installed, "installed": installed, "probes": probes,
            "detail": "Driver NVIDIA detectado." if installed else
                      "Driver NVIDIA não detectado."}


def _has_nvidia_card() -> bool:
    try:
        for entry in os.listdir("/sys/class/drm"):
            if "nvidia" in entry.lower():
                return True
    except Exception:
        pass
    lines = _run(["lspci", "-nn"])
    return "nvidia" in lines.lower()


def _module_loaded(module: str) -> bool:
    from . import lsmod  # lazy
    try:
        return module in lsmod.loaded_modules()
    except Exception:
        return False


def driver_version() -> Dict[str, Any]:
    """Obtém a versão do driver via ``nvidia-smi --query-gpu=driver_version``."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"ok": False, "version": "", "detail": "nvidia-smi não encontrado."}
    out = _run([exe, "--query-gpu=driver_version", "--format=csv,noheader"],
               timeout=30)
    version = ""
    for line in (out or "").splitlines():
        candidate = line.strip()
        if re.match(r"^\d+\.\d+(\.\d+)?", candidate):
            version = candidate
            break
    return {"ok": bool(version), "version": version,
            "detail": version or "Não foi possível ler a versão.",
            "raw": out}


def install_hint(dist: str = "") -> Dict[str, Any]:
    """Sugere o pacote NVIDIA apropriado para ``dist`` (id_like ou "").

    Se ``dist`` vazio, detecta via os-release. Retorna dict com pacote/nota.
    """
    from .base import detect_distro  # lazy

    if not dist:
        info = detect_distro()
        candidates = [info.get("id", "")] + info.get("id_like", [])
        dist = " ".join(candidates)

    dist_lower = dist.lower()
    pm = ""
    if any(k in dist_lower for k in ("debian", "ubuntu", "pop", "mint", "raspbian")):
        pm, chosen = "apt", _INSTALL_HINTS["apt"]
    elif any(k in dist_lower for k in ("fedora", "rhel", "centos", "rocky", "alma")):
        pm, chosen = "dnf", _INSTALL_HINTS["dnf"]
    elif any(k in dist_lower for k in ("arch", "manjaro", "endeavouros")):
        pm, chosen = "pacman", _INSTALL_HINTS["pacman"]
    elif any(k in dist_lower for k in ("suse", "opensuse")):
        pm, chosen = "zypper", _INSTALL_HINTS["zypper"]
    else:
        from .base import detect_package_manager  # lazy
        pm = detect_package_manager()
        chosen = _INSTALL_HINTS.get(pm, {"package": "nvidia-driver",
                                         "note": "Consulte a documentação da distro."})

    return {"ok": bool(pm), "pm": pm, "package": chosen["package"],
            "note": chosen["note"],
            "detail": f"Instale via {pm or 'seu gerenciador'}: "
                      f"{chosen['package']} — {chosen['note']}"}


def gpu_models() -> List[str]:
    """Lista modelos NVIDIA via ``nvidia-smi --query-gpu=name``."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    out = _run([exe, "--query-gpu=name", "--format=csv,noheader"], timeout=30)
    return [line.strip() for line in (out or "").splitlines() if line.strip()]