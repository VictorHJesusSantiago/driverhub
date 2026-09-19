# -*- coding: utf-8 -*-
"""Verificação de saúde (check) e resumo leve do último check.

As ações "cinderella" de verificação são delegadas a ``core.actions.run_check``
via import lazy; aqui elas são apenas orquestradas para o contrato
``{ok, problems, suggestions, date}`` consumível pela API.
"""
from __future__ import annotations

from datetime import datetime, timezone


def run_check(store):
    """Executa a verificação de saúde completa (pesado; melhor via POST)."""
    try:
        from ...core import actions
        report = actions.run_check(store)
        problems = report.get("problems", []) or []
        suggestions = report.get("suggestions", []) or []
        return {
            "ok": report.get("problems_count", len(problems)) == 0,
            "problems": problems,
            "problems_count": len(problems),
            "suggestions": suggestions,
            "suggestions_count": len(suggestions),
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stats": {
                "devices": report.get("devices", 0),
                "drivers": report.get("drivers", 0),
                "catalog": report.get("catalog", 0),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro na verificação: {exc}"}


def get_check_summary(store=None):
    """Resumo leve: conta problemas e mostra o último check registrado."""
    try:
        last = None
        rows = [] if store is None else store.history(limit=10000)
        for row in rows:
            if row.get("action") == "check":
                last = row
                break
        problems = 0
        if store is not None:
            problems = len([d for d in store.list_devices()
                            if str(d.get("status", "")).lower() == "problem"])
        return {
            "ok": problems == 0,
            "problems": problems,
            "suggestions": 0,
            "last_check": last,
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro no resumo da verificação: {exc}"}