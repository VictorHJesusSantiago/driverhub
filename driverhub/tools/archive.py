# -*- coding: utf-8 -*-
"""Extração de arquivos de driver: ZIP, TAR, TAR.GZ, TAR.BZ2, CAB (Windows).

Usa apenas a biblioteca padrão. Instaladores NSIS/Inno (.exe) são detectados
e retornam instrução para o usuário (não é feita extração automática).
"""
from __future__ import annotations

import os
import shutil
import tarfile
import zipfile
from typing import List, Optional

_EXTS = (".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".cab")


def is_archive(path: str) -> bool:
    low = path.lower()
    return low.endswith(_EXTS) or low.endswith(".tar.gz") or low.endswith(".tar.bz2")


def extract(path: str, dest_dir: str) -> dict:
    os.makedirs(dest_dir, exist_ok=True)
    low = path.lower()
    if low.endswith(".zip"):
        return _extract_zip(path, dest_dir)
    if tarfile.is_tarfile(path):
        return _extract_tar(path, dest_dir)
    if low.endswith(".cab") and shutil.which("expand"):
        return _extract_cab(path, dest_dir)
    return {"ok": False, "detail": f"Formato não suportado: {os.path.basename(path)}"}


def _extract_zip(path: str, dest: str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            z.extractall(dest)
            return {"ok": True, "files": len(names),
                    "detail": f"{len(names)} arquivos extraídos."}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _extract_tar(path: str, dest: str) -> dict:
    try:
        with tarfile.open(path) as t:
            members = t.getnames()
            t.extractall(dest)
            return {"ok": True, "files": len(members),
                    "detail": f"{len(members)} arquivos extraídos."}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _extract_cab(path: str, dest: str) -> dict:
    try:
        from . import shell
        r = shell.run(["expand", "-F:*", path, dest], timeout=120)
        return {"ok": r.ok, "detail": r.output.strip() or "extraído"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def find_infs(root: str, limit: int = 100) -> List[str]:
    found: List[str] = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".inf"):
                found.append(os.path.join(dp, fn))
                if len(found) >= limit:
                    return found
    return found


def detect_installer(path: str) -> Optional[str]:
    """Detecta tipo de instalador .exe por assinatura (heurística)."""
    if not path.lower().endswith(".exe"):
        return None
    try:
        with open(path, "rb") as f:
            head = f.read(2)
            tail = f.read(1_048_576)
        if head == b"MZ":
            if b"Inno Setup" in tail:
                return "inno"
            if b"Nullsoft" in tail or b"NSIS" in tail:
                return "nsis"
            return "installshield-or-generic"
    except OSError:
        return None
    return None