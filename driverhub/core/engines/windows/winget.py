# -*- coding: utf-8 -*-
"""Wrapper do cliente ``winget`` (Windows Package Manager).

Funções de busca, instalação, atualização e listagem com detecção de
ausência do cliente. Tudo retorna dict com ``ok``/``detail`` e nunca lança.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List


def _winget() -> str:
    """Caminho do binário winget ("" se ausente)."""
    return shutil.which("winget") or shutil.which("winget.exe") or ""


def _run(args: List[str], timeout: int = 300) -> Dict[str, Any]:
    exe = _winget()
    if not exe:
        return {"ok": False, "code": -1, "output": "",
                "error": "winget não encontrado. Instale via Microsoft Store."}
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    base = [exe, "--accept-source-agreements", "--disable-interactivity"]
    try:
        proc = subprocess.run(base + args, timeout=timeout,
                              text=True, errors="replace", **kwargs)
        return {"ok": proc.returncode == 0, "code": proc.returncode,
                "output": (proc.stdout or "").strip(),
                "error": (proc.stderr or "").strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -2, "output": "", "error": "tempo esgotado"}
    except Exception as exc:
        return {"ok": False, "code": -3, "output": "", "error": str(exc)}


def version() -> Dict[str, Any]:
    """Detecta a versão do winget (``winget --version``)."""
    result = _run(["--version"], timeout=60)
    out = result["output"] or result["error"]
    ver = next((line for line in out.splitlines() if "v" in line.lower()), out)
    return {"ok": result["ok"], "version": ver.strip(), "detail": out}


def search(package: str) -> Dict[str, Any]:
    """Busca um pacote no winget. Retorna dict com ``results`` (lista)."""
    what = (package or "").strip()
    if not what:
        return {"ok": False, "results": [], "detail": "Informe o termo da busca."}
    result = _run(["search", "--exact", what], timeout=180)
    results = _parse_table(result["output"]) if result["ok"] else []
    if not results:
        result = _run(["search", what], timeout=180)
        results = _parse_table(result["output"]) if result["ok"] else []
    return {"ok": bool(results), "query": what, "results": results,
            "detail": result["output"] or result["error"],
            "error": result["error"]}


def install(package: str) -> Dict[str, Any]:
    """Instala um pacote via winget (modo silencioso). Requer aceitação."""
    what = (package or "").strip()
    if not what:
        return {"ok": False, "detail": "Informe o Id/Name do pacote."}
    result = _run(["install", "--exact", "--silent",
                   "--accept-package-agreements", what], timeout=600)
    detail = result["output"] or result["error"] or "Sem saída do winget."
    return {"ok": result["ok"], "package": what, "detail": detail[:500],
            "error": result["error"]}


def upgrade_all() -> Dict[str, Any]:
    """Atualiza todos os pacotes do winget (``winget upgrade --all``)."""
    result = _run(["upgrade", "--all", "--silent",
                   "--accept-package-agreements"], timeout=900)
    detail = result["output"] or result["error"] or "Nada a atualizar."
    upgraded = len(re.findall(r"Successfully upgraded", result["output"] or ""))
    return {"ok": result["ok"], "upgraded": upgraded, "detail": detail[:500],
            "error": result["error"]}


def list() -> Dict[str, Any]:
    """Lista pacotes instalados via ``winget list``."""
    result = _run(["list"], timeout=180)
    packages = _parse_table(result["output"]) if result["ok"] else []
    return {"ok": result["ok"], "count": len(packages), "packages": packages,
            "detail": result["output"] or result["error"],
            "error": result["error"]}


def _parse_table(output: str) -> List[Dict[str, str]]:
    """Parsing best-effort da tabela do winget (Name Id Version Source...)."""
    rows: List[Dict[str, str]] = []
    if not output:
        return rows
    lines = output.splitlines()
    header_idx = None
    header = []
    for i, line in enumerate(lines[:40]):
        stripped = line.strip()
        if stripped.lower().startswith("name"):
            header = [c.strip() for c in stripped.split()]
            header_idx = i
            break
    if header_idx is None:
        return rows
    for line in lines[header_idx + 1:]:
        stripped = line.strip()
        if not stripped or re.match(r"^[-=]{3,}", stripped):
            continue
        cells = stripped.split()
        if not cells:
            continue
        row: Dict[str, str] = {}
        for idx, col in enumerate(header):
            col_key = col.lower()
            if idx == 0:
                row[col_key] = cells[0]
            elif idx == len(header) - 1:
                row[col_key] = " ".join(cells[idx:]) if len(cells) > idx else ""
            elif idx < len(cells):
                row[col_key] = cells[idx]
        if row.get("name"):
            rows.append(row)
    return rows