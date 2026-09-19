# -*- coding: utf-8 -*-
"""Sondas de baixo nível do DriverHub (Windows, Linux e macOS).

Cada sonda é uma função que NUNCA lança exceção: retorna um ``dict`` com
``ok``/``detail`` ou uma lista. A importação dos módulos internos é
preguiçosa (lazy) para evitar ciclos de importação.
"""
from __future__ import annotations

from typing import Any, Dict, List

__all__ = ["run_probe", "all_probes", "ensure_registered", "MODULES"]

MODULES = ("wmi", "pnputil", "powershell", "registry", "sysfs", "udevadm",
           "modinfo", "dmesg", "kextstat", "system_profiler", "fwupd",
           "lspci", "pci", "usb", "input", "disk")


def ensure_registered() -> None:
    """Importa todos os módulos de sondas para registrar. Nunca lança."""
    import importlib
    for mod in MODULES:
        try:
            importlib.import_module(f"{__name__}.{mod}")
        except Exception:  # noqa: BLE001
            continue


def all_probes() -> List[Dict[str, Any]]:
    """Lista as sondas registradas (name/desc/priority), sem executá-las."""
    from . import base

    ensure_registered()
    rows = []
    for p in base.PROBES.values():
        rows.append({"name": p.name, "desc": p.desc, "priority": p.priority})
    return rows


def run_probe(name: str, **kw: Any) -> Dict[str, Any]:
    """Executa uma sonda pelo nome; devolve dict ``ok``/``detail``/``data``.

    Nunca lança exceção: sondas desconhecidas retornam ``ok=False``.
    """
    from .base import dispatch

    ensure_registered()
    return dispatch(name, **kw).to_dict()