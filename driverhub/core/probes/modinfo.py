# -*- coding: utf-8 -*-
"""Sondas modinfo (Linux): metadados de módulos do kernel.

Parsing da saída ``campo: valor`` do binário ``modinfo``. Nunca lança.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

_COMMON = ("ext4", "ntfs3", "usb_storage", "btusb", "iwlwifi", "nouveau",
           "amdgpu", "nvidia", "snd_hda_intel", "r8169")


def modinfo_fields(mod: str) -> Dict[str, str]:
    """Consulta ``modinfo <mod>`` e devolve os campos ``chave: valor``."""
    if not sys.platform.startswith("linux"):
        return {}
    res = run_command(["modinfo", mod], 30)
    return _parse_fields(res["data"])


def modinfo_license(mod: str) -> Dict[str, Any]:
    """Retorna a licença declarada de um módulo (se disponível)."""
    fields = modinfo_fields(mod)
    license_ = (fields.get("license") or fields.get("license_err") or "").strip()
    return {"ok": bool(license_),
            "detail": f"Licença: {license_ or 'desconhecida'}",
            "data": license_}


def _parse_fields(text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            fields[key.strip()] = value.strip()
    return fields


def _run_probe() -> Result:
    found: Dict[str, str] = {}
    for mod in _COMMON:
        res = modinfo_license(mod)
        if res["ok"]:
            found[mod] = res["data"]
    return Result(bool(found),
                  f"{len(found)} módulos com licença conhecida",
                  {"modules": found}, "modinfo.licenses")


register(Probe("modinfo.licenses", "Licenças de módulos do kernel",
               _run_probe, priority=60))