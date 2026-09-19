# -*- coding: utf-8 -*-
"""Execução de scripts PowerShell com timeout, captura e encodings seguros.

Scripts são serializados com ``-EncodedCommand`` (UTF-16LE + base64) para
evitar problemas de aspas e acentuação. Nunca lança exceção.
"""
from __future__ import annotations

import base64
import sys
from typing import Any, Dict

from .base import Probe, Result, register, run_command


def powershell(script: str, timeout: int = 120) -> Dict[str, Any]:
    """Executa um script via powershell.exe e devolve dict ``ok``/``detail``."""
    if not sys.platform.startswith("win"):
        return {"ok": False, "detail": "PowerShell disponível apenas no Windows.",
                "data": "", "code": -4}
    try:
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    except Exception:  # noqa: BLE001
        encoded = ""
    args = ["powershell", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    res = run_command(args, timeout)
    return {"ok": res["ok"], "detail": res["detail"],
            "data": res["data"], "code": res["code"]}


def probe_ps() -> Dict[str, Any]:
    """Verifica o PowerShell disponível e retorna a versão."""
    res = powershell("$PSVersionTable.PSVersion.ToString()", 60)
    version = (res.get("data") or "").strip()
    return {"ok": bool(version),
            "detail": f"PowerShell {version or 'indisponível'}",
            "data": version}


def ps_admin_check() -> Dict[str, Any]:
    """Detecta se o processo atual roda como administrador (via PowerShell)."""
    script = ("([Security.Principal.WindowsPrincipal]"
              "[Security.Principal.WindowsIdentity]::GetCurrent().IsInRole("
              "[Security.Principal.WindowsBuiltInRole]::Administrator))")
    res = powershell(script, 60)
    is_admin = (res.get("data") or "").lower().startswith("true")
    return {"ok": True,
            "detail": "Administrador" if is_admin else "Usuário comum",
            "data": {"is_admin": is_admin, "ps_ok": res.get("ok", False),
                     "output": res.get("data", "")}}


def _run_ps_probe() -> Result:
    res = probe_ps()
    return Result(res["ok"], res["detail"], res["data"], "powershell.ps")


def _run_admin_probe() -> Result:
    res = ps_admin_check()
    return Result(res["ok"], res["detail"], res["data"], "powershell.admin")


register(Probe("powershell.ps", "Versão do PowerShell instalado",
               _run_ps_probe, priority=80))
register(Probe("powershell.admin", "Verificação de privilégios administrativos",
               _run_admin_probe, priority=85))