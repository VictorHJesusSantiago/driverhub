# -*- coding: utf-8 -*-
"""Acesso ao Driver Store (FileRepository) e verificação de assinatura.

Fornece o caminho da pasta de drivers do sistema, listagem de arquivos .inf
e uma checagem best-effort de assinatura de catálogos ``.cat`` (lendo o
binário) e, quando disponível, via ``signtool verify``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

#: Marcadores de assinatura da Microsoft encontrados em catálogos .cat.
_CAT_SIGNATURE_HINTS = (
    b"Microsoft Windows",
    b"Microsoft Corporation",
    b"BERKERY",
    b"CSEC",
)


def store_path() -> str:
    """Caminho do Driver Store (FileRepository) ou "" se não existir."""
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    candidates = (
        os.path.join(root, "System32", "DriverStore", "FileRepository"),
        os.path.join(root, "WinSxS", "amd64_microsoft-windows-driverstore"),
    )
    for path in candidates:
        if os.path.isdir(path):
            return path
    return ""


def list_files(limit: Optional[int] = 500) -> List[Dict[str, Any]]:
    """Lista arquivos do Driver Store (name, path, size, top-level).

    Só lista a raiz do FileRepository para não varrer milhares de pastas.
    """
    base = store_path()
    if not base:
        return []
    result: List[Dict[str, Any]] = []
    try:
        entries = sorted(os.listdir(base))
    except Exception:
        return []
    for entry in entries:
        full = os.path.join(base, entry)
        try:
            size = os.path.getsize(full)
            is_dir = os.path.isdir(full)
        except Exception:
            size, is_dir = 0, False
        result.append({"name": entry, "path": full, "size": size,
                       "is_dir": is_dir})
        if limit and len(result) >= limit:
            break
    return result


def find_inf(published_name: str) -> str:
    """Localiza um arquivo .inf no Driver Store pelo published name."""
    for name in _walk_infs():
        if name.lower() == published_name.lower():
            return name
    return ""


def _walk_infs(limit: int = 10000) -> List[str]:
    """Varre o FileRepository e retorna caminhos de arquivos .inf."""
    base = store_path()
    if not base:
        return []
    found: List[str] = []
    for root, _dirs, files in os.walk(base):
        for fname in files:
            if fname.lower().endswith(".inf"):
                found.append(os.path.join(root, fname))
                if len(found) >= limit:
                    return found
    return found


def signed(path: str) -> Dict[str, Any]:
    """Verifica assinatura de um catálogo ``.cat`` lendo o binário.

    Se ``path`` for um .inf, tenta achar o .cat correspondente no mesmo dir.
    Também tenta ``signtool verify`` quando disponível. Nunca lança.
    """
    cat = _resolve_cat(path)
    if not cat:
        return {"ok": False, "signed": False, "detail": "catálogo .cat não encontrado",
                "path": path, "method": "none"}
    sigtool_result = _signtool_verify(cat)
    if sigtool_result is not None:
        return sigtool_result
    return _binary_cat_check(cat)


def _resolve_cat(path: str) -> str:
    """Localiza o .cat a partir de um .inf ou aceita o próprio .cat."""
    if not path:
        return ""
    if path.lower().endswith(".cat") and os.path.isfile(path):
        return path
    base = os.path.dirname(os.path.abspath(path))
    name = os.path.splitext(os.path.basename(path))[0]
    candidates = (os.path.join(base, name + ".cat"),
                  os.path.join(base, name.upper() + ".CAT"))
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return ""


def _binary_cat_check(cat: str) -> Dict[str, Any]:
    """Leitura binária do .cat em busca de marcadores de assinatura."""
    try:
        with open(cat, "rb") as fh:
            data = fh.read()
    except Exception as exc:
        return {"ok": False, "signed": False, "detail": f"Erro ao ler .cat: {exc}",
                "path": cat, "method": "binary"}
    if not data:
        return {"ok": False, "signed": False, "detail": ".cat vazio",
                "path": cat, "method": "binary"}
    hints = [hint for hint in _CAT_SIGNATURE_HINTS if hint in data]
    signed_ok = len(hints) > 0
    return {
        "ok": signed_ok,
        "signed": signed_ok,
        "detail": ("Assinatura detectada (binário): " + ", ".join(
            h.decode("ascii", "replace") for h in hints)
            if signed_ok else "Nenhuma assinatura evidente no binário."),
        "path": cat,
        "method": "binary",
        "size": len(data),
    }


def _signtool_verify(cat: str) -> Optional[Dict[str, Any]]:
    """Executa ``signtool verify`` caso exista; retorna None se indisponível."""
    exe = shutil.which("signtool") or shutil.which("signtool.exe")
    if not exe:
        return None
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run([exe, "verify", "/pa", "-v", cat],
                              timeout=120, text=True, errors="replace", **kwargs)
        combined = f"{proc.stdout or ''}\n{proc.stderr or ''}"
        return {"ok": proc.returncode == 0,
                "signed": proc.returncode == 0,
                "detail": combined.strip()[:500],
                "path": cat, "method": "signtool"}
    except Exception:
        return None