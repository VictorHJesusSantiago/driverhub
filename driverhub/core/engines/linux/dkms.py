# -*- coding: utf-8 -*-
"""Gerenciamento de módulos DKMS (Dynamic Kernel Module Support).

Lista o status do DKMS, adiciona, remove e instala módulos, e traz uma tabela
de módulos DKMS comuns (nvidia, v4l2loopback, zfs, rtl8821ce, 8812au...).
Nenhuma função lança exceção.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Dict, List

#: Módulos DKMS comuns com descrição e pacote típico.
DKMS_MODULES: Dict[str, Dict[str, str]] = {
    "nvidia": {"description": "Driver NVIDIA (proprietário)",
               "package": "nvidia-dkms"},
    "v4l2loopback": {"description": "Dispositivo de vídeo virtual",
                     "package": "v4l2loopback-dkms"},
    "zfs": {"description": "Sistema de arquivos ZFS",
            "package": "zfs-dkms"},
    "rtl8821ce": {"description": "Wi-Fi Realtek RTL8821CE",
                  "package": "rtl8821ce-dkms"},
    "8812au": {"description": "Wi-Fi Realtek RTL8812AU",
               "package": "8812au-dkms"},
    "8821cu": {"description": "Wi-Fi Realtek RTL8821CU",
               "package": "rtl8821cu-dkms"},
    "rtl88x2bu": {"description": "Wi-Fi Realtek RTL88x2BU",
                  "package": "rtl88x2bu-dkms"},
    "broadcom-bt": {"description": "Bluetooth Broadcom",
                    "package": "broadcom-bt-firmware"},
    "evdi": {"description": "DisplayLink EVDI", "package": "evdi-dkms"},
    "openrazer": {"description": "Driver peripherals Razer",
                  "package": "openrazer-dkms"},
}


def _run(args: List[str], timeout: int = 120) -> Dict[str, Any]:
    exe = shutil.which("dkms")
    if not exe:
        return {"ok": False, "output": "", "code": -1,
                "error": "dkms não encontrado (instale 'dkms')."}
    try:
        proc = subprocess.run([exe] + args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        out = (proc.stdout or "").strip()
        return {"ok": proc.returncode == 0, "output": out,
                "code": proc.returncode, "error": out if proc.returncode else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "code": -2, "error": "tempo esgotado"}
    except Exception as exc:
        return {"ok": False, "output": "", "code": -3, "error": str(exc)}


def status() -> List[Dict[str, Any]]:
    """Status do DKMS (``dkms status``) como lista de dicts."""
    result = _run(["status"], timeout=60)
    modules: List[Dict[str, Any]] = []
    if not result["ok"]:
        return modules
    for line in result["output"].splitlines():
        # formato: "modulo/versao, kernel, arch: estado"
        match = re.match(r"^([^/,]+)/([^,]+),\s*([^,]+),\s*([^:]+):\s*(.+)$",
                         line.strip())
        if match:
            name = match.group(1).strip()
            modules.append({
                "id": name, "name": name,
                "version": match.group(2).strip(),
                "kernel": match.group(3).strip(),
                "arch": match.group(4).strip(),
                "state": match.group(5).strip().lower(),
                "description": DKMS_MODULES.get(name, {}).get("description", ""),
                "source": "linux:dkms",
            })
    return modules


def add(src: str) -> Dict[str, Any]:
    """Adiciona um módulo ao DKMS (``dkms add <src>``)."""
    if not src:
        return {"ok": False, "detail": "Caminho do fonte vazio."}
    result = _run(["add", src], timeout=180)
    return {"ok": result["ok"], "source": src,
            "detail": result["error"] or result["output"] or "Adicionado ao DKMS.",
            "output": result["output"]}


def remove(name: str) -> Dict[str, Any]:
    """Remove um módulo do DKMS (``dkms remove <name> --all``)."""
    if not name:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    result = _run(["remove", name, "--all"], timeout=180)
    return {"ok": result["ok"], "module": name,
            "detail": result["error"] or result["output"] or f"{name} removido.",
            "output": result["output"]}


def install(name: str) -> Dict[str, Any]:
    """Instala módulo do DKMS para o kernel atual (``dkms install``)."""
    if not name:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    result = _run(["install", name, "--force"], timeout=300)
    return {"ok": result["ok"], "module": name,
            "detail": result["error"] or result["output"] or f"{name} instalado.",
            "output": result["output"]}


def module_count() -> Dict[str, Any]:
    """Resumo do DKMS (quantidade por estado)."""
    modules = status()
    by_state: Dict[str, int] = {}
    for mod in modules:
        state = mod.get("state", "unknown")
        by_state[state] = by_state.get(state, 0) + 1
    return {"ok": True, "total": len(modules), "by_state": by_state,
            "detail": f"{len(modules)} módulo(s) no DKMS."}


def known_module(name: str) -> Dict[str, str]:
    """Retorna a entrada da tabela de módulos DKMS comuns."""
    return dict(DKMS_MODULES.get(name, {"description": "", "package": ""}))