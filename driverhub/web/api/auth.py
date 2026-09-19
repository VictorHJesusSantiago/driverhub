# -*- coding: utf-8 -*-
"""Autenticação simples por token para a API.

O token é lido da variável de ambiente ``DRIVERHUB_TOKEN`` ou da configuração
``web.token`` do DriverHub. Se nenhum token estiver configurado, a autenticação
fica **desativada** (falha segura: o acesso é liberado).
"""
from __future__ import annotations

import os
import secrets


def _configured_token() -> str:
    token = os.environ.get("DRIVERHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        from ...config import Config
        return str(Config().get("web.token", "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def token_ok(token) -> bool:
    """Valida ``token`` contra o token configurado (constante em tempo real).

    Falha segura: se nenhum token estiver configurado, qualquer chamada passa.
    """
    active = _configured_token()
    if not active:
        return True
    if not token:
        return False
    try:
        return secrets.compare_digest(str(token), active)
    except Exception:  # noqa: BLE001
        return str(token) == active


def bearer_from(handler) -> str:
    """Extrai o token do header ``Authorization: Bearer ...`` ou query ``token``."""
    import urllib.parse
    query = {}
    path = getattr(handler, "path", None)
    if path:
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(path).query))
    if query.get("token"):
        return str(query.get("token", ""))
    headers = getattr(handler, "headers", None)
    if headers is not None:
        auth = headers.get("Authorization", "") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
    return ""


def require_auth(handler) -> bool:
    """Exige um token válido; levanta :class:`ApiError` (401) se ausente/errado."""
    from .base import ApiError
    active = _configured_token()
    if active and not token_ok(bearer_from(handler)):
        raise ApiError("autenticação necessária: informe o token no header 'Authorization: Bearer <token>'", 401)
    return True


def issue_token() -> str:
    """Gera um novo token aleatório (32 bytes URL-safe)."""
    return secrets.token_urlsafe(32)