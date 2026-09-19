# -*- coding: utf-8 -*-
"""Integração com ``fwupdmgr`` (firmware do sistema via LVFS).

Lista dispositivos com firmware gerenciável, verifica atualizações, força a
atualização do cache de metadados e retorna as atualizações disponíveis.
Tudo retorna dict e nunca lança exceção.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 120) -> Dict[str, Any]:
    exe = shutil.which("fwupdmgr")
    if not exe:
        return {"ok": False, "output": "", "code": -1,
                "error": "fwupdmgr não encontrado (instale 'fwupd')."}
    try:
        proc = subprocess.run([exe] + args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        out = (proc.stdout or "").strip()
        return {"ok": proc.returncode == 0, "output": out,
                "code": proc.returncode, "error": out if proc.returncode else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "code": -2, "error": "tempo esgotado"}
    except Exception as exc:
        return {"ok": False, "output": "", "code": -3, "error": str(exc)}


def refresh() -> Dict[str, Any]:
    """Atualiza o cache de metadados do firmware (``refresh --force``)."""
    result = _run(["refresh", "--force"], timeout=300)
    return {"ok": result["ok"],
            "detail": result["error"] or result["output"] or "Metadados atualizados.",
            "output": result["output"]}


def device_list() -> Dict[str, Any]:
    """Lista dispositivos com firmware (``get-devices``)."""
    result = _run(["get-devices"], timeout=120)
    devices = _parse_devices(result["output"]) if result["ok"] else []
    return {"ok": result["ok"], "devices": devices,
            "detail": result["error"] or f"{len(devices)} dispositivos.",
            "output": result["output"]}


def get_updates() -> Dict[str, Any]:
    """Atualizações de firmware disponíveis (``get-updates``)."""
    result = _run(["get-updates"], timeout=120)
    updates = _parse_updates(result["output"]) if result["ok"] else []
    return {"ok": result["ok"], "updates": updates,
            "count": len(updates),
            "detail": result["error"] or f"{len(updates)} atualização(ões).",
            "output": result["output"]}


def update_available() -> Dict[str, Any]:
    """True se há atualização de firmware pendente.

    ``get-updates`` com exit code 2 significa "nada a atualizar".
    """
    result = _run(["get-updates"], timeout=120)
    available = result["ok"]
    no_updates = any(word in result["error"].lower()
                     for word in ("no update", "nothing to update", "no hardware"))
    return {"ok": available and not no_updates,
            "available": available and not no_updates,
            "detail": result["error"] or result["output"][:200],
            "output": result["output"]}


def update_by_name(device: str, timeout: int = 600) -> Dict[str, Any]:
    """Aplica atualização de firmware em um dispositivo (requer admin)."""
    result = _run(["update", device, "--force", "-y"], timeout=timeout)
    return {"ok": result["ok"], "device": device,
            "detail": result["error"] or result["output"] or "Atualização aplicada.",
            "output": result["output"]}


def _parse_devices(output: str) -> List[Dict[str, Any]]:
    """Parsing mínimo da saída de ``fwupdmgr get-devices``."""
    devices: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    order = ("DeviceType", "Guid", "CurrentVersion", "InstalledVersion")
    for line in (output or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(("├─", "└─", "│")):
            title = stripped.lstrip("├│└─ ")
            if title:
                current = {"name": title}
                devices.append(current)
            continue
        if ":" in stripped and current is not None:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if any(k in key for k in ("Version", "Guid", "Kind", "Type")):
                current[key.replace(" ", "")] = value
    return devices or [{"name": s.strip()}
                       for s in (output or "").splitlines() if s.strip()][:20]


def _parse_updates(output: str) -> List[Dict[str, Any]]:
    """Parsing mínimo da saída de ``fwupdmgr get-updates``."""
    updates: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith(("updates for", "no updates")):
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip().replace(" ", "")] = value.strip()
        elif current:
            updates.append(current)
            current = {}
    if current:
        updates.append(current)
    return updates