# -*- coding: utf-8 -*-
"""Agendamento leve de tarefas com persistência JSON.

``Schedule`` é serializável (json). ``scheduler_view`` devolve a visão legível
de todas as tarefas. ``due``/``next_run`` operam sobre ``Schedule`` ou dicts.
Nada aqui lança exceções.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class Schedule:
    """Uma tarefa agendada (persistência leve via JSON)."""
    name: str = "tarefa"
    task: str = "scan"
    interval_h: float = 24.0
    at: str = "00:00"
    last_run: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Schedule":
        try:
            d = dict(data or {})
            return cls(
                name=str(d.get("name", "tarefa")),
                task=str(d.get("task", "scan")),
                interval_h=float(d.get("interval_h", 24.0) or 24.0),
                at=str(d.get("at", "00:00")),
                last_run=d.get("last_run"),
                enabled=bool(d.get("enabled", True)),
            )
        except Exception:
            return cls()


def _coerce(item: Any) -> Schedule:
    if isinstance(item, Schedule):
        return item
    if isinstance(item, dict):
        return Schedule.from_dict(item)
    try:
        return Schedule(name=str(item), task="scan")
    except Exception:
        return Schedule()


def _iterate(items: Any) -> List[Any]:
    if isinstance(items, (list, tuple, set)):
        return list(items)
    if items is None:
        return []
    try:
        return list(items)
    except Exception:
        return [items]


def every_seconds(interval_h: float) -> int:
    try:
        from .maintenance import every
        return int(every(interval_h).get("seconds", 0))
    except Exception:
        try:
            return int(float(interval_h or 0) * 3600)
        except Exception:
            return 0


def next_run(item: Any, now: Any = None) -> str:
    """Próxima execução em ISO (considera ``last_run``, ``interval_h`` e ``at``)."""
    try:
        s = _coerce(item)
        now_dt = now if isinstance(now, datetime) else datetime.now()
        if isinstance(now, str):
            try:
                now_dt = datetime.fromisoformat(now)
            except Exception:
                now_dt = datetime.now()
        seconds = every_seconds(s.interval_h)
        if seconds <= 0:
            seconds = 24 * 3600
        interval = timedelta(seconds=seconds)
        at_parts = str(s.at or "00:00").split(":")
        try:
            at_dt = now_dt.replace(hour=int(at_parts[0]) % 24,
                                   minute=int(at_parts[1]) % 60,
                                   second=0, microsecond=0)
        except Exception:
            at_dt = now_dt
        if s.last_run:
            try:
                last = datetime.fromisoformat(str(s.last_run))
                base = last + interval
            except Exception:
                base = at_dt if at_dt > now_dt else now_dt + interval
        else:
            base = at_dt if at_dt > now_dt else now_dt + interval
        while base <= now_dt:
            base += interval
        return base.isoformat(timespec="minutes")
    except Exception:
        return (datetime.now() + timedelta(hours=24)).isoformat(timespec="minutes")


def due(item: Any, now: Any = None) -> bool:
    """True quando a tarefa já atingiu o momento de execução."""
    try:
        s = _coerce(item)
        if not s.enabled:
            return False
        now_dt = now if isinstance(now, datetime) else datetime.now()
        if isinstance(now, str):
            try:
                now_dt = datetime.fromisoformat(now)
            except Exception:
                now_dt = datetime.now()
        if s.last_run:
            try:
                last = datetime.fromisoformat(str(s.last_run))
                interval = timedelta(seconds=every_seconds(s.interval_h))
                return (last + interval) <= now_dt
            except Exception:
                return True
        at_parts = str(s.at or "00:00").split(":")
        try:
            at_dt = now_dt.replace(hour=int(at_parts[0]) % 24,
                                   minute=int(at_parts[1]) % 60,
                                   second=0, microsecond=0)
        except Exception:
            at_dt = now_dt
        return at_dt <= now_dt
    except Exception:
        return False


def scheduler_view(schedules: Any = None) -> List[Dict[str, Any]]:
    """Visão amigável (dicts) de todas as tarefas agendadas."""
    out: List[Dict[str, Any]] = []
    try:
        for raw in _iterate(schedules):
            s = _coerce(raw)
            is_due = due(s)
            nxt = next_run(s)
            out.append({
                "name": s.name,
                "task": s.task,
                "interval_h": s.interval_h,
                "at": s.at,
                "last_run": s.last_run,
                "enabled": s.enabled,
                "due": is_due,
                "next_run": nxt,
                "status": ("vencida" if is_due and s.enabled
                           else ("ativa" if s.enabled else "parada")),
            })
    except Exception:
        pass
    return out


def load_schedules(path: str) -> List[Schedule]:
    """Carrega tarefas de um arquivo JSON (persistência leve)."""
    try:
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [Schedule.from_dict(d) for d in data if isinstance(d, dict)]
    except Exception:
        pass
    return []


def save_schedules(schedules: Any, path: str) -> Dict[str, Any]:
    """Salva tarefas em JSON; retorna dict com o resultado."""
    try:
        rows = [s.to_dict() for s in (_coerce(r) for r in _iterate(schedules))]
        base = os.path.dirname(os.path.abspath(path))
        if base:
            os.makedirs(base, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
        return {"ok": True, "path": path, "count": len(rows)}
    except Exception as exc:
        return {"ok": False, "path": path, "count": 0, "detail": str(exc)}