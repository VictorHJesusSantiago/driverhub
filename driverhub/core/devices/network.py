# -*- coding: utf-8 -*-
"""Coletor de rede: NICs físicas, Wi-Fi, Bluetooth e opções do inventário."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device, enrich_from_ids

NET_HINTS = ("ethernet", "wifi", "wlan", "network", "bluetooth", "nic", "gbe")


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(raw):
        name = str(d.get("name") or "").lower()
        if not any(h in name for h in NET_HINTS):
            continue
        kind = "bluetooth" if "bluetooth" in name else "network"
        dev = enrich_from_ids(Device(
            id=f"net:{len(out)}",
            name=str(d.get("name") or "Adaptador de rede"),
            vendor=str(d.get("vendor") or ""),
            kind=kind,
            hwid=str(d.get("hwid") or ""),
            status=str(d.get("status") or "ok"),
            driver=str(d.get("driver") or ""),
            detail=str(d.get("detail") or ""),
        ))
        out.append(dev.to_dict())

    for i, nic in enumerate(inventory.get("network") or []):
        if any(d["name"] == nic.get("name") for d in out):
            continue
        dev = Device(
            id=f"net:inv{len(out)}",
            name=str(nic.get("name") or "Interface"),
            vendor="",
            kind="network",
            hwid="",
            status="up" if nic.get("up") else "unknown",
            driver="",
            detail=(
                f"MAC {nic.get('mac')} · {'ligada' if nic.get('up') else 'desligada'} "
                f"· {nic.get('speed_mbps') or '?'} Mb/s · IP {nic.get('ip') or '—'}"
            ),
            meta=nic,
        )
        out.append(dev.to_dict())
    return out