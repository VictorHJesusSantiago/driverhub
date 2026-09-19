# -*- coding: utf-8 -*-
from __future__ import annotations

"""Catálogo de drivers — ponto de entrada do pacote driverhub.core.cataloging."""

from typing import Any, Dict, List, Optional

__all__ = ["Catalog", "match_device", "recommend"]


def _builtin() -> List[Any]:
    from . import entries as _entries_mod

    return _entries_mod.builtin_entries()


def _make_index(entries: List[Any]) -> Dict[str, Any]:
    from . import matcher as _matcher

    return _matcher.build_index(entries)


class Catalog:
    """Catálogo pesquisável de drivers de fontes oficiais."""

    def __init__(self, entries: Optional[List[Any]] = None, build_index: bool = True):
        self.entries: List[Any] = list(entries) if entries is not None else _builtin()
        self.index: Dict[str, Any] = _make_index(self.entries) if build_index else {}

    def search(self, text: str, top: int = 10) -> List[Any]:
        if not text:
            return []
        from . import filter as _filter

        return _filter.search(self.entries, text)[: max(1, int(top or 1))]

    def by_category(self, category: str) -> List[Any]:
        from . import filter as _filter

        return _filter.by_category(self.entries, category)

    def match(self, device: Any, top_n: int = 3) -> List[Any]:
        from . import matcher as _matcher

        return _matcher.best_matches(device, self.entries, top_n)

    def recommend(self, device: Any, db: Any = None) -> Dict[str, Any]:
        from . import recommender as _rec

        return _rec.recommend(device, self.index, db=db)

    def refresh(self) -> int:
        self.entries = _builtin()
        self.index = _make_index(self.entries)
        return len(self.entries)


def match_device(device: Any, entries: Optional[List[Any]] = None, top_n: int = 3) -> List[Any]:
    """Corresponde um dispositivo ao catálogo e devolve o ranking."""
    from . import matcher as _matcher

    base: List[Any] = list(entries) if entries is not None else _builtin()
    return _matcher.best_matches(device, base, top_n)


def recommend(device: Any, db: Any = None, index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Recomenda um driver para o dispositivo (matcher + checagem)."""
    from . import recommender as _rec

    idx: Dict[str, Any] = index if index is not None else _make_index(_builtin())
    return _rec.recommend(device, idx, db=db)