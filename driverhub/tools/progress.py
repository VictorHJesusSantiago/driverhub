# -*- coding: utf-8 -*-
from __future__ import annotations

"""Barra de progresso em terminal, com fallback seguro fora de TTY."""

import sys
import time
from typing import Optional


def eta(n: int, total: int, start_time: Optional[float] = None) -> Optional[float]:
    """Segundos restantes estimados, ou None quando não há base."""
    try:
        total = max(1, int(total or 1))
        n = max(0, int(n or 0))
        if n <= 0 or start_time is None:
            return None
        elapsed = max(0.0, time.monotonic() - float(start_time))
        per_item = elapsed / n
        return round(per_item * (total - n), 1)
    except Exception:
        return None


class Progress:
    """Barra de progresso simples impressa apenas em terminais (TTY)."""

    def __init__(self, total: int, label: str = "", width: int = 40):
        self.total = max(1, int(total or 1))
        self.label = str(label or "")
        self.width = max(10, min(80, int(width or 40)))
        self.n = 0
        self.started = time.monotonic()
        self._tty = self._is_tty()

    @staticmethod
    def _is_tty() -> bool:
        try:
            return bool(getattr(sys.stdout, "isatty", lambda: False)())
        except Exception:
            return False

    def update(self, n: int):
        self.n = min(self.total, max(0, int(n or 0)))
        if not self._tty:
            return None
        self._render()

    def _pct(self) -> float:
        return round(100.0 * self.n / self.total, 1)

    def eta(self) -> Optional[float]:
        return eta(self.n, self.total, self.started)

    def _render(self):
        try:
            filled = int(self.width * self.n / self.total)
            bar = "#" * filled + "-" * (self.width - filled)
            remaining = self.eta()
            suffix = ""
            if remaining is not None:
                suffix = f" ~{remaining:.0f}s restantes"
            percent = self._pct()
            head = f"{self.label} " if self.label else ""
            sys.stdout.write(f"\r{head}[{bar}] {percent:>5.1f}%{suffix}")
            sys.stdout.flush()
        except Exception:
            pass

    def finish(self):
        if self._tty:
            try:
                self.n = self.total
                self._render()
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception:
                pass
        return self