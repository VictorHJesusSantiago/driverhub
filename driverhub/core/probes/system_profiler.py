# -*- coding: utf-8 -*-
"""Sondas system_profiler (macOS) para categorias de hardware.

Categorias suportadas: SPHardwareDataType, SPUSBDataType,
SPParallelATADataType e SPDisplaysDataType. Parse minimalista por
blocos ``Item:`` + campos ``Chave: valor`` recuados. Nunca lança.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

CATEGORIES = ("SPHardwareDataType", "SPUSBDataType", "SPParallelATADataType",
              "SPDisplaysDataType")


def profiler(category: str) -> Dict[str, Any]:
    """Executa ``system_profiler <category>`` com parse minimalista."""
    if category not in CATEGORIES:
        return {"ok": False, "detail": f"Categoria não suportada: {category}",
                "data": []}
    if sys.platform not in ("darwin",):
        return {"ok": False, "detail": "system_profiler disponível apenas no macOS.",
                "data": []}
    res = run_command(["system_profiler", category], 90)
    entries = _parse_minimal(res["data"])
    return {"ok": bool(entries), "detail": res["detail"], "data": entries}


def _parse_minimal(text: str) -> List[Dict[str, Any]]:
    """Separa em itens de nível superior e colhe ``Chave: valor`` recuados."""
    entries: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[:1].isspace():
            if current:
                entries.append(current)
            current = {"name": line.strip().rstrip(":"), "fields": {}}
        elif current:
            key, _, value = line.strip().partition(":")
            if key.strip():
                current["fields"][key.strip()] = value.strip()
    if current:
        entries.append(current)
    return entries


def _run_hardware_probe() -> Result:
    res = profiler("SPHardwareDataType")
    return Result(res["ok"], res["detail"], res["data"],
                  "system_profiler.hardware")


register(Probe("system_profiler.hardware", "Hardware do macOS via system_profiler",
               _run_hardware_probe, priority=40))