# -*- coding: utf-8 -*-
"""Registro de acesso HTTP do servidor web (thread-safe, em memória).

Cada requisição atendida por um handler envolvido por ``access_log`` /
``log_request`` gera um registro com método, rota, status, duração e IP
remoto. Os registros ficam num buffer circular consultado por
``get_recent_logs`` e também são anexados (best-effort) a um arquivo de log.
Nunca lança exceção para fora.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

_MAX_RECORDS = 2000
_log_lock = threading.Lock()
_recent: List[Dict[str, Any]] = []

_STATUS_ATTR = "_driverhub_status"


def _now_iso() -> str:
    try:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    except Exception:
        return ""


def _remote_ip(handler: Any) -> str:
    try:
        addr = getattr(handler, "client_address", None)
        if addr:
            ip = addr[0]
            if ip:
                return str(ip)
    except Exception:
        pass
    return "-"


def _method_route(handler: Any) -> tuple:
    try:
        method = str(getattr(handler, "command", "") or "")
        route = str(getattr(handler, "path", "") or "")
    except Exception:
        method, route = "?", "?"
    return method or "?", route or "?"


def _status_of(handler: Any, fallback: int) -> int:
    try:
        status = getattr(handler, _STATUS_ATTR, fallback)
        return int(status)
    except Exception:
        return fallback


def _duration_ms(started: float) -> float:
    try:
        now = time.monotonic()
        if started < 1e8:
            ms = (now - started) * 1000.0
        else:
            ms = (time.time() - started) * 1000.0
        return round(max(ms, 0.0), 2)
    except Exception:
        return 0.0


def _format_line(entry: Dict[str, Any]) -> str:
    return (
        "{ts} {method} {route} status={status} duration_ms={duration_ms} ip={ip}".format(
            ts=entry.get("ts", ""),
            method=entry.get("method", "?"),
            route=entry.get("route", ""),
            status=entry.get("status", 200),
            duration_ms=entry.get("duration_ms", 0.0),
            ip=entry.get("ip", "-"),
        )
    )


def _log_path() -> Optional[str]:
    try:
        base = os.path.join(os.path.expanduser("~"), ".driverhub", "logs")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "web_access.log")
    except Exception:
        return None


def _append_file(entry: Dict[str, Any]) -> None:
    try:
        path = _log_path()
        if not path:
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write((entry.get("line") or "") + "\n")
    except Exception:
        pass


def _record(entry: Dict[str, Any]) -> None:
    global _recent
    try:
        with _log_lock:
            _recent.append(entry)
            if len(_recent) > _MAX_RECORDS:
                del _recent[: len(_recent) - _MAX_RECORDS]
        _append_file(entry)
    except Exception:
        pass


def access_log(handler: Callable[..., Any],
               started_at: Optional[Union[int, float]] = None) -> Callable[..., Any]:
    """Envolve um handler gravando a linha de acesso após a resposta.

    ``started_at`` é um timestamp para calcular a duração (monotônico ou
    epoch); se ausente, a marca é capturada na primeira chamada. Para medição
    por requisição, prefira ``log_request``.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        rq = args[0] if args else None
        method, route = _method_route(rq)
        started: float = float(started_at) if isinstance(started_at, (int, float)) else time.monotonic()
        entry: Dict[str, Any] = {
            "ts": _now_iso(),
            "method": method,
            "route": route,
            "ip": _remote_ip(rq),
            "status": 200,
            "duration_ms": 0.0,
            "ok": True,
            "error": "",
            "line": "",
        }
        try:
            result = handler(*args, **kwargs)
            status = _status_of(rq, 200)
            entry["status"] = status
            entry["ok"] = status < 500
        except Exception as exc:  # noqa: BLE001
            entry["status"] = 500
            entry["ok"] = False
            entry["error"] = str(exc)
            result = None
        entry["duration_ms"] = _duration_ms(started)
        entry["line"] = _format_line(entry)
        _record(entry)
        return result

    return wrapper


def log_request(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Como ``access_log``, porém mede a duração de cada requisição."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.monotonic()
        try:
            return access_log(handler, started)(*args, **kwargs)
        except Exception:
            return None

    return wrapper


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retorna os registros mais recentes (mais novos primeiro)."""
    try:
        with _log_lock:
            rows = list(reversed(list(_recent)))
        if limit < 0:
            return rows
        return rows[:limit]
    except Exception:
        return []