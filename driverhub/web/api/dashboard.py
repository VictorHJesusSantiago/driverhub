# -*- coding: utf-8 -*-
"""Agregações do painel principal (dashboard) e informações de boot."""
from __future__ import annotations


def _top(counts, n: int):
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n])


def _driver_classes(store):
    counts = {}
    for r in store.list_drivers():
        c = r.get("class") or "outros"
        counts[c] = counts.get(c, 0) + 1
    return counts


def _device_kinds(store):
    counts = {}
    for r in store.list_devices():
        k = r.get("kind") or "outros"
        counts[k] = counts.get(k, 0) + 1
    return counts


def get_dashboard(store):
    """Agrega contagens de devices/drivers, problemas, status do catálogo e as
    últimas execuções registradas no histórico."""
    try:
        problems = [d for d in store.list_devices() if d.get("status") == "problem"]
        from ...core import platform
        return {
            "stats": store.stats(),
            "drivers_classes": _top(_driver_classes(store), 12),
            "devices_kinds": _top(_device_kinds(store), 12),
            "recent": store.history(limit=12),
            "os": platform.detect_os(),
            "problems": problems[:12],
            "problems_count": len(problems),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao montar o painel: {exc}"}


def get_boot(store):
    """Informações de boot da máquina: versão, SO, privilégios e estatísticas."""
    try:
        from ... import __version__
        from ...core import platform
        info = platform.detect_all()
        return {
            "version": __version__,
            "os": info["os"],
            "device_class": info.get("device_class", ""),
            "admin": info["os"].get("admin", False),
            "stats": store.stats(),
            "recent": store.history(limit=8),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao montar as informações de boot: {exc}"}