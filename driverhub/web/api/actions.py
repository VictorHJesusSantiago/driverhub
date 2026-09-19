# -*- coding: utf-8 -*-
"""Runner genérico de ações POST com confirmação obrigatória.

Ações destrutivas/sensíveis só devem ser executadas com ``?confirm=1`` na query
(ou ``confirm`` no corpo). O despacho delega para ``core.actions`` (import lazy).
"""
from __future__ import annotations


def _confirmed(query: dict) -> bool:
    from .base import CONFIRM_VALUES
    return str(query.get("confirm", "")).lower() in CONFIRM_VALUES


def confirm_required(action) -> bool:
    """True para ações que exigem confirmação explícita antes de rodar."""
    return str(action or "").lower() in {
        "scan", "install", "remove", "update", "catalog-update",
        "check", "backup", "restore", "delete-backup", "clear-history",
        "settings-reset",
    }


def require_confirm(handler) -> bool:
    """Exige ``confirm=1`` na query do handler; levanta ApiError (400) senão."""
    from .base import ApiError, parse_query
    if not _confirmed(parse_query(handler)):
        raise ApiError("confirmação obrigatória: adicione ?confirm=1 à requisição", 400)
    return True


def dispatch_action(name: str, payload=None, store=None):
    """Despacha ``name`` para a ação ``core.actions`` correspondente.

    ``payload`` é o corpo JSON do POST; devolve o mesmo dict que a CLI usaria.
    """
    payload = payload or {}
    try:
        from ...core import actions as core_actions
        if store is None:
            from ...core.database import Database
            store = Database()
        act = str(name or "").strip().lower()
        if act == "scan":
            return core_actions.run_scan(store)
        if act == "install":
            return _with_target(core_actions.run_install, payload, store)
        if act == "remove":
            target = _target(payload)
            return core_actions.run_remove(store, target, force=bool(payload.get("force")))
        if act == "update":
            target = _target(payload)
            return core_actions.run_update(store, target, payload.get("inf"))
        if act == "catalog-update":
            manifest = str(payload.get("manifest", "") or "").strip()
            if manifest:
                return core_actions.catalog_sync(store, manifest)
            return core_actions.catalog_sync(store)
        if act == "check":
            return core_actions.run_check(store)
        if act == "backup":
            return core_actions.run_backup(store)
        if act == "restore":
            source = str(payload.get("source", "") or "").strip()
            if not source:
                return {"error": "source obrigatório"}
            return core_actions.run_restore(store, source)
        return {"error": f"ação desconhecida: {name}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao executar a ação: {exc}"}


def _target(payload) -> str:
    target = str(payload.get("target", "") or "").strip()
    if not target:
        raise ValueError("target obrigatório")
    return target


def _with_target(fn, payload, store):
    target = _target(payload)
    return fn(store, target)