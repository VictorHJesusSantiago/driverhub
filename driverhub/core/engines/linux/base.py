# -*- coding: utf-8 -*-
"""Motor de drivers do Linux: detecção de distro e delegação a helpers.

Detecta a distribuição via ``/etc/os-release`` (com fallback), identifica o
gerenciador de pacotes e delega instalação/remoção para os módulos auxiliares
do subpacote (:mod:`.kmod`, :mod:`.modprobe`, :mod:`.fwupd`, etc.).
"""
from __future__ import annotations

import os
import re
import shutil
from typing import Any, Dict, List

from ..base import DriverEngine

#: Distro -> gerenciador de pacotes associado.
_PM_BY_ID = {
    "debian": "apt", "ubuntu": "apt", "linuxmint": "apt", "pop": "apt",
    "raspbian": "apt", "elementary": "apt",
    "fedora": "dnf", "rhel": "dnf", "centos": "dnf", "rocky": "dnf",
    "almalinux": "dnf", "amzn": "dnf",
    "arch": "pacman", "manjaro": "pacman", "endeavouros": "pacman",
    "opensuse": "zypper", "suse": "zypper",
    "alpine": "apk", "void": "xbps-install", "gentoo": "emerge",
}

_PM_BINARIES = ("apt", "apt-get", "dnf", "yum", "pacman", "zypper",
                "apk", "xbps-install", "emerge", "nix-env")


def _read_os_release() -> Dict[str, str]:
    info: Dict[str, str] = {}
    try:
        with open("/etc/os-release", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or "=" not in line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                info[key] = value
    except Exception:
        pass
    return info


def detect_distro() -> Dict[str, Any]:
    """Detecta a distribuição Linux (os-release + fallback). Nunca lança."""
    info = _read_os_release()
    if not info.get("ID") and os.path.exists("/etc/debian_version"):
        info["ID"] = "debian"
        info["NAME"] = "Debian GNU/Linux"
    if not info.get("ID") and os.path.exists("/etc/redhat-release"):
        info["ID"] = "rhel"
    if not info.get("ID"):
        info["ID"] = platform_id_fallback()
    pretty = info.get("PRETTY_NAME") or info.get("NAME") or info["ID"] or "Linux"
    id_like = info.get("ID_LIKE", "")
    return {
        "id": (info.get("ID") or "").lower(),
        "name": pretty,
        "pretty_name": pretty,
        "version": info.get("VERSION_ID", ""),
        "version_codename": info.get("VERSION_CODENAME", ""),
        "id_like": [i for i in id_like.split() if i],
        "source": "os-release" if info.get("ID") else "fallback",
    }


def platform_id_fallback() -> str:
    """Fallback: infere ID pela presença de arquivos clássicos de distro."""
    checks = (
        ("/etc/arch-release", "arch"),
        ("/etc/fedora-release", "fedora"),
        ("/etc/SuSE-release", "opensuse"),
        ("/etc/alpine-release", "alpine"),
        ("/etc/gentoo-release", "gentoo"),
        ("/etc/debian_version", "debian"),
    )
    for path, distro_id in checks:
        if os.path.exists(path):
            return distro_id
    return "linux"


def detect_package_manager() -> str:
    """Retorna o gerenciador de pacotes da distro ("" se desconhecido)."""
    info = detect_distro()
    candidates = [info.get("id", "")] + info.get("id_like", [])
    for candidate in candidates:
        cand = candidate.lower()
        for key, pm in _PM_BY_ID.items():
            if key == cand:
                return pm
        for pattern, pm in (("debian", "apt"), ("ubuntu", "apt"),
                            ("fedora", "dnf"), ("arch", "pacman"),
                            ("suse", "zypper")):
            if pattern in cand:
                return pm
    for binary in _PM_BINARIES:
        if shutil.which(binary):
            return binary
    return ""


def is_root() -> bool:
    """True se o processo roda como root (uid == 0)."""
    if hasattr(os, "geteuid"):
        try:
            return os.geteuid() == 0
        except Exception:
            return False
    return False


def kernel_release() -> str:
    """Versão do kernel (``uname -r``) com fallback simples."""
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8",
                  errors="replace") as fh:
            return fh.read().strip()
    except Exception:
        import platform as _platform  # lazy
        return _platform.release()


