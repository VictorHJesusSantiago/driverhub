# -*- coding: utf-8 -*-
"""Rotinas de manutenção periódica: varredura, limpeza e backup.

Todas as funções nunca lançam exceções e retornam dicts/listas simples,
seguros para serialização.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

DEFAULTS: Dict[str, Dict[str, Any]] = {
    "scan": {"interval_h": 24, "label": "Varredura de drivers"},
    "cleanup": {"interval_h": 168, "label": "Limpeza de cache e downloads antigos"},
    "backup": {"interval_h": 720, "label": "Backup do banco de dados"},
}


def every(hours: float) -> Dict[str, Any]:
    """Converte horas em dict amigável (segundos + rótulo legível)."""
    try:
        h = max(0.0, float(hours or 0))
    except Exception:
        h = 0.0
    seconds = int(h * 3600)
    days = seconds // 86400
    rem = seconds % 86400
    hs = rem // 3600
    mins = (rem % 3600) // 60
    if seconds <= 0:
        label = "imediatamente"
    elif days:
        label = f"{days}d {hs}h {mins}min"
    elif hs:
        label = f"{hs}h {mins}min"
    else:
        label = f"{mins}min"
    return {"hours": h, "seconds": seconds, "label": label}


def maintenance_schedule(base: Optional[str] = None,
                         intervals: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Gera as próximas datas de varredura, limpeza e backup.

    ``base`` é um timestamp ISO (para testes); sem ele usa o momento atual.
    """
    tasks: List[Dict[str, Any]] = []
    try:
        now = datetime.now()
        if base:
            try:
                now = datetime.fromisoformat(str(base))
            except Exception:
                now = datetime.now()
        for key, spec in (intervals or DEFAULTS).items():
            interval_h = float(spec.get("interval_h", 1) or 1)
            step = every(interval_h)
            next_dt = now + timedelta(seconds=step["seconds"])
            tasks.append({
                "task": key,
                "label": str(spec.get("label", key)),
                "interval_h": interval_h,
                "interval": step["label"],
                "next": next_dt.isoformat(timespec="minutes"),
                "due": False,
            })
    except Exception:
        pass
    return tasks


def suggest_maintenance(db: Any = None) -> List[Dict[str, Any]]:
    """Sugere manutenções com base no estado do banco (nunca lança).

    ``db`` deve expor ``stats()`` e ``history(limit=...)`` (padrão Database).
    Se vazio/inválido, devolve sugestões genéricas de primeira execução.
    """
    try:
        stats: Dict[str, Any] = {}
        history: List[Any] = []
        if db is not None:
            if hasattr(db, "stats"):
                stats = db.stats() or {}
            if hasattr(db, "history"):
                history = db.history(limit=5) or []
    except Exception:
        stats, history = {}, []
    suggestions: List[Dict[str, Any]] = []
    try:
        if not stats:
            suggestions.append({
                "task": "scan", "action": "run_scan", "priority": "high",
                "reason": "Nenhum inventário registrado. Execute uma varredura inicial."})
        else:
            if not stats.get("drivers"):
                suggestions.append({
                    "task": "scan", "action": "run_scan", "priority": "medium",
                    "reason": "Nenhum driver catalogado ainda."})
            if not stats.get("catalog"):
                suggestions.append({
                    "task": "catalog", "action": "catalog_sync", "priority": "high",
                    "reason": "Catálogo vazio: sincronize as fontes oficiais."})
            if stats.get("drivers"):
                suggestions.append({
                    "task": "cleanup", "action": "cleanup", "priority": "low",
                    "reason": f"{stats.get('drivers')} drivers registrados; limpe versões antigas."})
        last_action = ""
        if isinstance(history, list) and history:
            last = history[0]
            last_action = str((last or {}).get("action", "")) if isinstance(last, dict) else ""
        if not history:
            suggestions.append({
                "task": "backup", "action": "run_backup", "priority": "medium",
                "reason": "Nenhum backup encontrado no histórico."})
        elif "backup" not in last_action:
            suggestions.append({
                "task": "backup", "action": "run_backup", "priority": "low",
                "reason": "Última atividade sem registro de backup."})
    except Exception:
        suggestions = [{
            "task": "scan", "action": "run_scan", "priority": "low",
            "reason": "Manutenção recomendada."}]
    return suggestions