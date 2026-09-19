# -*- coding: utf-8 -*-
"""Helpers para o pnputil: enumeração de drivers e dispositivos.

Engloba ``pnputil /enum-drivers`` e ``pnputil /enum-devices`` com parsing das
saídas em blocos. Todas as funções públicas são seguras: nunca lançam exceção
e retornam listas de dicts (vazias em caso de falha).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any, Dict, List

_DRIVER_FIELDS = ("Published Name", "Original Name", "Provider Name",
                  "Class Name", "Class Guid", "Driver Version", "Driver Date")
_DEVICE_FIELDS = ("Instance ID", "Device Description", "Class Name",
                  "Class Guid", "Driver Name", "Status", "Problem Code")

_FIELD_ALIASES = {
    "class guid": "class_guid",
    "class name": "class_name",
    "driver version": "driver_version",
    "driver date": "driver_date",
    "driver name": "driver_name",
    "device description": "device_description",
    "instance id": "instance_id",
    "original name": "original_name",
    "provider name": "provider_name",
    "published name": "published_name",
    "problem code": "problem_code",
    "status": "status",
}


def _run_pnputil(args: List[str], timeout: int = 60) -> str:
    """Executa pnputil e retorna stdout+stderr ("" em qualquer falha)."""
    exe = shutil.which("pnputil") or shutil.which("pnputil.exe")
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


def _split_blocks(text: str) -> List[List[str]]:
    """Divide a saída em blocos separados por linhas em branco."""
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in (text or "").splitlines():
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_block(block: List[str]) -> Dict[str, Any]:
    """Converte um bloco de linhas 'Campo: valor' em um dict normalizado."""
    data: Dict[str, Any] = {}
    for line in block:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        norm = _FIELD_ALIASES.get(key, key.replace(" ", "_"))
        data[norm] = value
    return data


def parse_driver_block(block: List[str]) -> Dict[str, Any]:
    """Converte um bloco do ``pnputil /enum-drivers`` em um dict."""
    data = _parse_block(block)
    if data.get("published_name"):
        data["id"] = data["published_name"]
        data["name"] = data.get("original_name") or data["published_name"]
        data["provider"] = data.get("provider_name", "")
        data["class"] = data.get("class_name", "")
        data["status"] = "published"
        data["source"] = "windows:pnputil"
    return data


def parse_device_block(block: List[str]) -> Dict[str, Any]:
    """Converte um bloco do ``pnputil /enum-devices`` em um dict."""
    data = _parse_block(block)
    if data.get("instance_id"):
        data["id"] = data["instance_id"]
        data["name"] = data.get("device_description") or data["instance_id"]
        data["hwid"] = data["instance_id"]
        data["status"] = _device_status(data.get("status", ""))
        data["source"] = "windows:pnputil"
    return data


def _device_status(raw: str) -> str:
    low = (raw or "").lower()
    if low in ("started", "started/pending", "ok", "running"):
        return "ok"
    if low in ("stopped", "not present", "error"):
        return "problem"
    return raw or "unknown"


def enum_drivers() -> List[Dict[str, Any]]:
    """Lista drivers publicados via ``pnputil /enum-drivers``."""
    out = _run_pnputil(["/enum-drivers"], timeout=120)
    result: List[Dict[str, Any]] = []
    for block in _split_blocks(out):
        parsed = parse_driver_block(block)
        if parsed:
            result.append(parsed)
    return result


def enum_devices() -> List[Dict[str, Any]]:
    """Lista dispositivos com driver via ``pnputil /enum-devices``."""
    out = _run_pnputil(["/enum-devices"], timeout=120)
    result: List[Dict[str, Any]] = []
    for block in _split_blocks(out):
        parsed = parse_device_block(block)
        if parsed:
            result.append(parsed)
    return result


def driver_details(published_name: str) -> Dict[str, Any]:
    """Busca detalhes de um driver publicado pelo ``Published Name``."""
    for driver in enum_drivers():
        if driver.get("id") == published_name:
            return driver
    return {"id": published_name, "name": published_name, "status": "unknown"}