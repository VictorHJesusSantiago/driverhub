# -*- coding: utf-8 -*-
from __future__ import annotations

"""Estruturas base do catálogo: entradas, correspondências e utilitários."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CatalogEntry:
    """Uma entrada curada de driver de fonte oficial."""

    vendor: str = ""
    model: str = ""
    kinds: List[str] = field(default_factory=list)
    version: str = ""
    url: str = ""
    official: bool = True
    signature: str = ""
    checksums: Dict[str, str] = field(default_factory=dict)
    date: str = ""


@dataclass
class Match:
    """Resultado de uma correspondência dispositivo -> catálogo."""

    score: float = 0.0
    confidence: float = 0.0
    entry: Optional[CatalogEntry] = None


def as_dict(obj: Any) -> Dict[str, Any]:
    """Converte uma entrada (ou dict) em dicionário de forma segura."""
    try:
        if isinstance(obj, CatalogEntry):
            return asdict(obj)
        if isinstance(obj, dict):
            return dict(obj)
    except Exception:
        pass
    return {}


def _to_entry(obj: Any) -> CatalogEntry:
    if isinstance(obj, CatalogEntry):
        return obj
    d = as_dict(obj)
    try:
        return CatalogEntry(
            vendor=str(d.get("vendor") or ""),
            model=str(d.get("model") or ""),
            kinds=list(d.get("kinds") or []),
            version=str(d.get("version") or ""),
            url=str(d.get("url") or ""),
            official=bool(d.get("official", True)),
            signature=str(d.get("signature") or ""),
            checksums=dict(d.get("checksums") or {}),
            date=str(d.get("date") or ""),
        )
    except Exception:
        return CatalogEntry()


def _merged_kinds(a: CatalogEntry, b: CatalogEntry) -> List[str]:
    out: List[str] = []
    for value in list(a.kinds) + list(b.kinds):
        if value and value not in out:
            out.append(str(value))
    return out


def merge_entries(a: Any, b: Any) -> CatalogEntry:
    """Mescla duas entradas; b tem precedência sobre campos não vazios."""
    ea = _to_entry(a)
    eb = _to_entry(b)
    checksums = dict(ea.checksums)
    checksums.update(eb.checksums)
    try:
        return CatalogEntry(
            vendor=eb.vendor or ea.vendor,
            model=eb.model or ea.model,
            kinds=_merged_kinds(ea, eb),
            version=eb.version or ea.version,
            url=eb.url or ea.url,
            official=bool(ea.official and eb.official),
            signature=eb.signature or ea.signature,
            checksums=checksums,
            date=eb.date or ea.date,
        )
    except Exception:
        return ea