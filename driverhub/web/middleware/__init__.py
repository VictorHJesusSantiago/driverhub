# -*- coding: utf-8 -*-
"""Middlewares web do DriverHub: CORS, registro de acesso e segurança.

Um middleware é uma fábrica no estilo ``next``: recebe um ``handler`` e
devolve um novo ``handler`` que adiciona comportamento (cabeçalhos, validação
ou registro). ``apply`` encadeia os middlewares simples em sequência, na ordem
de ``all_middlewares()``.

Uso típico::

    from driverhub.web.middleware import apply
    do_get = apply(original_do_get, ctx={"started_at": time.monotonic()})

Os middlewares parametrizados (``access_log``, ``max_body_size``) não fazem
parte da cadeia simples e devem ser encadeados manualmente pelo chamador.
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional

from . import cors, logging, security

__all__ = ["all_middlewares", "apply", "cors", "logging", "security"]

CTX_ATTR = "_driverhub_ctx"

_SIMPLE_FACTORIES: List[Callable[..., Callable[..., Any]]] = [
    cors.add_cors_headers,
    cors.preflight_allowed,
    security.security_headers,
]


def all_middlewares() -> List[Callable[..., Callable[..., Any]]]:
    """Retorna as fábricas de middleware simples disponíveis nesta versão."""
    return list(_SIMPLE_FACTORIES)


def apply(handler: Callable[..., Any],
          ctx: Optional[Any] = None) -> Callable[..., Any]:
    """Encadeia os middlewares simples ao redor de ``handler`` (estilo ``next``).

    Devolve um novo callable; o contexto ``ctx`` fica disponível no atributo
    ``_driverhub_ctx`` do callable final para leitura pelos handlers internos.
    Nunca lança exceção para fora: falhas de um middleware são ignoradas e a
    cadeia continua com o handler original.
    """
    chained: Callable[..., Any] = handler
    for factory in all_middlewares():
        try:
            chained = factory(chained)
        except Exception:
            continue
    if ctx is not None:
        try:
            setattr(chained, CTX_ATTR, ctx)
        except Exception:
            pass
    return chained