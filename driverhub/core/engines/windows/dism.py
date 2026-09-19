# -*- coding: utf-8 -*-
"""Wrappers do DISM: listagem, inspeção, adição e remoção de drivers.

CLI: ``dism /online /get-drivers``, ``/get-driverinfo``, ``/add-driver``,
``/remove-driver``. Requer privilégios administrativos para alterações.
Todas as funções são seguras e retornam dicts com ``ok``/``detail``.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any, Dict, List

_OK_MARKERS = ("operation completed successfully", "operação concluída",
               "success", "concluída", "concluido")
_FAIL_MARKERS = ("error", "failed", "falha", "erro", "cannot be found")


def _run_dism(args: List[str], timeout: int = 120) -> Dict[str, Any]:
    exe = shutil.which("dism") or shutil.which("dism.exe")
    if not exe:
        return {"ok": False, "code": -1, "output": "", "error": "dism não encontrado"}
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([exe] + args, timeout=timeout,
                              text=True, errors="replace", **kwargs)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        ok = proc.returncode == 0 and not _failed(out, err)
        return {"ok": ok, "code": proc.returncode, "output": out, "error": err}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -2, "output": "", "error": "timeout"}
    except Exception as exc:
        return {"ok": False, "code": -3, "output": "", "error": str(exc)}


def _failed(out: str, err: str) -> bool:
    combined = f"{out}\n{err}".lower()
    return any(m in combined for m in _FAIL_MARKERS)


def _block_lines(out: str) -> List[List[str]]:
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in (out or "").splitlines():
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def list_drivers() -> List[Dict[str, Any]]:
    """Lista drivers do sistema via ``dism /online /get-drivers``."""
    result = _run_dism(["/online", "/get-drivers"], timeout=180)
    drivers: List[Dict[str, Any]] = []
    if not result["ok"]:
        return drivers
    for block in _block_lines(result["output"]):
        data: Dict[str, Any] = {}
        for line in block:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            data[key.strip().lower().replace(" ", "_")] = value.strip()
        if data.get("published_name"):
            data["id"] = data["published_name"]
            data["name"] = data.get("original_file_name", data["published_name"])
            data["provider"] = data.get("provider_name", "")
            data["class"] = data.get("class_name", "")
            data["status"] = "published"
            data["source"] = "windows:dism"
            drivers.append(data)
    return drivers


def get_driverinfo(published_name: str) -> Dict[str, Any]:
    """Inspeciona um driver publicado via ``dism /online /get-driverinfo``."""
    result = _run_dism(["/online", "/get-driverinfo",
                        f"/driver:{published_name}"], timeout=120)
    data: Dict[str, Any] = {"id": published_name}
    if result["ok"]:
        for block in _block_lines(result["output"]):
            for line in block:
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                data[key.strip().lower().replace(" ", "_")] = value.strip()
        data["name"] = data.get("original_name", published_name)
    data.update({"ok": result["ok"], "detail": result["output"] or result["error"]})
    data["source"] = "windows:dism"
    return data


def add_driver(inf_path: str, force_unsigned: bool = True) -> Dict[str, Any]:
    """Adiciona um driver ``.inf`` via ``dism /online /add-driver``."""
    args = ["/online", "/add-driver", f"/driver:{inf_path}"]
    if force_unsigned:
        args.append("/forceunsigned")
    result = _run_dism(args, timeout=300)
    detail = result["output"] or result["error"] or "Sem saída do DISM"
    return {"ok": result["ok"], "detail": detail[:500],
            "output": result["output"], "error": result["error"],
            "inf": inf_path}


def remove_driver(published_name: str) -> Dict[str, Any]:
    """Remove um driver publicado via ``dism /online /remove-driver``."""
    if not published_name.lower().endswith(".inf"):
        for d in list_drivers():
            if d.get("id") == published_name or d.get("name") == published_name:
                published_name = d["id"]
                break
    result = _run_dism(["/online", "/remove-driver",
                        f"/driver:{published_name}"], timeout=300)
    detail = result["output"] or result["error"] or "Sem saída do DISM"
    return {"ok": result["ok"], "detail": detail[:500],
            "output": result["output"], "error": result["error"],
            "driver": published_name}