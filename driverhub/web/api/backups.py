# -*- coding: utf-8 -*-
"""Gestão de backups do DriverHub (delegação lazy às ferramentas do projeto).

A criação e a restauração delegam para ``core.actions.run_backup`` / ``run_restore``
(import lazy); listagem e exclusão são locais, sempre restritas ao diretório de
backups para evitar deleção fora da pasta.
"""
from __future__ import annotations

import os
import shutil
import time


def _backups_dir() -> str:
    from ...constants import backups_dir
    return backups_dir()


def list_backups(store):
    """Lista os backups presentes no diretório de backups do DriverHub."""
    try:
        base = _backups_dir()
        items = []
        os.makedirs(base, exist_ok=True)
        for entry in sorted(os.listdir(base), reverse=True):
            full = os.path.join(base, entry)
            if not os.path.isdir(full):
                continue
            stat = os.stat(full)
            size = 0
            for dp, _, fns in os.walk(full):
                for fn in fns:
                    try:
                        size += os.path.getsize(os.path.join(dp, fn))
                    except OSError:
                        pass
            items.append({
                "name": entry,
                "path": full,
                "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "size": size,
            })
        return {"items": items, "total": len(items)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao listar backups: {exc}"}


def create_backup(store, dest=None):
    """Cria um backup completo dentro do diretório de backups."""
    try:
        from ...core import actions
        base = _backups_dir()
        os.makedirs(base, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = dest or os.path.join(base, f"driverhub-backup-{stamp}")
        res = actions.run_backup(store, dest)
        if res.get("ok"):
            res["name"] = os.path.basename(dest)
        return res
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao criar backup: {exc}"}


def restore_backup(source, store):
    """Restaura um backup (nome dentro do diretório ou caminho absoluto dele)."""
    try:
        from ...core import actions
        base = _backups_dir()
        src = str(source or "").strip()
        if not src:
            return {"error": "backup obrigatório"}
        full = os.path.normpath(src) if os.path.isabs(src) else \
            os.path.normpath(os.path.join(base, os.path.basename(src)))
        base_norm = os.path.normpath(base)
        inside = os.path.commonpath([base_norm, full]) == base_norm
        if not inside or not os.path.exists(full):
            return {"error": f"backup não encontrado: {source}"}
        res = actions.run_restore(store, full)
        res["name"] = os.path.basename(full)
        return res
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao restaurar backup: {exc}"}


def delete_backup(name, store):
    """Exclui um backup com validação de caminho (sem escape do diretório)."""
    try:
        safe = os.path.basename(str(name or "").strip())
        if not safe:
            return {"error": "nome de backup inválido"}
        base = _backups_dir()
        full = os.path.normpath(os.path.join(base, safe))
        if os.path.commonpath([os.path.normpath(base), full]) != os.path.normpath(base):
            return {"error": "backup inválido"}
        if not os.path.isdir(full):
            return {"error": f"backup não encontrado: {name}"}
        shutil.rmtree(full)
        try:
            store.log("backup:delete", safe, "backup excluído", ok=True)
        except Exception:  # noqa: BLE001
            pass
        return {"ok": True, "detail": f"Backup '{safe}' excluído."}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao excluir backup: {exc}"}