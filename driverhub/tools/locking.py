# -*- coding: utf-8 -*-
"""Locking: garante uma única instância de operação crítica por processo/máquina."""
from __future__ import annotations

import os
import tempfile
import threading
import time
from typing import Dict, Optional

_locks_lock = threading.Lock()
_locks: Dict[str, threading.RLock] = {}


class FileLock:
    """Lock de arquivo atômico (O_CREAT|O_EXCL). Stale locks são removidos."""

    def __init__(self, name: str, timeout: float = 30.0):
        base = os.path.join(tempfile.gettempdir(), "driverhub-locks")
        os.makedirs(base, exist_ok=True)
        self.path = os.path.join(base, name.replace(os.sep, "_") + ".lock")
        self.timeout = timeout
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode())
                return True
            except FileExistsError:
                self._reap_stale()
                time.sleep(0.2)
        return False

    def _reap_stale(self, max_age: float = 600) -> None:
        try:
            if time.time() - os.path.getmtime(self.path) > max_age:
                os.unlink(self.path)
        except OSError:
            pass

    def release(self) -> None:
        try:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            try:
                os.unlink(self.path)
            except OSError:
                pass
        except OSError:
            pass


def thread_lock(key: str) -> threading.RLock:
    """Lock em memória por chave (multithreading do servidor web)."""
    with _locks_lock:
        if key not in _locks:
            _locks[key] = threading.RLock()
        return _locks[key]