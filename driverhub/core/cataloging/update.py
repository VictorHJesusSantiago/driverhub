# -*- coding: utf-8 -*-
from __future__ import annotations

"""Atualização do catálogo a partir de manifestos remotos/offline."""

import json
import os
from typing import Any, Dict, List

from .base import as_dict, merge_entries
from . import entries as _entries_mod


def _read_catalog(db: str) -> List[Dict[str, Any]]:
    if not db or not os.path.isfile(str(db)):
        return []
    try:
        with open(str(db), "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("entries") or []
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def _write_catalog(db: str, rows: List[Any]) -> bool:
    try:
        path = str(db)
        parent = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(parent, exist_ok=True)
        payload = {
            "format": "driverhub-catalog",
            "schema_version": 1,
            "generated": "",
            "entries": [as_dict(r) for r in rows],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _dedupe(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("vendor", "")).lower().strip(), str(row.get("model", "")).lower().strip())
        if key in seen or not key[0] or not key[1]:
            continue
        seen.add(key)
        out.append(row)
    return out


def _merged_rows(builtin: List[Any], remote: List[Any]) -> List[Dict[str, Any]]:
    """Mescla entradas embutidas com as remotas sem duplicar (vendor+model)."""
    combined: Dict[tuple, Dict[str, Any]] = {}
    for row in _dedupe([as_dict(e) for e in builtin]):
        key = (_norm_key(row.get("vendor")), _norm_key(row.get("model")))
        combined.setdefault(key, row)
    for row in _dedupe([as_dict(e) for e in remote]):
        key = (_norm_key(row.get("vendor")), _norm_key(row.get("model")))
        if key in combined:
            merged = merge_entries(combined[key], row)
            combined[key] = as_dict(merged)
        else:
            combined[key] = row
    return [combined[k] for k in combined]


def _norm_key(value: Any) -> str:
    return str(value or "").lower().strip()


def update(db: str, manifest_url: str = None) -> Dict[str, Any]:
    """Baixa um manifest, valida, mescla com o catálogo embutido e grava em `db`.

    Nunca lança: retorna um dicionário de resultado.
    """
    from . import manifest as _manifest_mod
    from . import sources as _sources_mod

    result: Dict[str, Any] = {
        "ok": False,
        "valid": False,
        "errors": [],
        "source": None,
        "merged": 0,
        "db": str(db) if db else None,
    }
    try:
        data: Any = None
        source_label = "offline"
        if manifest_url:
            text = _sources_mod.fetch(manifest_url)
            if text:
                try:
                    data = json.loads(text)
                    source_label = manifest_url
                except Exception:
                    data = None
        if data is None:
            data = _manifest_mod.load_offline_manifest()
            source_label = "offline-manifest"

        valid, errors = _manifest_mod.validate_manifest(data)
        result.update(valid=valid, errors=errors, source=source_label)
        if not valid:
            result["reason"] = "Manifesto inválido; catálogo não atualizado."
            return result

        builtin = _entries_mod.builtin_entries()
        remote = list(data.get("entries") or [])
        merged = _merged_rows(builtin, remote)
        saved = _write_catalog(db, merged) if db else False
        result.update(
            ok=saved and valid,
            merged=len(merged),
            saved=saved,
            entries=merged if saved else [],
        )
        return result
    except Exception as exc:
        result["reason"] = f"Falha ao atualizar catálogo: {exc}"
        return result


def sync_catalog(db: str) -> Dict[str, Any]:
    """Sincroniza o catálogo no banco com o catálogo embutido. Nunca lança."""
    result: Dict[str, Any] = {"ok": False, "count": 0, "db": str(db) if db else None}
    try:
        current = _read_catalog(db)
        builtin = _entries_mod.builtin_entries()
        merged = _merged_rows(builtin, current)
        saved = _write_catalog(db, merged) if db else False
        result.update(ok=saved, count=len(merged))
        return result
    except Exception as exc:
        result["reason"] = f"Falha ao sincronizar catálogo: {exc}"
        return result