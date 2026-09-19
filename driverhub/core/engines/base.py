# -*- coding: utf-8 -*-
"""Base dos motores de driver: interface comum + helper de execução."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RunResult:
    ok: bool
    code: int = 0
    output: str = ""
    error: str = ""
    args: Tuple[str, ...] = ()
    elapsed: float = 0.0


class DriverEngine(ABC):
    """Interface que cada motor específico de SO implementa."""

    name = "generic"
    label = "Motor genérico"

    def __init__(self, db: Optional[Any] = None):
        self.db = db

    def os_info(self) -> Dict[str, Any]:
        from ...menu import detect_os
        try:
            return detect_os()
        except Exception:
            return {}

    def scan_devices_and_drivers(self) -> Dict[str, Any]:
        return {"devices": self.list_devices(), "drivers": self.list_drivers()}

    def list_devices(self) -> List[Dict[str, Any]]:
        return []

    def list_drivers(self) -> List[Dict[str, Any]]:
        return []

    def install_driver(self, target: str) -> Dict[str, Any]:
        return {"ok": False, "detail": "Não suportado neste SO."}

    def remove_driver(self, target: str, force: bool = False) -> Dict[str, Any]:
        return {"ok": False, "detail": "Não suportado neste SO."}

    def update_driver(self, target: str, source: str = "") -> Dict[str, Any]:
        return {"ok": False, "detail": "Não suportado neste SO."}

    def run(self, args: List[str], timeout: int = 60, input_text: str = "",
            env: Optional[Dict[str, str]] = None) -> RunResult:
        t0 = time.time()
        kwargs: Dict[str, Any] = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        full_env = dict(os.environ)
        if env:
            full_env.update(env)
        try:
            proc = subprocess.run(args, timeout=timeout, input=input_text,
                                  text=True, env=full_env, **kwargs)
            return RunResult(
                ok=proc.returncode == 0, code=proc.returncode,
                output=(proc.stdout or "").strip(), error=(proc.stderr or "").strip(),
                args=tuple(args), elapsed=time.time() - t0,
            )
        except subprocess.TimeoutExpired:
            return RunResult(ok=False, code=-1, error="timeout",
                             args=tuple(args), elapsed=time.time() - t0)
        except OSError as exc:
            return RunResult(ok=False, code=-2, error=str(exc),
                             args=tuple(args), elapsed=time.time() - t0)