# -*- coding: utf-8 -*-
"""Motor de drivers nativo do Linux (kernel modules e hardware).

Usa ``lspci``/``lsusb`` para inventário, ``lsmod``/``modinfo``/``modprobe``
para módulos do kernel e o gerenciador de pacotes da distro para drivers
empacotados. Nunca lança exceção; retorna estruturas vazias em caso de erro.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .platform import _run, _full_cmd

DISTRO_PM: Dict[str, str] = {
    "debian": "apt", "ubuntu": "apt", "linuxmint": "apt", "elementary": "apt",
    "raspbian": "apt", "pop": "apt", "kde neon": "apt",
    "fedora": "dnf", "rhel": "dnf", "centos": "dnf", "almalinux": "dnf",
    "rocky": "dnf", "arch": "pacman", "manjaro": "pacman", "endeavouros": "pacman",
    "opensuse": "zypper", "suse": "zypper", "void": "xbps-install",
    "alpine": "apk", "gentoo": "emerge", "nixos": "nix",
}


def _detect_pm() -> tuple[str, str]:
    id_like = ""
    try:
        for line in open("/etc/os-release", encoding="utf-8", errors="replace"):
            if line.startswith("ID_LIKE="):
                id_like = line.split("=", 1)[1].strip().strip('"').lower()
            if line.startswith("ID="):
                id_like = (id_like or line.split("=", 1)[1].strip().strip('"').lower())
    except Exception:
        pass
    for key, pm in DISTRO_PM.items():
        if key in id_like:
            return pm, id_like
    for name in ("apt", "dnf", "yum", "pacman", "zypper", "apk", "nix-env"):
        if _full_cmd(name):
            return name, id_like
    return "", id_like


def detect_os_family() -> Dict[str, Any]:
    pm, id_like = _detect_pm()
    return {"package_manager": pm, "id_like": id_like}


def kernel_modules() -> List[Dict[str, Any]]:
    """Módulos do kernel carregados com seus detalhes."""
    out = _run(["lsmod"], timeout=30)
    mods: List[Dict[str, Any]] = []
    lines = out.splitlines()[1:]  # pula header
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        size = parts[1] if len(parts) > 1 else ""
        used = parts[2] if len(parts) > 2 else ""
        info = _run(["modinfo", name], timeout=20)
        version = _re_first(info, r"^version:\s*(.*)", default="")
        author = _re_first(info, r"^author:\s*(.*)", default="")
        desc = _re_first(info, r"^description:\s*(.*)", default="")
        alias = _re_first(info, r"^alias:\s*(.*)", default="")
        mods.append({
            "id": name, "name": name, "version": version, "author": author,
            "description": desc, "alias": alias, "size": size, "used_by": used,
            "status": "loaded", "source": f"kernel:{name}",
        })
    return mods


def _re_first(text: str, pattern: str, default: str = "") -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default


def module_details(name: str) -> Dict[str, Any]:
    info = _run(["modinfo", name], timeout=20)
    return {
        "id": name, "name": name,
        "version": _re_first(info, r"^version:\s*(.*)"),
        "author": _re_first(info, r"^author:\s*(.*)"),
        "description": _re_first(info, r"^description:\s*(.*)"),
        "params": _re_first(info, r"^parm:\s*(.*)"),
        "alias": _re_first(info, r"^alias:\s*(.*)"),
        "signer": _re_first(info, r"^sig_key:\s*(.*)"),
        "filename": _re_first(info, r"^filename:\s*(.*)"),
    }


def devices() -> List[Dict[str, Any]]:
    """Inventário de hardware PCI/USB/block."""
    result: List[Dict[str, Any]] = []
    out = _run(["lspci", "-nn", "-D"], timeout=40)
    for line in out.splitlines():
        name = re.sub(r"\[[0-9a-f]{4}:[0-9a-f]{4}\]", "", line).strip()
        pci = line.split()[0] if line else ""
        low = name.lower()
        result.append({
            "kind": "pci", "name": name, "vendor": _vendor_of(low),
            "driver_id": pci, "driver_version": "", "status": "ok",
        })
    usb = _run(["lsusb"], timeout=30)
    for line in usb.splitlines():
        result.append({
            "kind": "usb", "name": line.strip(), "vendor": "USB Device",
            "driver_id": "", "driver_version": "", "status": "ok",
        })
    return result


def _vendor_of(low: str) -> str:
    if "intel" in low: return "Intel"
    if "amd" in low or "advanced micro devices" in low: return "AMD"
    if "nvidia" in low: return "NVIDIA"
    if "realtek" in low: return "Realtek"
    if "broadcom" in low: return "Broadcom"
    if "qualcomm" in low: return "Qualcomm"
    if "qualcomm atheros" in low: return "Qualcomm Atheros"
    if "mediatek" in low: return "MediaTek"
    if "samsung" in low: return "Samsung"
    if "marvell" in low: return "Marvell"
    if "mic" in low or "wavesystem" in low: return "Microchip"
    return "Unknown"


def install_module(name: str, permanent: bool = False) -> Dict[str, Any]:
    out = _run(["modprobe", "-v", name], timeout=40)
    ok = "FATAL" not in out.upper() and "error" not in out.lower()
    if ok:
        sys_out = "Systemd"
        if permanent:
            _run(["sh", "-c", f"mkdir -p /etc/modules-load.d && echo '{name}' "
                              f">> /etc/modules-load.d/driverhub.conf"], timeout=20)
        return {"ok": True,
                "detail": f"Módulo {name} carregado" + (". Persistência ativada." if permanent else ""),
                "output": out}
    return {"ok": False, "detail": out or f"Falha ao carregar {name}", "output": out}


def unload_module(name: str, persistent: bool = False) -> Dict[str, Any]:
    out = _run(["modprobe", "-rv", name], timeout=40)
    ok = "error" not in out.lower()
    if persistent:
        _run(["sh", "-c", f"sed -i '/^{name}$/d' /etc/modules-load.d/driverhub.conf"], timeout=20)
    return {"ok": ok, "detail": out or f"Módulo {name} descarregado",
            "output": out}


def remove_module_package(name: str) -> Dict[str, Any]:
    pm, _ = _detect_pm()
    if not pm:
        return {"ok": False, "detail": "Nenhum gerenciador de pacotes detectado."}
    cmd = {
        "apt": ["apt", "remove", "-y", name],
        "dnf": ["dnf", "remove", "-y", name],
        "yum": ["yum", "remove", "-y", name],
        "pacman": ["pacman", "-Rns", "--noconfirm", name],
        "zypper": ["zypper", "remove", "-y", name],
        "apk": ["apk", "del", name],
        "xbps-install": ["xbps-remove", "-y", name],
        "emerge": ["emerge", "--unmerge", name],
    }.get(pm, [])
    if not cmd:
        return {"ok": False, "detail": f"PM {pm} não suportado para remoção."}
    out = _run(cmd, timeout=300)
    ok = "error" not in out.lower() or "unable to locate" not in out.lower()
    return {"ok": ok, "detail": out.strip() or f"Removido via {pm}", "output": out}


def installed_driver_packages() -> List[Dict[str, Any]]:
    """Pacotes candidatos a driver instalados (linux-*-modules etc.)."""
    pm, _ = _detect_pm()
    pkgs: List[Dict[str, Any]] = []
    queries = {
        "apt": ["dpkg", "-l"],
        "dnf": ["dnf", "list", "installed"],
        "yum": ["yum", "list", "installed"],
        "pacman": ["pacman", "-Q"],
        "zypper": ["zypper", "se", "-i"],
        "apk": ["apk", "info", "-e", "*"],
    }
    cmd = queries.get(pm)
    if not cmd:
        return pkgs
    out = _run(cmd, timeout=120)
    for line in out.splitlines():
        low = line.lower()
        if ("firmware" in low or "linux-modules" in low or "nvidia" in low
                or "never" in low or "intel" in low or "amd" in low
                or "realtek" in low or "mesa" in low
                or "va-driver" in low or "vulkan" in low):
            name = low.split()[0] if low else line
            pkgs.append({
                "id": name, "name": name, "provider": "Distro",
                "version": "", "status": "installed",
                "source": f"linux:{pm}", "class": "package",
            })
    return pkgs


def scan_devices_and_drivers() -> Dict[str, Any]:
    pm = detect_os_family()
    return {
        "devices": devices(),
        "drivers": kernel_modules() + installed_driver_packages(),
        "os_extra": pm,
    }