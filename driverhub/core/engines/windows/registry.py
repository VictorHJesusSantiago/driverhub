# -*- coding: utf-8 -*-
"""Leitura do Registro do Windows (via ``reg query``) com parsing.

Funções para listar subchaves, valores e uma consulta de hardware resumida
sobre ``HKLM\\SYSTEM\\CurrentControlSet\\Enum``. Nunca lançam exceção.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List

#: Prefixos de raízes de registro aceitos nas chamadas do usuário.
_ROOT_ALIASES = {
    "HKLM": r"HKEY_LOCAL_MACHINE",
    "HKCU": r"HKEY_CURRENT_USER",
    "HKCR": r"HKEY_CLASSES_ROOT",
    "HKU": r"HKEY_USERS",
    "HKCC": r"HKEY_CURRENT_CONFIG",
}

_HARDWARE_KEY = r"HKLM\SYSTEM\CurrentControlSet\Enum"


def _full_path(path: str) -> str:
    """Normaliza um caminho de registro (HKLM -> HKEY_LOCAL_MACHINE...)."""
    head, sep, tail = (path or "").partition("\\")
    head = head.upper()
    if head in _ROOT_ALIASES:
        if tail:
            return f"{_ROOT_ALIASES[head]}\\{tail}"
        return _ROOT_ALIASES[head]
    return path or ""


def _reg_query(args: List[str], timeout: int = 60) -> str:
    exe = shutil.which("reg") or shutil.which("reg.exe")
    if not exe:
        return ""
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([exe, "query"] + args, timeout=timeout,
                              text=True, errors="replace", **kwargs)
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def subkeys(path: str, timeout: int = 60) -> List[str]:
    """Lista os nomes das subchaves diretas de ``path`` (nunca lança).

    Usa ``reg query <path>`` e coleta apenas nomes, evitando recursão.
    """
    full = _full_path(path)
    if not full:
        return []
    out = _reg_query([full], timeout=timeout)
    keys: List[str] = []
    for line in (out or "").splitlines():
        line = line.rstrip()
        # Subchave imediata é indicada por header de chave mais profundo
        # (reg query imprime "path" e, abaixo, a lista de chaves/valores).
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("HKEY_") and "\\" in stripped:
            rest = stripped[len(full):].lstrip("\\")
            first = rest.split("\\", 1)[0]
            if first and first not in keys:
                keys.append(first)
    # Se o reg não retornou headers, tenta com formato recursivo limitado
    if not keys:
        for line in (out or "").splitlines():
            stripped = line.strip()
            if stripped and stripped not in keys and not re.match(r"^.+?\s+REG_\w+", stripped):
                keys.append(stripped)
    return keys[:500]


def values(path: str, timeout: int = 60) -> List[Dict[str, str]]:
    """Lista os valores da chave ``path`` como [{name,type,data}, ...]."""
    full = _full_path(path)
    if not full:
        return []
    out = _reg_query([full], timeout=timeout)
    result: List[Dict[str, str]] = []
    for line in (out or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^(.*?)\s+(REG_\w+)\s+(.*)$", stripped)
        if match:
            name = match.group(1) or "(Default)"
            name = "(default)" if name in ("(Default)", "@") else name
            result.append({"name": name, "type": match.group(2), "data": match.group(3)})
        elif not stripped.startswith("HKEY_") and ":" in stripped:
            # linha tipo "chave\sub" sem valor — ignora
            continue
    return result


def value(path: str, name: str, timeout: int = 60) -> str:
    """Retorna o dado de um valor específico ("" se ausente). Nunca lança."""
    name = name or "(Default)"
    for item in values(path, timeout=timeout):
        if item["name"].lower() == name.lower():
            return item["data"]
    return ""


def query_hardware(limit: int = 200) -> List[Dict[str, Any]]:
    """Levanta dispositivos a partir de ``HKLM\\SYSTEM\\CurrentControlSet\\Enum``.

    Percorre as classes (RAZER, PCI, USB...) e suas instâncias, coleta os
    campos mais úteis e retorna lista de dicts. Limitada a ``limit`` itens.
    """
    result: List[Dict[str, Any]] = []
    classes = subkeys(_HARDWARE_KEY, timeout=90)
    for cls in classes:
        class_path = f"{_HARDWARE_KEY}\\{cls}"
        instances = subkeys(class_path, timeout=60)
        for inst in instances:
            inst_path = f"{class_path}\\{inst}"
            vals = {v["name"]: v["data"] for v in values(inst_path, timeout=30)}
            hwid = vals.get("HardwareID") or vals.get("MatchingDeviceId") or ""
            desc = vals.get("DeviceDesc", "")
            if ";" in desc:
                desc = desc.rsplit(";", 1)[-1]
            result.append({
                "class": cls,
                "instance": inst,
                "description": desc,
                "hwid": hwid,
                "driver": vals.get("Driver", ""),
                "status": "ok",
                "source": "windows:registry",
                "id": inst,
            })
            if len(result) >= limit:
                return result
    return result