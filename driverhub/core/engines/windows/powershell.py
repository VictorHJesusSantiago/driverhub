# -*- coding: utf-8 -*-
"""Execução de PowerShell (expressão única) com timeout e captura de saída.

Como alternativa, também detecta se o processo atual roda como administrador
via múltiplas rotas (UAC, ``net session`` e WMI).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


def powershell(script: str, timeout: Optional[int] = 120) -> str:
    """Executa uma expressão única do PowerShell e retorna o stdout limpo.

    Returns apenas o texto de saída (sem exceções em caso de erro); em
    qualquer falha retorna ``""``.
    """
    exe = shutil.which("powershell") or shutil.which("powershell.exe")
    if not exe:
        return ""
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    cmd = [exe, "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-NonInteractive", "-Command", script]
    try:
        proc = subprocess.run(cmd, timeout=timeout or 120,
                              text=True, errors="replace", **kwargs)
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def ps_json(script: str, timeout: Optional[int] = 120) -> Optional[str]:
    """Executa um script PS que emite JSON e retorna o JSON como texto."""
    import re  # lazy
    out = powershell(script, timeout=timeout)
    if not out:
        return None
    # remove possíveis avisos (linhas sem chave JSON) no início da saída
    match = re.search(r"(\{.*\}|\[.*\])", out, flags=re.DOTALL)
    return match.group(1) if match else out


def _is_admin_uac() -> bool:
    """Rota 1: chamada IsUserAnAdmin da shell32 (UAC)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes  # lazy
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _is_admin_net() -> bool:
    """Rota 2: ``net session`` só responde a administradores."""
    out = powershell("net session 2>$null; if ($LASTEXITCODE -eq 0) { 'ADMIN' }")
    return "ADMIN" in (out or "")


def _is_admin_whoami() -> bool:
    """Rota 3: verifica grupo S-1-5-32-544 (Administrators) no whoami."""
    out = powershell("whoami /groups")
    return "S-1-5-32-544" in (out or "")


def _routes_admin() -> bool:
    """Detecta administrador percorrendo várias rotas (nunca lança)."""
    for probe in (_is_admin_uac, _is_admin_net, _is_admin_whoami):
        try:
            if probe():
                return True
        except Exception:
            continue
    return False


def check_admin() -> Dict[str, Any]:
    """Resumo público e seguro sobre privilégios administrativos."""
    admin = _routes_admin()
    return {
        "ok": admin,
        "admin": admin,
        "detail": ("" if admin else
                   "Execute como Administrador para modificar drivers."),
    }


def run_ps(script: str, timeout: Optional[int] = 120) -> Dict[str, Any]:
    """Executa PS e retorna dict estruturado com ok/detail/output."""
    out = powershell(script, timeout=timeout)
    return {
        "ok": bool(out) and "error" not in out.lower(),
        "output": out,
        "detail": out.strip() or "Sem saída do PowerShell.",
    }


def script_which(cmd: str) -> bool:
    """Verifica internamente ao PowerShell se um comando existe."""
    out = powershell(f"Get-Command {cmd} -ErrorAction SilentlyContinue")
    return bool(out)