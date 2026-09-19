# -*- coding: utf-8 -*-
"""Rotas de drivers: listagem, detalhe e ações de instalação/remoção/atualização.

As ações de alto nível delegam para ``core.actions`` (import lazy) e devolvem
os mesmos dicts (``ok``/``detail``) que a CLI consome.
"""
from __future__ import annotations


def _default_store(store):
    if store is not None:
        return store
    from ...core.database import Database
    return Database()


def get_drivers(store, q: str = "", status: str = ""):
    """Lista drivers com filtro opcional por texto (``q``) e status."""
    try:
        rows = store.list_drivers(term=q or "", cls="")
        if status:
            rows = [r for r in rows
                    if str(r.get("status", "")).lower() == str(status).lower()]
        return {"items": rows, "total": len(rows), "classes": store.driver_classes()}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao listar drivers: {exc}"}


def get_driver(driver_id: str, store=None):
    """Busca um driver pela id; no Windows também consulta o motor nativo."""
    try:
        db = _default_store(store)
        row = db.get_driver(str(driver_id))
        if row is None:
            from ...core import actions
            from ...core import platform
            if platform.detect_os().get("system") == "windows":
                eng = actions.engine()
                if eng is not None and hasattr(eng, "driver_details"):
                    row = eng.driver_details(str(driver_id))
        return {"item": row or {}}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao buscar driver: {exc}"}


def install_driver(payload, store=None):
    """Instala um driver a partir de ``payload["target"]`` (caminho .inf/.run)."""
    try:
        target = str((payload or {}).get("target", "") or "").strip()
        if not target:
            return {"error": "target obrigatório"}
        from ...core import actions
        return actions.run_install(_default_store(store), target)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro na instalação: {exc}"}


def remove_driver(payload, store=None):
    """Remove um driver (target + opção ``force``). Requer privilégios."""
    try:
        target = str((payload or {}).get("target", "") or "").strip()
        if not target:
            return {"error": "target obrigatório"}
        force = bool((payload or {}).get("force", False))
        from ...core import actions
        return actions.run_remove(_default_store(store), target, force=force)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro na remoção: {exc}"}


def update_driver(payload, store=None):
    """Atualiza/recarrega um driver; ``payload["inf"]`` opcional re-instala."""
    try:
        target = str((payload or {}).get("target", "") or "").strip()
        if not target:
            return {"error": "target obrigatório"}
        inf = (payload or {}).get("inf")
        from ...core import actions
        return actions.run_update(_default_store(store), target, inf)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro na atualização: {exc}"}