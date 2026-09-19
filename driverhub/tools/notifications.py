# -*- coding: utf-8 -*-
"""Notificações de atualizações/eventos: console, arquivo e opcionalmente desktop."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from .. import constants as C
from ..config import Config


@dataclass
class Notification:
    kind: str  # update | backup | warning | info | error
    message: str
    extra: Optional[dict] = None

    def to_dict(self) -> dict:
        return {"kind": self.kind, "message": self.message, "extra": self.extra or {}}


class Notifier:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._pending: List[Notification] = []

    def notify(self, kind: str, message: str, extra: Optional[dict] = None) -> None:
        self._pending.append(Notification(kind, message, extra))

    def flush(self) -> List[Notification]:
        out = list(self._pending)
        self._pending.clear()
        return out

    def tail_log(self, n: int = 50) -> List[str]:
        try:
            with open(C.log_file(), "r", encoding="utf-8") as f:
                return f.read().splitlines()[-n:]
        except OSError:
            return []


def desktop_notify(title: str, body: str) -> bool:
    """Notificação nativa quando possível; retorna False se não disponível."""
    from ..tools import compat
    if compat.IS_LINUX and compat.has_bin("notify-send"):
        from ..tools import shell
        r = shell.run(["notify-send", "-a", C.APP_NAME, title, body], timeout=10)
        return r.ok
    if compat.IS_MACOS:
        from ..tools import shell
        script = (
            'display notification "%s" with title "%s"' % (body, title)
        )
        r = shell.run(["osascript", "-e", script], timeout=10)
        return r.ok
    return False


def notify_updates(updates: List[dict], enabled: bool = True) -> int:
    if not enabled or not updates:
        return 0
    for u in updates[:3]:
        desktop_notify("Atualização disponível",
                       f"{u.get('name', 'Driver')} → {u.get('latest_version', 'nova versão')}")
    return len(updates)