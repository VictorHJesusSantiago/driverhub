# -*- coding: utf-8 -*-
"""Rotas de histórico: leitura, evento individual e limpeza."""
from __future__ import annotations

import os
import sqlite3

_CONFIRM_OK = ("1", "true", "yes", "sim")


def _default_store(store):
    if store is not None:
        return store
    from ...core.database import Database
    return Database()


def get_history(store, limit: int = 100):
    """Lê os eventos mais recentes do histórico (mais novo primeiro)."""
    try:
        try:
            limit = max(1, min(int(limit), 10000))
        except (TypeError, ValueError):
            limit = 100
        rows = store.history(limit=limit)
        return {"items": rows, "total": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao ler o histórico: {exc}"}


def get_event(eid, store=None):
    """Busca um evento do histórico pela id da linha."""
    try:
        db = _default_store(store)
        for row in db.history(limit=10000):
            if str(row.get("id")) == str(eid):
                return {"item": row}
        return {"error": f"evento não encontrado: {eid}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao buscar evento: {exc}"}


def clear_history(store, confirm=False):
    """Apaga todo o histórico. Exige confirmação explícita (``confirm``)."""
    try:
        if str(confirm or "").lower() not in _CONFIRM_OK:
            return {"error": "confirmação obrigatória: informe confirm=1"}
        conn = sqlite3.connect(store.path)
        try:
            conn.execute("DELETE FROM history")
            conn.commit()
        finally:
            conn.close()
        try:
            store.log("history:clear", "todos",
                      f"{store.stats().get('history', 0)} eventos restantes", ok=True)
        except Exception:  # noqa: BLE001
            pass
        return {"ok": True, "detail": "Histórico apagado."}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao limpar o histórico: {exc}"}