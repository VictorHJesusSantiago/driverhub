# -*- coding: utf-8 -*-
from __future__ import annotations

"""Correspondência dispositivo -> catálogo com pesos e ranking."""

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .base import CatalogEntry, Match

WEIGHTS: Dict[str, float] = {
    "hwid": 0.60,
    "vendor": 0.75,
    "model": 0.85,
    "class": 0.10,
}

_STOPWORDS = frozenset({
    "the", "inc", "intl", "ltd", "llc", "corp", "corporation", "company",
    "co", "limited", "device", "devices", "controller", "adapters", "adapter",
    "driver", "drivers", "windows", "system", "computers", "computer", "pc",
    "pci", "pcie", "usb", "generic", "standard", "and", "de", "da", "do",
})


def normalize(text: Any) -> str:
    """Minúsculas sem acentos e sem combinações diacríticas."""
    try:
        value = unicodedata.normalize("NFKD", str(text))
        return "".join(ch for ch in value if not unicodedata.combining(ch)).lower()
    except Exception:
        return ""


def _tokens(text: Any) -> List[str]:
    """Tokeniza texto normalizado em termos significantes."""
    norm = normalize(text)
    parts = re.split(r"[^0-9a-z]+", norm)
    return [p for p in parts if len(p) > 1 and p not in _STOPWORDS]


def _listify(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def _device_fields(device: Any) -> Dict[str, str]:
    if not isinstance(device, dict):
        return {}
    alias = {
        "hwid": ("hwid", "hardware_id", "hardware_ids", "hwids", "device_id"),
        "vendor": ("vendor", "manufacturer", "make"),
        "model": ("model", "device_name", "name", "description"),
        "class": ("class", "class_name", "category", "cls"),
    }
    out: Dict[str, str] = {}
    for field, keys in alias.items():
        for key in keys:
            value = device.get(key)
            if isinstance(value, list):
                text = " ".join(str(v) for v in value)
            else:
                text = str(value) if value is not None else ""
            if text.strip():
                out[field] = text
                break
    return out


def _overlap(a: Sequence[str], b: Sequence[str]) -> float:
    """Fração dos termos de `b` presentes em `a` (0..1)."""
    if not a or not b:
        return 0.0
    sa = set(a)
    hit = sum(1 for t in b if t in sa)
    return hit / max(1.0, float(len(b)))


def score(device: Any, entry: Any) -> float:
    """Pontua 0..100 o quão bem `device` corresponde a `entry`."""
    d = _device_fields(device)
    if not d:
        return 0.0
    e = _to_entry(entry)

    ev = _tokens(e.vendor)
    em = _tokens(e.model)
    ek = _tokens(" ".join(e.kinds))

    parts: Dict[str, float] = {}
    present: List[str] = []

    if d.get("hwid"):
        hwid_norm = normalize(d["hwid"])
        needed = set(ev) | set(em)
        parts["hwid"] = 1.0 if (needed and any(t in hwid_norm for t in needed)) else 0.0
        present.append("hwid")

    if d.get("vendor"):
        parts["vendor"] = _overlap(_tokens(d["vendor"]), ev)
        present.append("vendor")

    if d.get("model"):
        parts["model"] = _overlap(_tokens(d["model"]), em)
        present.append("model")

    if d.get("class"):
        parts["class"] = _overlap(_tokens(d["class"]), ek)
        present.append("class")

    if not present:
        return 0.0

    total = sum(WEIGHTS.get(k, 0.0) for k in present) or 1.0
    weighted = sum(WEIGHTS.get(k, 0.0) * parts[k] for k in present)
    return round(100.0 * weighted / total, 1)


def _to_entry(entry: Any) -> CatalogEntry:
    return entry if isinstance(entry, CatalogEntry) else CatalogEntry(
        vendor=str(getattr(entry, "vendor", "") or (entry.get("vendor") if isinstance(entry, dict) else "") or ""),
        model=str(getattr(entry, "model", "") or (entry.get("model") if isinstance(entry, dict) else "") or ""),
        kinds=list(getattr(entry, "kinds", []) or (entry.get("kinds") if isinstance(entry, dict) else []) or []),
        version=str(getattr(entry, "version", "") or (entry.get("version") if isinstance(entry, dict) else "") or ""),
        url=str(getattr(entry, "url", "") or (entry.get("url") if isinstance(entry, dict) else "") or ""),
        official=bool(getattr(entry, "official", True) if hasattr(entry, "official") else True),
    )


def build_index(entries: Iterable[Any]) -> Dict[str, Any]:
    """Índice invertido de tokens -> índices das entradas."""
    entries = list(entries or [])
    token_map: Dict[str, List[int]] = {}
    for i, e in enumerate(entries):
        ee = _to_entry(e)
        tokens = set(_tokens(ee.vendor)) | set(_tokens(ee.model)) | set(_tokens(" ".join(ee.kinds)))
        for t in tokens:
            token_map.setdefault(t, []).append(i)
    return {"entries": entries, "token_map": token_map, "size": len(entries)}


def best_matches(device: Any, entries: Iterable[Any], top_n: int = 3) -> List[Match]:
    """Ranking das melhores correspondências, do melhor para o pior."""
    results: List[Match] = []
    for e in entries or []:
        try:
            s = score(device, e)
        except Exception:
            s = 0.0
        if s > 0:
            results.append(Match(score=s, confidence=round(s / 100.0, 4), entry=_to_entry(e)))
    results.sort(key=lambda m: (m.score, m.entry.version if m.entry else ""), reverse=True)
    top_n = max(1, int(top_n or 1))
    return results[:top_n]


def rank(device: Any, entries: Iterable[Any], top_n: int = 3) -> List[Tuple[int, Match]]:
    """Retorna lista de (posição, Match) ordenada por relevância."""
    return list(enumerate(best_matches(device, entries, top_n), start=1))