# -*- coding: utf-8 -*-
"""Rotas de dispositivos do inventário (leitura)."""
from __future__ import annotations


def _matches(dev, q: str) -> bool:
    q = str(q or "").strip().lower()
    if not q:
        return True
    hay = " ".join(str(dev.get(k, "")) for k in ("name", "vendor", "kind", "driver_id"))
    return q in hay.lower()


def get_devices(store, q: str = "", category: str = ""):
    """Lista dispositivos com filtro opcional por texto (``q``) e categoria."""
    try:
        rows = []
        for r in store.list_devices():
            if category and r.get("kind") != category:
                continue
            if not _matches(r, q):
                continue
            rows.append(r)
        return {"items": rows, "total": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao listar dispositivos: {exc}"}


def get_device(store, device_id: str):
    """Busca um dispositivo por id (linha), driver_id ou nome."""
    try:
        for r in store.list_devices():
            if (str(r.get("id")) == str(device_id)
                    or r.get("driver_id") == device_id
                    or r.get("name") == device_id):
                return {"item": r}
        return {"error": f"dispositivo não encontrado: {device_id}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao buscar dispositivo: {exc}"}


def device_problems(store):
    """Lista apenas os dispositivos com status ``problem``."""
    try:
        problems = [d for d in store.list_devices()
                    if str(d.get("status", "")).lower() == "problem"]
        return {"items": problems, "total": len(problems)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao listar problemas: {exc}"}