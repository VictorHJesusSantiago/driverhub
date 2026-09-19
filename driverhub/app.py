# -*- coding: utf-8 -*-
"""App: orquestração principal, contexto compartilhado e ciclo de vida.

Reúne Config, Database e logging num único objeto ``App`` usado por CLI e web.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional

from . import constants as C
from .config import Config
from .core.database import Database

_log: Optional[logging.Logger] = None


class App:
    """Contexto de aplicação (Singleton leve; apenas um por processo)."""

    _instance: Optional["App"] = None

    def __init__(self, db_path: Optional[str] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.db = Database(db_path)
        self.start_time = time.time()
        self._lock = threading.RLock()
        self._logger = _make_logger()
        self._logger.info("%s v%s iniciado", C.APP_NAME, C.APP_VERSION)
        set_current_app(self)

    # -------- API do contexto --------
    @classmethod
    def get(cls) -> "App":
        if cls._instance is None:
            cls._instance = App()
        return cls._instance

    def emit(self, action: str, target: str = "", detail: str = "", ok: bool = True) -> None:
        self.db.log(action, target, detail, ok)
        self._logger.info("%s | %s | %s | ok=%s", action, target, detail, ok)

    def log(self, level: int, msg: str) -> None:
        if self._logger:
            self._logger.log(level, msg)

    def close(self) -> None:
        try:
            self.emit(C.EVENT_APP_STOP, "", "encerramento", True)
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass

    def uptime_seconds(self) -> int:
        return int(time.time() - self.start_time)


def set_current_app(app: App) -> None:
    App._instance = app


def _make_logger() -> logging.Logger:
    global _log
    if _log is not None:
        return _log
    logger = logging.getLogger(C.APP_SLUG)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            os.makedirs(C.config_dir(), exist_ok=True)
            fh = logging.FileHandler(C.log_file(), encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(fh)
        except Exception:
            pass
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)
    _log = logger
    return logger