# -*- coding: utf-8 -*-
from __future__ import annotations

"""Manifesto do catálogo: esquema, validação e manifesto offline."""

import os
from typing import Any, Dict, List, Tuple

SCHEMA_VERSION = 1

_REQUIRED_ENTRY_FIELDS = ("vendor", "model", "version", "url")

_EXTRA_MODEL_FIELDS = ("kinds", "official", "signature", "checksums", "date")


def manifest_schema() -> Dict[str, Any]:
    """Esquema de referência do manifesto (cópia mutável)."""
    return {
        "format": "driverhub-catalog",
        "schema_version": SCHEMA_VERSION,
        "required": ["format", "schema_version", "entries"],
        "entry_fields": {
            "required": list(_REQUIRED_ENTRY_FIELDS),
            "optional": list(_EXTRA_MODEL_FIELDS),
        },
    }


def default_manifest() -> Dict[str, Any]:
    """Manifesto padrão, sem entradas remotas."""
    return {
        "format": "driverhub-catalog",
        "schema_version": SCHEMA_VERSION,
        "generated": "",
        "sources": [],
        "entries": [],
    }


def validate_manifest(data: Any) -> Tuple[bool, List[str]]:
    """Valida um manifesto; retorna (ok, lista de erros em pt-BR). Nunca lança."""
    errors: List[str] = []
    try:
        if data is None:
            return False, ["Manifesto ausente."]
        if not isinstance(data, dict):
            return False, ["Manifesto deve ser um objeto JSON."]
        if data.get("format") != "driverhub-catalog":
            errors.append("Campo 'format' deve ser 'driverhub-catalog'.")
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            errors.append(f"Versão de esquema não suportada: {version!r}.")
        entries = data.get("entries")
        if entries is None:
            errors.append("Campo obrigatório 'entries' ausente.")
        elif not isinstance(entries, list):
            errors.append("Campo 'entries' deve ser uma lista.")
        else:
            for i, entry in enumerate(entries, start=1):
                if not isinstance(entry, dict):
                    errors.append(f"Entrada #{i}: deve ser um objeto.")
                    continue
                for field in _REQUIRED_ENTRY_FIELDS:
                    value = entry.get(field)
                    if value is None or str(value).strip() == "":
                        errors.append(f"Entrada #{i}: campo obrigatório '{field}' ausente ou vazio.")
        sources = data.get("sources")
        if sources is not None and not isinstance(sources, list):
            errors.append("Campo 'sources' deve ser uma lista.")
    except Exception as exc:
        errors.append(f"Falha ao validar manifesto: {exc}")
    return (not errors), errors


def load_offline_manifest() -> Dict[str, Any]:
    """Carrega um manifesto offline junto ao pacote, se existir. Nunca lança."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(here, "offline_manifest.json")
        if os.path.isfile(candidate):
            import json

            with open(candidate, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        return default_manifest()
    except Exception:
        return default_manifest()