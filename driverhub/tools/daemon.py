# -*- coding: utf-8 -*-
from __future__ import annotations

"""Daemonização POSIX (fork/setsid) com suporte a pidfile; no Windows, no-op."""

import os
from typing import Optional


def is_daemon() -> bool:
    """Heurística: o processo é um daemon? Nunca lança. Windows -> False."""
    if os.name == "nt":
        return False
    try:
        if not hasattr(os, "getppid"):
            return False
        ppid = os.getppid()
        if ppid <= 1:
            return os.getpid() != 1
        if hasattr(os, "getsid"):
            try:
                return os.getsid(0) != os.getpgrp()
            except Exception:
                return False
    except Exception:
        pass
    return False


def daemonize(logfile: Optional[str] = None) -> bool:
    """Desacopla o processo do terminal (fork duplo + setsid).

    Windows ou ausência de fork: retorna False sem alterar o processo.
    """
    if os.name == "nt" or not hasattr(os, "fork"):
        return False
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
        os.setsid()

        pid = os.fork()
        if pid > 0:
            os._exit(0)

        os.chdir("/")
        os.umask(0)

        try:
            sys_stdout = __import__("sys").stdout
            sys_stderr = __import__("sys").stderr
            sys_stdout.flush()
            sys_stderr.flush()
        except Exception:
            pass

        if logfile:
            fd = os.open(str(logfile), os.O_RDWR | os.O_CREAT, 0o644)
        else:
            fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(fd, 0)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        if fd > 2:
            os.close(fd)
        return True
    except Exception:
        return False


def write_pidfile(path: str) -> bool:
    """Grava o PID do processo atual em `path`. Nunca lança."""
    if not path:
        return False
    try:
        parent = os.path.dirname(os.path.abspath(str(path))) or "."
        os.makedirs(parent, exist_ok=True)
        with open(str(path), "w", encoding="ascii") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False


def read_pidfile(path: str) -> Optional[int]:
    """Lê o PID do pidfile; None se ausente ou inválido. Nunca lança."""
    if not path:
        return None
    try:
        if not os.path.isfile(str(path)):
            return None
        with open(str(path), "r", encoding="ascii") as f:
            value = f.read().strip()
        return int(value) if value else None
    except Exception:
        return None