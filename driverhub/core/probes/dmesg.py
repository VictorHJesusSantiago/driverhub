# -*- coding: utf-8 -*-
"""Mensagens do kernel via ``dmesg`` ou ``/dev/kmsg`` (Linux).

Filtra mensagens de firmware (incluindo *Direct firmware load*), úteis
para diagnosticar drivers de firmware ausentes. Nunca lança exceção.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

_FIRMWARE_PATTERNS = ("firmware", "direct firmware load")


def dmesg_tail(lines: int = 200) -> Dict[str, Any]:
    """Últimas ``lines`` mensagens do kernel."""
    entries = _read_dmesg()
    if entries:
        tail = entries[-lines:]
        return {"ok": True, "detail": f"{len(entries)} mensagens lidas",
                "data": tail, "count": len(entries)}
    return {"ok": False, "detail": "dmesg indisponível", "data": []}


def firmware_messages() -> Dict[str, Any]:
    """Mensagens do kernel relacionadas a firmware (incl. direct-load)."""
    entries = _read_dmesg()
    hits = [line for line in entries
            if any(p in line.lower() for p in _FIRMWARE_PATTERNS)]
    if entries:
        return {"ok": True, "detail": f"{len(hits)} mensagem(ns) de firmware",
                "data": hits, "count": len(hits)}
    return {"ok": False, "detail": "dmesg indisponível", "data": []}


def _read_dmesg() -> List[str]:
    res = run_command(["dmesg"], 15)
    if res["ok"] and res["data"].strip():
        return res["data"].splitlines()
    return _read_kmsg()


def _read_kmsg() -> List[str]:
    if not sys.platform.startswith("linux"):
        return []
    try:
        fd = os.open("/dev/kmsg", os.O_RDONLY | os.O_NONBLOCK)
    except Exception:  # noqa: BLE001
        return []
    chunks: List[bytes] = []
    try:
        while True:
            try:
                chunk = os.read(fd, 1 << 16)
            except BlockingIOError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if len(chunks) > 64:
                break
    except Exception:  # noqa: BLE001
        pass
    finally:
        os.close(fd)
    text = b"".join(chunks).decode("utf-8", errors="replace")
    return [ln for ln in text.splitlines() if ln.strip()]


def _run_firmware_probe() -> Result:
    res = firmware_messages()
    return Result(res["ok"], res["detail"], res["data"], "dmesg.firmware")


register(Probe("dmesg.firmware", "Mensagens de firmware do kernel",
               _run_firmware_probe, priority=55))