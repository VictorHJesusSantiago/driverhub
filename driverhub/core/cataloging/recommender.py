# -*- coding: utf-8 -*-
from __future__ import annotations

"""Recomendação de drivers: matcher + checagem do que está instalado."""

from typing import Any, Dict, List, Optional

from .base import Match, as_dict


def _entries_from_index(index: Any) -> List[Any]:
    if index is None:
        return []
    if isinstance(index, dict):
        return list(index.get("entries") or [])
    if isinstance(index, (list, tuple)):
        return list(index)
    return []


def _installed_version(device: Any, db: Any) -> Optional[str]:
    """Consulta a versão instalada do dispositivo, de forma segura."""
    try:
        if not isinstance(device, dict):
            return None
        name = str(device.get("name") or device.get("model") or "")
        if not name:
            return None
        if isinstance(db, dict):
            installed = db.get("drivers") or db.get("installed") or {}
            if isinstance(installed, dict):
                for key, value in installed.items():
                    if key and (str(key).lower() in name.lower() or name.lower() in str(key).lower()):
                        if isinstance(value, dict):
                            v = value.get("version") or value.get("installed_version")
                        else:
                            v = value
                        if v:
                            return str(v)
                named = installed.get(name)
                if isinstance(named, dict) and named.get("version"):
                    return str(named["version"])
                return str(named) if named else None
            return None
        if isinstance(db, str):
            from driverhub.core import database  # lazy: evita ciclos

            conn = database.Database(db)
            rows = conn.installed_drivers() if hasattr(conn, "installed_drivers") else None
            if not rows:
                return None
            for row in rows:
                text = " ".join(str(v) for v in (row if isinstance(row, (list, tuple)) else []))
                if name.lower() in text.lower():
                    for v in (row if isinstance(row, (list, tuple)) else []):
                        version = str(v)
                        if len(version) > 1 and version.lower() != name.lower():
                            return version
        return None
    except Exception:
        return None


def _needs_update(installed: Optional[str], top: Optional[Match]) -> bool:
    if installed is None or top is None or top.entry is None:
        return False
    try:
        from driverhub.tools import semver  # lazy: utilitário genérico

        return bool(semver.satisfies(str(installed), "<" + str(top.entry.version)))
    except Exception:
        return False


def recommend(device: Any, index: Any, db: Any = None) -> Dict[str, Any]:
    """Recomenda o melhor driver catalogado para o dispositivo.

    Nunca lança: em erro retorna um resumo vazio com `ok=False`.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "device": device,
        "installed": None,
        "up_to_date": False,
        "matches": [],
        "recommended": None,
        "version": None,
        "reason": "Nenhuma correspondência encontrada.",
    }
    try:
        from . import matcher  # lazy
    except Exception:
        return out
    entries = _entries_from_index(index)
    matches = matcher.best_matches(device, entries, top_n=5) if entries else []
    top = matches[0] if matches else None
    installed = _installed_version(device, db)
    up_to_date = bool(top and installed and not _needs_update(installed, top))
    out.update(
        {
            "ok": True,
            "installed": installed,
            "up_to_date": up_to_date,
            "matches": [
                {"score": m.score, "confidence": m.confidence, "entry": as_dict(m.entry)}
                for m in matches
            ],
            "recommended": as_dict(top.entry) if top else None,
            "version": top.entry.version if top and top.entry else None,
            "reason": (
                "Driver instalado está atualizado."
                if up_to_date
                else (
                    f"Recomendado: versão {top.entry.version}."
                    if top and top.entry
                    else "Nenhuma correspondência encontrada."
                )
            ),
        }
    )
    return out


def suggest_for_problems(problems: Any, index: Any) -> List[Dict[str, Any]]:
    """Para cada problema relatado, sugere o driver catalogado adequado."""
    results: List[Dict[str, Any]] = []
    try:
        from . import matcher  # lazy
    except Exception:
        return results
    entries = _entries_from_index(index)
    for problem in problems or []:
        if not isinstance(problem, dict):
            continue
        query = {
            "name": str(problem.get("name") or ""),
            "vendor": str(problem.get("vendor") or problem.get("make") or ""),
            "model": str(problem.get("model") or problem.get("device") or ""),
            "class": str(problem.get("category") or problem.get("class_name") or ""),
            "hwid": str(problem.get("hwid") or problem.get("hardware_id") or ""),
        }
        matches = matcher.best_matches(query, entries, top_n=3) if entries else []
        results.append(
            {
                "problem": problem,
                "matches": [
                    {"score": m.score, "confidence": m.confidence, "entry": as_dict(m.entry)}
                    for m in matches
                ],
                "top": as_dict(matches[0].entry) if matches else None,
            }
        )
    return results