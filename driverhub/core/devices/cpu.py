# -*- coding: utf-8 -*-
"""Coletor de CPUs: enriquece com frequência, núcleos e threads."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    cpu = inventory.get("cpu") or {}
    name = cpu.get("name") or "CPU"
    dev = Device(
        id="cpu:0",
        name=str(name),
        vendor="",
        kind="cpu",
        hwid="ACPI\\CPU0",
        status="ok",
        driver="",
        detail=(f"{cpu.get('cores', 0)} núcleos / {cpu.get('threads', 0)} threads"
                + (f" / {cpu.get('freq_mhz')} MHz" if cpu.get("freq_mhz") else "")),
        meta={k: v for k, v in (cpu or {}).items() if not isinstance(v, dict)},
    )
    return [dev.to_dict()]