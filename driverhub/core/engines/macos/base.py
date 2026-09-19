# -*- coding: utf-8 -*-
"""Motor de drivers do macOS: sw_vers, system_profiler e delegação.

No macOS os drivers de terceiros são KEXTs (legados) e pacotes .pkg; a
maioria do hardware usa drivers Apple incorporados. O motor expõe helpers de
``sw_vers``/``system_profiler`` e delega para os módulos do subpacote.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List

from ..base import DriverEngine

_COMMON_PROFILER_TYPES = ("SPHardwareDataType", "SPDisplaysDataType",
                          "SPPCIDataType", "SPStorageDataType",
                          "SPNetworkDataType")


class MacOSEngine(DriverEngine):
    """Motor de drivers para macOS (SIP limita carregamento de KEXTs)."""

    name = "macos"
    label = "Motor macOS (system_profiler / kextstat)"

    # ----- helpers do SO -----
    def sw_vers(self) -> Dict[str, Any]:
        """Executa ``sw_vers`` e retorna produto/versão/build."""
        return sw_vers()

    def system_profiler(self, category: str = "SPHardwareDataType") -> str:
        """Executa ``system_profiler`` e retorna texto bruto ("" em falha)."""
        from . import profiler  # lazy
        return profiler.system_profiler(category)

    def is_admin(self) -> bool:
        """No macOS, não há modo 'admin' para drivers (root via sudo)."""
        import os  # lazy
        try:
            return os.geteuid() == 0  # type: ignore[attr-defined]
        except Exception:
            return False

    # ----- interface comum -----
    def list_drivers(self) -> List[Dict[str, Any]]:
        """Lista KEXTs carregadas + pacotes de driver instalados."""
        from . import kext, pkgutil  # lazy

        drivers: List[Dict[str, Any]] = []
        try:
            drivers.extend(kext.kextstat())
        except Exception:
            pass
        try:
            for pkg in pkgutil.packages():
                if any(tok in pkg.lower() for tok in ("kext", "driver", "gpu", "audio")):
                    drivers.append({"id": pkg, "name": pkg, "version": "",
                                    "status": "installed",
                                    "source": "macos:pkgutil"})
        except Exception:
            pass
        return drivers

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lista hardware via system_profiler (displays, PCI, storage...)."""
        from . import profiler  # lazy
        devices: List[Dict[str, Any]] = []
        try:
            devices.extend(profiler.displays())
        except Exception:
            pass
        try:
            devices.extend(profiler.pci_devices())
        except Exception:
            pass
        return devices

    def install_driver(self, target: str) -> Dict[str, Any]:
        """Instala um KEXT/package driver (requer SIP desativado + admin)."""
        return {"ok": False,
                "detail": "macOS gerencia drivers nativamente; instalação "
                          "manual de KEXT exige SIP desativado (csrutil "
                          "disable) e reinicialização."}

    def remove_driver(self, target: str, force: bool = False) -> Dict[str, Any]:
        """Remoção de KEXT (requer SIP desativado)."""
        return {"ok": False,
                "detail": "Remoção de KEXT não é suportada na instalação "
                          "padrão (SIP ativo)."}

    def update_driver(self, target: str, source: str = "") -> Dict[str, Any]:
        """Atualização via Software Update / pacotes Apple."""
        return {"ok": False,
                "detail": "Use 'softwareupdate' ou o App Store para "
                          "atualizar drivers de sistema no macOS."}

    def scan_devices_and_drivers(self) -> Dict[str, Any]:
        return {
            "devices": self.list_devices(),
            "drivers": self.list_drivers(),
            "os_extra": {"sw_vers": sw_vers(), "admin": self.is_admin()},
        }

    def software_update_list(self) -> List[str]:
        """Lista atualizações de software pendentes (``softwareupdate -l``)."""
        from . import profiler  # lazy (reaproveita runner)
        out = _run(["softwareupdate", "-l"], timeout=120)
        return [line for line in (out or "").splitlines() if line.strip()]


def _run(args: List[str], timeout: int = 60) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def sw_vers() -> Dict[str, Any]:
    """Executa ``sw_vers`` e retorna dict com ProductName/Version/Build."""
    if not (shutil.which("sw_vers")):
        return {"ok": False, "product_name": "", "version": "", "build": "",
                "detail": "sw_vers não encontrado (não é macOS?)."}
    out = _run(["sw_vers"], timeout=30)
    result: Dict[str, str] = {}
    for line in (out or "").splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip().replace(" ", "_")] = value.strip()
    return {"ok": bool(result), "product_name": result.get("ProductName", ""),
            "version": result.get("ProductVersion", ""),
            "build": result.get("BuildVersion", ""),
            "raw": out,
            "detail": f"macOS {result.get('ProductVersion', '?')} "
                      f"({result.get('BuildVersion', '?')})" if result else
                      "Não foi possível ler sw_vers."}


def has_sip_enabled() -> bool:
    """Verifica se o SIP está ativo (``csrutil status``)."""
    if not shutil.which("csrutil"):
        return True
    out = _run(["csrutil", "status"], timeout=30)
    return "enabled" in (out or "").lower() and "disabled" not in (out or "").lower()