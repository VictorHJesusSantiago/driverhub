# -*- coding: utf-8 -*-
from __future__ import annotations

"""Manipulação de versões semânticas: parse, compare, constraints e bump."""

import re
from typing import Any, Dict, Optional, Tuple

_VERSION_RE = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    r"(?:[-.]([0-9A-Za-z.-]+))?"
    r"(?:\+([0-9A-Za-z.-]+))?\s*$"
)

_CONSTRAINT_RE = re.compile(r"^\s*(>=|<=|==|~=|!=|<|>)?\s*(\S+)\s*$")


def parse(version: Any) -> Optional[Dict[str, Any]]:
    """Converte '1.2.3-beta.1+build5' em dict; None se inválido."""
    if version is None:
        return None
    try:
        m = _VERSION_RE.match(str(version))
        if not m:
            return None
        major = int(m.group(1))
        minor = int(m.group(2)) if m.group(2) is not None else 0
        patch = int(m.group(3)) if m.group(3) is not None else 0
        return {
            "major": major,
            "minor": minor,
            "patch": patch,
            "prerelease": m.group(4) or "",
            "build": m.group(5) or "",
            "raw": str(version),
        }
    except Exception:
        return None


def _pre_key(pre: str) -> Tuple[int, str]:
    if not pre:
        return (0, "")
    return (1, pre)


def compare(a: Any, b: Any) -> int:
    """-1 se a < b, 0 se iguais, 1 se a > b. Erros de parse retornam 0."""
    pa = parse(a)
    pb = parse(b)
    if pa is None or pb is None:
        return 0
    for key in ("major", "minor", "patch"):
        if pa[key] != pb[key]:
            return -1 if pa[key] < pb[key] else 1
    ka, kb = _pre_key(pa["prerelease"]), _pre_key(pb["prerelease"])
    if ka[0] != kb[0]:
        return -1 if ka[0] < kb[0] else 1
    if ka[1] != kb[1]:
        return -1 if ka[1] < kb[1] else 1
    return 0


def satisfies(version: Any, constraint: Any) -> bool:
    """Verifica `version` contra constraint simples (>=, <=, ==, ~=, <, >, !=)."""
    try:
        if version is None or constraint is None:
            return False
        pv = parse(version)
        if pv is None:
            return False
        m = _CONSTRAINT_RE.match(str(constraint))
        if not m:
            return False
        op, raw_target = m.group(1) or "==", m.group(2)
        target = parse(raw_target)
        if target is None:
            return False
        cmp = compare(version, raw_target)
        if op == "==":
            return cmp == 0 and bool(
                not target["prerelease"] or (target["prerelease"] == pv["prerelease"])
            )
        if op == "!=":
            return cmp != 0
        if op == ">":
            return cmp > 0
        if op == "<":
            return cmp < 0
        if op == ">=":
            return cmp >= 0
        if op == "<=":
            return cmp <= 0
        if op == "~=":
            left = f"{target['major']}.{target['minor']}.{target['patch']}"
            right = f"{target['major']}.{target['minor'] + 1}.0"
            return (compare(version, left) >= 0) and (compare(version, right) < 0)
        return False
    except Exception:
        return False


def next_major(version: Any) -> str:
    p = parse(version)
    if p is None:
        return str(version or "")
    return f"{p['major'] + 1}.0.0"


def next_minor(version: Any) -> str:
    p = parse(version)
    if p is None:
        return str(version or "")
    return f"{p['major']}.{p['minor'] + 1}.0"


def next_patch(version: Any) -> str:
    p = parse(version)
    if p is None:
        return str(version or "")
    return f"{p['major']}.{p['minor']}.{p['patch'] + 1}"