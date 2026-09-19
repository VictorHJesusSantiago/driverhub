# -*- coding: utf-8 -*-
"""Sondas do registro do Windows (via ``reg query``) — sem exceções.

Enumerate o ramo ``HKLM\\SYSTEM\\CurrentControlSet\\Enum`` para inventariar
as classes de hardware conhecidas do Plug and Play.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

_ENUM_ROOT = r"HKLM\SYSTEM\CurrentControlSet\Enum"


def reg_query(path: str) -> Dict[str, Any]:
    """Consulta os valores de uma chave do registro. Nunca lança."""
    if not sys.platform.startswith("win"):
        return {"ok": False, "detail": "Registro disponível apenas no Windows.",
                "data": {}}
    res = run_command(["reg", "query", path], 30)
    return {"ok": res["ok"], "detail": res["detail"],
            "data": _parse_values(res["data"])}


def reg_suba(path: str) -> List[str]:
    """Lista as subchaves diretas de ``path`` (path normalizado)."""
    if not sys.platform.startswith("win"):
        return []
    res = run_command(["reg", "query", path], 30)
    wanted = path.upper().rstrip("\\")
    subs: List[str] = []
    for line in res["data"].splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("HKLM", "HKCR", "HKCU", "HKU", "HKEY")):
            if line.upper().rstrip("\\") == wanted:
                continue
            subs.append(line)
    return subs


def _parse_values(text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\s*(.+?)\s+REG_[A-Z_]+\s+(?:REG_[A-Z_]+\s+)?(.*)$", line)
        if m:
            values[m.group(1).strip()] = m.group(2).strip()
    return values


def probe_enum_hardware() -> Dict[str, Any]:
    """Inventaria classes de hardware sob CurrentControlSet\\Enum."""
    classes = reg_suba(_ENUM_ROOT)
    sample: Dict[str, List[str]] = {}
    for cls in classes[:8]:
        sample[cls] = reg_suba(_ENUM_ROOT + "\\" + cls)[:5]
    return {"ok": bool(classes),
            "detail": f"{len(classes)} classes de dispositivo no Enum",
            "data": {"classes": classes, "sample": sample}}


def _run_enum_probe() -> Result:
    res = probe_enum_hardware()
    return Result(res["ok"], res["detail"], res["data"], "registry.enum_hardware")


register(Probe("registry.enum_hardware",
               "Classes de hardware em CurrentControlSet\\Enum",
               _run_enum_probe, priority=45))