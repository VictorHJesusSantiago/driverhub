# -*- coding: utf-8 -*-
"""Comparação de versões de drivers (formato Windows e semver)."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

_NUM = re.compile(r"^\d+$")


def tokenize(version: str) -> List[object]:
    out: List[object] = []
    for part in re.split(r"[.\-_+ ]+", str(version).strip().lower()):
        if not part:
            continue
        if _NUM.match(part):
            try:
                out.append(int(part))
                continue
            except ValueError:
                pass
        out.append(part)
    return out


def compare(a: str, b: str) -> int:
    """-1 se a<b, 0 se a==b, 1 se a>b."""
    ta, tb = tokenize(a), tokenize(b)
    for x, y in zip(ta, tb):
        if type(x) is type(y):
            if x < y:
                return -1
            if x > y:
                return 1
        else:
            nx, ny = isinstance(x, int), isinstance(y, int)
            if nx and not ny:
                return -1 if y else 1
            if not nx and ny:
                return 1
    if len(ta) == len(tb):
        return 0
    return -1 if len(ta) < len(tb) else 1


def is_newer(candidate: str, current: str) -> bool:
    return compare(candidate, current) > 0


def parse_windows_files(file_version: Optional[str]) -> Tuple[int, int, int, int]:
    """'10.0.22621.1234' -> (10,0,22621,1234)."""
    if not file_version:
        return (0, 0, 0, 0)
    parts = [int(p) for p in re.findall(r"\d+", file_version)][:4]
    parts += [0] * (4 - len(parts))
    return tuple(parts)  # type: ignore[return-value]