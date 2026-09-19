# -*- coding: utf-8 -*-
"""Atualização do GRUB e leitura da linha de comando do kernel.

Escolhe o comando de atualização de acordo com a distribuição
(``update-grub`` em Debian/Ubuntu; ``grub2-mkconfig`` em Fedora/RHEL e
Arch). Nunca lança exceção.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 120) -> Dict[str, Any]:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        out = (proc.stdout or "").strip()
        return {"ok": proc.returncode == 0, "output": out,
                "code": proc.returncode,
                "error": out if proc.returncode else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "code": -2, "error": "tempo esgotado"}
    except Exception as exc:
        return {"ok": False, "output": "", "code": -3, "error": str(exc)}


def _grub_command() -> List[str]:
    """Seleciona o comando de atualização do GRUB conforme a distro."""
    from .base import detect_distro  # lazy

    info = detect_distro()
    distro = f"{info.get('id', '')} {info.get('pretty_name', '')}".lower()

    if shutil.which("update-grub"):
        return ["update-grub"]

    if any(k in distro for k in ("arch", "manjaro")):
        if shutil.which("grub-mkconfig"):
            return ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
        return []

    if shutil.which("grub2-mkconfig"):
        target = "/boot/grub2/grub.cfg"
        if not os.path.exists("/boot/grub2"):
            target = "/boot/grub/grub.cfg"
        return ["grub2-mkconfig", "-o", target]

    if os.path.exists("/boot/grub/grub.cfg") and shutil.which("grub-mkconfig"):
        return ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]

    return []


def update_grub(timeout: int = 300) -> Dict[str, Any]:
    """Atualiza a configuração do GRUB. Requer privilégios de root.

    Retorna dict com ``ok``, ``command`` e ``detail``.
    """
    cmd = _grub_command()
    if not cmd:
        return {"ok": False, "command": "",
                "detail": "Nenhum comando GRUB reconhecido (update-grub/"
                          "grub2-mkconfig ausente)."}
    result = _run(cmd, timeout=timeout)
    return {"ok": result["ok"], "command": " ".join(cmd),
            "detail": result["error"] or result["output"] or "GRUB atualizado.",
            "output": result["output"]}


def kernel_cmdline() -> Dict[str, Any]:
    """Lê a linha de comando do kernel em ``/proc/cmdline``.

    Retorna o texto bruto e o dicionário de parâmetros (chave -> valor).
    """
    raw = ""
    try:
        with open("/proc/cmdline", encoding="utf-8", errors="replace") as fh:
            raw = fh.read().strip()
    except Exception:
        pass
    params: Dict[str, str] = {}
    for token in raw.split():
        key, _, value = token.partition("=")
        params[key] = value
    return {"ok": bool(raw), "raw": raw, "count": len(params), "params": params}


def grub_config_path() -> str:
    """Caminho do arquivo de configuração do GRUB ("" se ausente)."""
    for candidate in ("/boot/grub/grub.cfg", "/boot/grub2/grub.cfg"):
        if os.path.isfile(candidate):
            return candidate
    return ""


def last_boot_kernel() -> str:
    """Nome do kernel do último boot no config do GRUB ("" se não achar)."""
    path = grub_config_path()
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception:
        return ""
    match = re.search(r"/(vmlinuz-[^\s'\" ]+)", text)
    return match.group(1) if match else ""