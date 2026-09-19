# -*- coding: utf-8 -*-
"""Wrapper do ``modprobe`` com timeout e sugestões quando o módulo falta.

Fornece ``modprobe(args)`` (genérico), ``load_module``/``unload_module`` e
``not_found_suggests``, que sugere pacotes de cabeçalho/firmware quando o
módulo (ou o firmware dele) não é encontrado — inclusive via fwupd.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    exe = shutil.which("modprobe")
    if not exe:
        return {"ok": False, "output": "", "code": -1,
                "error": "modprobe não encontrado."}
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


def modprobe(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    """Executa ``modprobe`` com os argumentos dados. Nunca lança."""
    result = _run(args, timeout=timeout)
    args_s = " ".join(args)
    detail = result["error"] or result["output"] or f"modprobe {args_s} ok"
    return {"ok": result["ok"], "args": list(args), "detail": detail[:400],
            "output": result["output"], "error": result["error"]}


def load_module(name: str, params: str = "") -> Dict[str, Any]:
    """Carrega um módulo (``modprobe <name> [params]``)."""
    if not name:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    args = [name] + (params.split() if params else [])
    result = _run(args)
    suggests = not_found_suggests(name) if not result["ok"] else []
    return {"ok": result["ok"], "module": name,
            "detail": (result["error"] or result["output"]
                       or f"Módulo {name} carregado."),
            "suggests": suggests}


def unload_module(name: str) -> Dict[str, Any]:
    """Descarrega um módulo (``modprobe -r <name>``)."""
    if not name:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    result = _run(["-r", name])
    return {"ok": result["ok"], "module": name,
            "detail": (result["error"] or result["output"]
                       or f"Módulo {name} descarregado.")}


def reload_module(name: str) -> Dict[str, Any]:
    """Recarrega um módulo (unload + load). Aplica-se a drivers do kernel."""
    unload = unload_module(name)
    if not unload["ok"]:
        # módulo ausente carregado é aceitável para reload
        pass
    return load_module(name)


def not_found_suggests(mod: str) -> List[str]:
    """Sugestões quando o módulo/firmware não é encontrado.

    Inclui cabeçalhos do kernel, pacotes de firmware extras e a recomendação
    de atualizar firmware via ``fwupd``. Nunca lança.
    """
    from .base import detect_package_manager  # lazy
    from . import lsmod  # lazy

    pm = detect_package_manager() or ""
    suggestions: List[str] = []
    if pm in ("apt", "apt-get"):
        suggestions.append("linux-headers-generic")
        suggestions.append("linux-modules-extra-$(uname -r)")
        suggestions.append("firmware-linux")
    elif pm == "dnf":
        suggestions.append("kernel-devel")
        suggestions.append("linux-firmware")
    elif pm == "pacman":
        suggestions.append("linux-headers")
        suggestions.append("linux-firmware")
    elif pm == "zypper":
        suggestions.append("kernel-devel")
        suggestions.append("linux-firmware")
    suggestions.append("fwupd")
    if mod and mod in lsmod.REFERENCE_MODULES:
        suggestions.append(f"pacote do driver '{mod}' da distribuição")
    return suggestions