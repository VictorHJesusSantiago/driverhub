# -*- coding: utf-8 -*-
"""Backup e restauração de drivers do Windows.

Exporta drivers publicados (pnputil/DISM) para um diretório de backup e
reimporta ``.inf`` desse diretório de volta ao sistema. Usa ``shutil`` para
cópia de arquivos. Nunca lança exceção.
"""
from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List


def export_drivers(dest: str) -> Dict[str, Any]:
    """Exporta os drivers publicados do sistema para ``dest``.

    Usa o Driver Store como fonte primária dos arquivos e registra metadados.
    Retorna dict com ``ok``, ``dest``, ``exported`` e ``detail``.
    """
    from . import driverstore  # lazy

    try:
        os.makedirs(dest, exist_ok=True)
    except Exception as exc:
        return {"ok": False, "dest": dest, "exported": [],
                "detail": f"Falha ao criar destino: {exc}"}

    exported: List[str] = []
    failed: List[str] = []
    for inf_path in driverstore._walk_infs():
        name = os.path.basename(inf_path)
        target = os.path.join(dest, name)
        try:
            shutil.copy2(inf_path, target)
            exported.append(name)
        except Exception:
            failed.append(name)
    detail = (f"{len(exported)} drivers exportados para {dest}."
              f" Falhas: {len(failed)}" if failed else
              f"{len(exported)} drivers exportados para {dest}.")
    return {"ok": True, "dest": dest, "exported": exported,
            "failed": failed, "detail": detail}


def import_drivers(dest: str) -> Dict[str, Any]:
    """Reimporta drivers de ``dest`` usando pnputil add-driver (requer admin).

    Varre ``dest`` por ``*.inf`` e tenta instalar cada um. Nunca lança.
    """
    from . import pnputil  # lazy

    if not os.path.isdir(dest):
        return {"ok": False, "dest": dest, "imported": [],
                "detail": f"Diretório inexistente: {dest}"}

    infs = _find_inf_files(dest)
    if not infs:
        return {"ok": False, "dest": dest, "imported": [],
                "detail": "Nenhum arquivo .inf encontrado no backup."}

    imported: List[str] = []
    failed: List[str] = []
    for inf in infs:
        out = pnputil._run_pnputil(["/add-driver", inf], timeout=120)
        combined = (out or "").lower()
        if out and ("successfully" in combined or "conclu" in combined
                    or "added" in combined):
            imported.append(os.path.basename(inf))
        else:
            failed.append(os.path.basename(inf))
    return {
        "ok": bool(imported),
        "dest": dest,
        "imported": imported,
        "failed": failed,
        "detail": f"{len(imported)} drivers importados; {len(failed)} falharam.",
    }


def _find_inf_files(base: str) -> List[str]:
    """Recursivamente encontra arquivos ``.inf`` dentro de ``base``."""
    found: List[str] = []
    if not os.path.isdir(base):
        return found
    for root, _dirs, files in os.walk(base):
        for name in files:
            if name.lower().endswith(".inf"):
                found.append(os.path.join(root, name))
    return found


def backup_size(dest: str) -> Dict[str, Any]:
    """Estatísticas simples do diretório de backup (arquivos .inf)."""
    infs = _find_inf_files(dest)
    total = 0
    for inf in infs:
        try:
            total += os.path.getsize(inf)
        except Exception:
            continue
    return {"ok": True, "inf_count": len(infs), "total_bytes": total,
            "detail": f"{len(infs)} arquivos .inf, {total} bytes."}