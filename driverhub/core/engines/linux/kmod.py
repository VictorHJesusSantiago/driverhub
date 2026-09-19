# -*- coding: utf-8 -*-
"""Gerenciamento de módulos do kernel: lsmod, modinfo, modprobe, rmmod.

Usa ``/proc/modules`` diretamente para listagem (fallback: binário ``lsmod``)
e delega a operações de carga/descarga ao ``modprobe``/``rmmod``. Nenhuma
função lança exceção.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def lsmod() -> List[Dict[str, Any]]:
    """Módulos carregados (via /proc/modules ou binário lsmod).

    Formato /proc: ``nome tamanho refs [lista-dependencias]``.
    """
    modules: List[Dict[str, Any]] = []
    try:
        with open("/proc/modules", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parsed = _parse_proc_line(line)
                if parsed:
                    modules.append(parsed)
    except Exception:
        modules = _parse_lsmod_output(_run(["lsmod"], timeout=30))
    return modules


def _parse_proc_line(line: str) -> Dict[str, Any]:
    parts = line.split()
    if len(parts) < 3:
        return {}
    name = parts[0]
    size = parts[1]
    refs = parts[2] if parts[2].isdigit() else "0"
    used_by = parts[3].rstrip(",") if len(parts) > 3 else ""
    return {
        "id": name, "name": name,
        "size": int(size) if size.isdigit() else 0,
        "refs": int(refs) if refs.isdigit() else 0,
        "used_by": used_by,
        "status": "loaded",
        "source": "linux:kmod",
    }


def _parse_lsmod_output(output: str) -> List[Dict[str, Any]]:
    modules: List[Dict[str, Any]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[0]:
            continue
        modules.append({
            "id": parts[0], "name": parts[0],
            "size": int(parts[1]) if parts[1].isdigit() else 0,
            "refs": int(parts[-3]) if len(parts) > 2 and parts[-3].isdigit() else 0,
            "used_by": parts[-1] if len(parts) > 1 else "",
            "status": "loaded",
            "source": "linux:kmod",
        })
    return modules


def modules_loaded() -> List[str]:
    """Apenas os nomes dos módulos carregados."""
    return [m["name"] for m in lsmod()]


def modinfo(mod: str) -> Dict[str, Any]:
    """Metadados de um módulo via ``modinfo`` (vazio se falhar)."""
    if not mod:
        return {}
    out = _run(["modinfo", mod], timeout=20)
    info: Dict[str, Any] = {"name": mod, "id": mod}
    safe = re.sub(r"\x00", "", out)
    for key, _, value in (line.partition(":") for line in safe.splitlines()):
        key = key.strip()
        value = value.strip()
        if key:
            info.setdefault(key.lower(), value)
    return info


def modprobe(mod: str) -> Dict[str, Any]:
    """Carrega um módulo via ``modprobe`` (requer root)."""
    if not mod:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    exe = shutil.which("modprobe")
    if not exe:
        return {"ok": False, "detail": "modprobe não encontrado."}
    out = _run([exe, mod], timeout=30)
    ok = bool(out) is False or "not found" not in out.lower()
    return {"ok": ok, "module": mod, "detail": out or f"Módulo {mod} carregado.",
            "output": out}


def rmmod(mod: str) -> Dict[str, Any]:
    """Descarrega um módulo via ``rmmod`` (requer root)."""
    if not mod:
        return {"ok": False, "detail": "Nome do módulo vazio."}
    exe = shutil.which("rmmod") or shutil.which("modprobe")
    if not exe:
        return {"ok": False, "detail": "rmmod/modprobe não encontrado."}
    if "modprobe" in exe:
        out = _run([exe, "-r", mod], timeout=30)
    else:
        out = _run([exe, mod], timeout=30)
    low = (out or "").lower()
    ok = not any(bad in low for bad in ("error", "not found", "is in use"))
    return {"ok": ok, "module": mod, "detail": out or f"Módulo {mod} descarregado.",
            "output": out}


def module_loaded(mod: str) -> bool:
    """True se o módulo está carregado atualmente."""
    return mod in modules_loaded()