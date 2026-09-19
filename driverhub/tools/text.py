# -*- coding: utf-8 -*-
"""Helpers de texto: tabelas simples, separadores e progresso no terminal."""
from __future__ import annotations

import shutil
import sys
import time
from typing import Iterable, List, Optional


def table(headers: List[str], rows: Iterable[List[str]], indent: int = 2,
          max_col: int = 42) -> str:
    cols = [list(r) for r in rows]
    col_count = len(headers)
    for r in cols:
        while len(r) < col_count:
            r.append("")
    width = [len(h) for h in headers]
    for r in cols:
        for i in range(col_count):
            width[i] = min(max(width[i], len(r[i])), max_col)
    sep = "  "
    out = [" " * indent + sep.join(h.ljust(width[i]) for i, h in enumerate(headers))]
    out.append(" " * indent + sep.join("-" * w for w in width))
    for r in cols:
        cells = []
        for i in range(col_count):
            text = r[i]
            cells.append(text[:max_col] + ("…" if len(text) > max_col else "")
                         .ljust(width[i]))
        out.append(" " * indent + sep.join(cells))
    return "\n".join(out)


def truncate(s: str, n: int = 80) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def divider(char: str = "─", length: Optional[int] = None) -> str:
    cols = shutil.get_terminal_size((80, 24)).columns if length is None else length
    return char * min(cols, 120)


class Spinner:
    def __init__(self, message: str = "", enabled: bool = True):
        self.message = message
        self.enabled = enabled
        self._frames = "|/-\\"
        self._i = 0
        self._started = 0.0

    def start(self) -> None:
        self._started = time.time()

    def spin(self, force: bool = False) -> None:
        if not self.enabled or not sys.stdout.isatty():
            return
        sys.stdout.write("\r" + f"{self.message} {self._frames[self._i % 4]} ")
        sys.stdout.flush()
        self._i += 1

    def stop(self, final: str = "") -> float:
        elapsed = time.time() - self._started
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * 60 + "\r")
            if final:
                sys.stdout.write(final + "\n")
            sys.stdout.flush()
        return elapsed