class LinuxEngine(DriverEngine):
    """Motor de drivers para distribuições Linux."""

    name = "linux"
    label = "Motor Linux (kmod / DKMS / fwupd)"

    def distro(self) -> Dict[str, Any]:
        return detect_distro()

    def package_manager(self) -> str:
        return detect_package_manager()

    def list_drivers(self) -> List[Dict[str, Any]]:
        """Lista módulos de kernel carregados + status DKMS."""
        from . import dkms, kmod  # lazy

        drivers: List[Dict[str, Any]] = []
        try:
            drivers.extend(kmod.lsmod())
        except Exception:
            pass
        try:
            drivers.extend(dkms.status())
        except Exception:
            pass
        return drivers

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lista dispositivos PCI/USB principais (fallback simples)."""
        return pci_devices() + usb_devices()

    def install_driver(self, target: str) -> Dict[str, Any]:
        """Carrega um módulo do kernel (nome) via modprobe."""
        from . import modprobe  # lazy
        return modprobe.load_module(target)

    def remove_driver(self, target: str, force: bool = False) -> Dict[str, Any]:
        """Descarrega um módulo do kernel via modprobe -r."""
        from . import modprobe  # lazy
        return modprobe.unload_module(target)

    def update_driver(self, target: str, source: str = "") -> Dict[str, Any]:
        """Recarrega um módulo do kernel (rmmod + modprobe)."""
        from . import modprobe  # lazy
        return modprobe.reload_module(target)

    def scan_devices_and_drivers(self) -> Dict[str, Any]:
        return {
            "devices": self.list_devices(),
            "drivers": self.list_drivers(),
            "distro": detect_distro(),
            "package_manager": detect_package_manager(),
            "root": is_root(),
        }

    def firmware_status(self) -> Dict[str, Any]:
        """Status do fwupd (firmware do sistema)."""
        from . import fwupd  # lazy
        return fwupd.get_updates()

    def dkms_status(self) -> Dict[str, Any]:
        """Status DKMS consolidado."""
        from . import dkms  # lazy
        return {"ok": True, "modules": dkms.status()}


def _run_cmd(args: List[str], timeout: int = 30) -> str:
    import subprocess  # lazy
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def pci_devices() -> List[Dict[str, Any]]:
    """Lista dispositivos PCI via ``lspci -nn`` (vazio se indisponível)."""
    if not shutil.which("lspci"):
        return []
    out = _run_cmd(["lspci", "-nn"], timeout=30)
    devices: List[Dict[str, Any]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        slot = parts[0]
        desc = re.sub(r"\[[0-9a-f]{4}:[0-9a-f]{4}\]", "", parts[1]).strip() \
            if len(parts) > 1 else ""
        kind = _guess_kind(desc)
        devices.append({"id": slot, "name": desc or slot, "kind": kind,
                        "driver_id": slot, "status": "ok",
                        "source": "linux:lspci"})
    return devices


def usb_devices() -> List[Dict[str, Any]]:
    """Lista dispositivos USB via ``lsusb`` (vazio se indisponível)."""
    if not shutil.which("lsusb"):
        return []
    out = _run_cmd(["lsusb"], timeout=30)
    devices: List[Dict[str, Any]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        devices.append({"id": line.split()[5] if len(line.split()) > 5 else line,
                        "name": line.strip(), "kind": "usb",
                        "driver_id": "", "status": "ok",
                        "source": "linux:lsusb"})
    return devices


def _guess_kind(desc: str) -> str:
    low = desc.lower()
    if "vga" in low or "display controller" in low or "3d controller" in low:
        return "gpu"
    if "audio" in low or "sound" in low:
        return "audio"
    if "ethernet" in low or "wi-fi" in low or "network controller" in low \
            or "wireless" in low:
        return "network"
    if "usb" in low:
        return "usb"
    if "sata" in low or "nvme" in low or "storage" in low or "raid" in low:
        return "storage"
    if "bluetooth" in low:
        return "bluetooth"
    if "camera" in low:
        return "camera"
    if "printer" in low:
        return "printer"
    if "processor" in low or "cpu" in low:
        return "cpu"
    return "pci"