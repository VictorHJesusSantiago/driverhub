# -*- coding: utf-8 -*-
"""Rotas de catálogo: consultas às fontes oficiais de drivers."""
from __future__ import annotations


def _default_store(store):
    if store is not None:
        return store
    from ...core.database import Database
    return Database()


def get_catalog(store, q: str = "", category: str = ""):
    """Consulta o catálogo com filtro opcional por texto (``q``) e categoria."""
    try:
        rows = store.catalog_search(term=q or "", category=category or "")
        return {"items": rows, "total": len(rows), "categories": store.catalog_categories()}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao consultar o catálogo: {exc}"}


def get_catalog_entry(id, store=None):
    """Busca uma entrada de catálogo pelo id da linha."""
    try:
        db = _default_store(store)
        for row in db.catalog_search(term=""):
            if str(row.get("id")) == str(id):
                return {"item": row}
        return {"error": f"entrada de catálogo não encontrada: {id}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao buscar entrada de catálogo: {exc}"}


def catalog_search(text: str, store=None):
    """Busca texto livre no catálogo (fabricante, dispositivo, categoria, notas)."""
    try:
        db = _default_store(store)
        rows = db.catalog_search(term=text or "")
        return {"items": rows, "total": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro na busca do catálogo: {exc}"}


def catalog_categories(store=None):
    """Lista as categorias distintas presentes no catálogo."""
    try:
        db = _default_store(store)
        cats = db.catalog_categories()
        return {"items": cats, "total": len(cats)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao listar categorias: {exc}"}