# -*- coding: utf-8 -*-
"""Execução de comandos do sistema com timeout, captura e encodings seguros."""
from __future__ import annotations

import locale
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RunResult:
    ok: bool
    code: int
    output: str = ""
    error: str = ""
    args: List[str] = field(default_factory=list)

    def outlines(self) -> List[str]:
        return [ln for ln in self.output.splitlines() if ln.strip()]


def _decode(b: bytes) -> str:
    for enc in ("utf-8", locale.getpreferredencoding(False), "latin-1", "cp850"):
        try:
            return b.decode(enc, errors="strict").strip()
        except Exception:
            continue
    return b.decode("utf-8", errors="replace").strip()


def _prepend_shell(args: List[str]) -> List[str]:
    if sys.platform.startswith("win"):
        return args
    return args


def run(args: List[str], timeout: Optional[int] = 60, cwd: Optional[str] = None,
        env: Optional[dict] = None, input_text: Optional[str] = None) -> RunResult:
    """Executa com CREATE_NO_WINDOW no Windows e captura stdout/stderr."""
    kwargs: dict = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    kwargs["env"] = full_env
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run(args, timeout=timeout, input=input_text,
                              text=False, **kwargs)
        out = _decode(proc.stdout or b"")
        err = _decode(proc.stderr or b"")
        return RunResult(ok=proc.returncode == 0, code=proc.returncode,
                         output=out, error=err, args=list(args))
    except subprocess.TimeoutExpired:
        return RunResult(ok=False, code=-1, output="", error="timeout", args=list(args))
    except FileNotFoundError:
        return RunResult(ok=False, code=-2, error=f"binário não encontrado: {args[0] if args else ''}",
                         args=list(args))
    except Exception as exc:  # noqa: BLE001
        return RunResult(ok=False, code=-3, error=str(exc), args=list(args))


def which(name: str) -> bool:
    from shutil import which as _which
    return _which(name) is not None


def path_of(name: str) -> Optional[str]:
    from shutil import which as _which
    res = _which(name)
    if res is None and sys.platform.startswith("win"):
        for ext in (".exe", ".bat", ".cmd", ".ps1"):
            res = _which(name + ext)
            if res:
                return res
    return res


def admin() -> bool:
    """Detecta se o processo atual roda como administrador."""
    if sys.platform == "win32":
        import ctypes
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def canonical(args: List[str]) -> str:
    return " ".join(shlex.quote(a) for a in args)