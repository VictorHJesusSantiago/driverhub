# -*- coding: utf-8 -*-
from __future__ import annotations

"""Filtros e busca textual sobre entradas do catálogo."""

import unicodedata
from typing import Any, Dict, List, Optional

from .base import CatalogEntry


def _norm(text: Any) -> str:
    """Minúsculas sem acentos (stemming simples via unicodedata)."""
    try:
        value = unicodedata.normalize("NFKD", str(text))
        return "".join(ch for ch in value if not unicodedata.combining(ch)).lower()
    except Exception:
        return str(text).lower()


def _entries(entries: Any) -> List[Any]:
    return list(entries or [])


def by_category(entries: Any, category: str) -> List[Any]:
    """Entradas cujas `kinds` contêm a categoria (insensível a acento)."""
    target = _norm(category).strip()
    if not target:
        return _entries(entries)
    out: List[Any] = []
    for entry in _entries(entries):
        kinds = entry.kinds if isinstance(entry, CatalogEntry) else (entry.get("kinds") or [] if isinstance(entry, dict) else [])
        try:
            if any(target in _norm(k) for k in kinds):
                out.append(entry)
        except Exception:
            continue
    return out


def _relevance(entry: Any, tokens: List[str]) -> int:
    hay = _norm(
        getattr(entry, "vendor", "") or (entry.get("vendor", "") if isinstance(entry, dict) else "") or ""
    )
    hay += " " + _norm(
        getattr(entry, "model", "") or (entry.get("model", "") if isinstance(entry, dict) else "") or ""
    )
    hay += " " + _norm(
        " ".join(getattr(entry, "kinds", []) or (entry.get("kinds", []) if isinstance(entry, dict) else []))
    )
    return sum(1 for t in tokens if t and t in hay)


def search(entries: Any, text: str) -> List[Any]:
    """Busca simples por tokens; retorna entradas ordenadas por relevância."""
    tokens = [t for t in _norm(text).split() if t]
    if not tokens:
        return _entries(entries)
    hits = [(entry, _relevance(entry, tokens)) for entry in _entries(entries)]
    hits = [(e, r) for e, r in hits if r > 0]
    hits.sort(key=lambda pair: (-pair[1], str(pair[0].date if hasattr(pair[0], "date") else "")),)
    return [pair[0] for pair in hits]


def filter_entries(
    entries: Any,
    category: str = None,
    query: str = None,
    min_score: int = 0,
) -> List[Any]:
    """Filtra por categoria e/ou query, exigindo relevância mínima."""
    result = _entries(entries)
    if category:
        result = by_category(result, category)
    if query:
        ranked = search(result, query)
        min_score = max(0, int(min_score or 0))
        if min_score > 0:
            tokens = [t for t in _norm(query).split() if t]
            result = [e for e in ranked if _relevance(e, tokens) >= min_score]
        else:
            result = ranked
    try:
        result.sort(key=lambda e: str(getattr(e, "date", "") or ""), reverse=True)
    except Exception:
        pass
    return result