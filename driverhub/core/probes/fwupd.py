# -*- coding: utf-8 -*-
"""Sondas fwupdmgr (Linux): firmwares do sistema (LVFS/sofwares UEFI).

Os wrappers ``fwupdmgr_*`` nunca lançam: falhas devolvem ``ok=False`` com a
saída do comando como contexto.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command


def fwupd_refresh() -> Dict[str, Any]:
    """Atualiza os metadados de firmware (``fwupdmgr refresh``)."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "fwupdmgr disponível apenas no Linux.",
                "data": ""}
    res = run_command(["fwupdmgr", "refresh"], 120)
    if not res["ok"]:
        fallback = run_command(["fwupdmgr", "refresh", "--force"], 120)
        if fallback["ok"] and not res["data"]:
            res = fallback
    return {"ok": res["ok"], "detail": res["data"] or res["detail"],
            "data": res["data"]}


def fwupd_updates() -> Dict[str, Any]:
    """Lista atualizações de firmware disponíveis (``fwupdmgr get-updates``)."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "fwupdmgr disponível apenas no Linux.",
                "data": []}
    res = run_command(["fwupdmgr", "get-updates"], 120)
    updates = _parse_updates(res["data"])
    return {"ok": True,
            "detail": f"{len(updates)} atualização(ões) de firmware encontrada(s)",
            "data": updates}


def _parse_updates(text: str) -> List[Dict[str, str]]:
    """Extrai pares (dispositivo, nova versão) da tabela de atualizações."""
    updates: List[Dict[str, str]] = []
    device = "Desconhecido"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        bare = stripped.strip("•-└├'").strip()
        if bare and ":" not in bare and "version" not in bare.lower():
            device = bare
        match = re.search(r"New version:\s*(\S+)", stripped)
        if match:
            updates.append({"device": device,
                            "new_version": match.group(1), "source": "fwupdmgr"})
    return updates


def fwupd_device_count() -> Dict[str, Any]:
    """Conta dispositivos de firmware conhecidos (``fwupdmgr get-devices``)."""
    if not sys.platform.startswith("linux"):
        return {"ok": False, "detail": "fwupdmgr disponível apenas no Linux.",
                "data": 0}
    res = run_command(["fwupdmgr", "get-devices"], 60)
    count = sum(1 for line in res["data"].splitlines()
                if line.strip().lower().startswith("deviceid:"))
    return {"ok": True, "detail": f"{count} dispositivos de firmware",
            "data": count}


def _run_updates_probe() -> Result:
    res = fwupd_updates()
    return Result(res["ok"], res["detail"], res["data"], "fwupd.updates")


def _run_devices_probe() -> Result:
    res = fwupd_device_count()
    return Result(res["ok"], res["detail"], res["data"], "fwupd.devices")


def _run_refresh_probe() -> Result:
    res = fwupd_refresh()
    return Result(res["ok"], res["detail"], res["data"], "fwupd.refresh")


register(Probe("fwupd.updates", "Atualizações de firmware disponíveis",
               _run_updates_probe, priority=40))
register(Probe("fwupd.devices", "Dispositivos de firmware conhecidos",
               _run_devices_probe, priority=60))
register(Probe("fwupd.refresh", "Atualização dos metadados de firmware (LVFS)",
               _run_refresh_probe, priority=95))