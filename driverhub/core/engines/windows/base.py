# -*- coding: utf-8 -*-
"""Motor de drivers do Windows: descoberta de ferramentas e delegação.

O motor expõe a interface comum de :class:`DriverEngine` e delega a lógica
para os módulos auxiliares do subpacote (:mod:`.pnputil`, :mod:`.dism`,
:mod:`.wmi`, etc.), todos importados de forma preguiçosa dentro das funções.
"""
from __future__ import annotations

import shutil
from typing import Any, Dict, List

from ..base import DriverEngine

#: Ferramentas nativas do Windows consultadas pelo motor.
_TOOLS = (
    "pnputil", "dism", "powershell", "wmic", "reg",
    "sc", "winget", "driverquery", "signtool",
)


class WindowsEngine(DriverEngine):
    """Motor de drivers para Windows 10/11 e Windows Server."""

    name = "windows"
    label = "Motor Windows (pnputil / DISM / WMI)"

    def discover_tools(self) -> Dict[str, str]:
        """Descobre o caminho das ferramentas de sistema disponíveis."""
        found: Dict[str, str] = {}
        for tool in _TOOLS:
            path = None
            for suffix in ("", ".exe"):
                path = shutil.which(tool + suffix)
                if path:
                    break
            found[tool] = path or ""
        return found

    def tool_path(self, tool: str) -> str:
        """Caminho de uma ferramenta específica (vazio se ausente)."""
        return self.discover_tools().get(tool, "")

    def is_admin(self) -> bool:
        """True se o processo atual roda como administrador."""
        from . import powershell  # lazy
        return powershell._routes_admin()

    def list_drivers(self) -> List[Dict[str, Any]]:
        """Lista drivers publicados no sistema (pnputil + DISM)."""
        from . import dism, pnputil  # lazy

        drivers: List[Dict[str, Any]] = []
        try:
            drivers.extend(pnputil.enum_drivers())
        except Exception:
            pass
        try:
            drivers.extend(dism.list_drivers())
        except Exception:
            pass
        return drivers

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lista dispositivos PnP/driverizados do sistema."""
        from . import pnputil  # lazy

        try:
            return pnputil.enum_devices()
        except Exception:
            return []

    def install_driver(self, target: str) -> Dict[str, Any]:
        """Instala um driver a partir de um .inf (DISM add-driver)."""
        from . import dism  # lazy

        if not target.lower().endswith(".inf"):
            return {"ok": False,
                    "detail": "Informe um arquivo .inf válido para instalação."}
        return dism.add_driver(target)

    def remove_driver(self, target: str, force: bool = False) -> Dict[str, Any]:
        """Remove um driver publicado (pubname ou nome do .inf)."""
        from . import dism  # lazy

        return dism.remove_driver(target)

    def update_driver(self, target: str, source: str = "") -> Dict[str, Any]:
        """Atualiza um driver; com ``source`` (.".inf") reinstala/atualiza."""
        from . import dism  # lazy

        if not source.lower().endswith(".inf"):
            return {"ok": False,
                    "detail": "Informe o .inf de origem para atualizar o driver."}
        result = dism.add_driver(source)
        result["detail"] = f"Atualização: {result.get('detail', '')}".strip()
        return result

    def scan_devices_and_drivers(self) -> Dict[str, Any]:
        """Coleta de dispositivos + drivers + ferramentas em um dict."""
        return {
            "devices": self.list_devices(),
            "drivers": self.list_drivers(),
            "tools": self.discover_tools(),
            "admin": self.is_admin(),
        }

    def backup(self, dest: str) -> Dict[str, Any]:
        """Exporta os drivers publicados para ``dest``."""
        from . import backup  # lazy
        return backup.export_drivers(dest)

    def restore(self, dest: str) -> Dict[str, Any]:
        """Reinstala drivers a partir de um diretório de backup."""
        from . import backup  # lazy
        return backup.import_drivers(dest)

    def list_kernel_services(self) -> List[Dict[str, Any]]:
        """Lista serviços de kernel (drivers) do Windows."""
        from . import services  # lazy
        return services.list_kernel_services()

    def winget_search(self, package: str) -> Dict[str, Any]:
        """Busca um pacote no repositório winget."""
        from . import winget  # lazy
        return winget.search(package)

    def winget_install(self, package: str) -> Dict[str, Any]:
        """Instala um pacote via winget."""
        from . import winget  # lazy
        return winget.install(package)