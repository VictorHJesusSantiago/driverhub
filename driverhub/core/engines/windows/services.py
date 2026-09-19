# -*- coding: utf-8 -*-
"""Descoberta e controle de serviços/drivers de kernel do Windows.

Baseado em ``sc query`` / ``sc config``. Lista serviços de kernel, inicia,
para e configura o tipo de inicialização. Nunca lança exceção.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List

_TYPE_MAP = {
    "1": "kernel_driver",
    "2": "file_system_driver",
    "7": "recognizer_driver",
}

_STATE_MAP = {
    "1": "stopped",
    "2": "start_pending",
    "3": "stop_pending",
    "4": "running",
    "5": "continue_pending",
    "6": "pause_pending",
    "7": "paused",
}


def _run_sc(args: List[str], timeout: int = 60) -> str:
    exe = shutil.which("sc") or shutil.which("sc.exe")
    if not exe:
        return ""
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([exe] + args, timeout=timeout,
                              text=True, errors="replace", **kwargs)
        return f"{proc.stdout or ''}\n{proc.stderr or ''}".strip()
    except Exception:
        return ""


def _parse_query_blocks(out: str) -> List[Dict[str, Any]]:
    """Converte a saída de ``sc query type= driver`` em lista de dicts."""
    services: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        line = line.strip()
        if not line:
            if current:
                services.append(current)
                current = {}
            continue
        if line.lower().startswith("service_name:"):
            current = {"name": line.split(":", 1)[1].strip()}
        elif line.lower().startswith("display_name:"):
            current["display_name"] = line.split(":", 1)[1].strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if key == "type":
                current["type_code"] = value.split()[0]
                current["service_type"] = _TYPE_MAP.get(value.split()[0], value)
            elif key == "state":
                code = value.split()[0]
                current["state_code"] = code
                current["state"] = _STATE_MAP.get(code, value)
    if current:
        services.append(current)
    return services


def list_kernel_services() -> List[Dict[str, Any]]:
    """Lista serviços de kernel (drivers) via ``sc query type= driver``."""
    out = _run_sc(["query", "type=", "driver", "state=", "all"], timeout=120)
    services = _parse_query_blocks(out)
    for svc in services:
        svc["source"] = "windows:sc"
        svc.setdefault("display_name", svc.get("name", ""))
    return services


def _status(args: List[str], service: str) -> Dict[str, Any]:
    out = _run_sc(args, timeout=120)
    low = (out or "").lower()
    ok = bool(out) and not re.search(r"\bfailed\b|\berror\b|\bcannot\b", low)
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    detail = lines[0] if lines else (out or "")
    return {"ok": ok, "service": service, "detail": detail[:300], "output": out}


def start(service: str) -> Dict[str, Any]:
    """Inicia um serviço de driver (``sc start``). Requer admin."""
    return _status(["start", service], service)


def stop(service: str) -> Dict[str, Any]:
    """Para um serviço de driver (``sc stop``). Requer admin."""
    return _status(["stop", service], service)


def configure_autostart(service: str, enable: bool = True) -> Dict[str, Any]:
    """Define inicialização automática via ``sc config`` (requer admin)."""
    mode = "auto" if enable else "demand"
    out = _run_sc(["config", service, "start=", mode], timeout=120)
    low = (out or "").lower()
    ok = bool(out) and not re.search(r"\bfailed\b|\berror\b", low)
    return {"ok": ok, "service": service, "start_type": mode,
            "detail": (out or "").strip()[:300]}


def status(service: str) -> Dict[str, Any]:
    """Consulta o estado de um serviço de driver (``sc query``)."""
    out = _run_sc(["query", service], timeout=60)
    current: Dict[str, Any] = {}
    for line in (out or "").splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if key == "state":
                current["state_code"] = value.split()[0]
                current["state"] = _STATE_MAP.get(value.split()[0], value)
            elif key == "service_type" or key == "type":
                current["service_type"] = _TYPE_MAP.get(value.split()[0], value)
    ok = bool(out) and "does not exist" not in (out or "").lower()
    return {"ok": ok, "service": service, **current,
            "detail": (out or "").strip()[:300]}