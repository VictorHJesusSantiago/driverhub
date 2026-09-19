# -*- coding: utf-8 -*-
"""Middlewares de CORS (Cross-Origin Resource Sharing) para a API web.

Habilita chamadas do navegador (fetch/XMLHttpRequest) e responde preflights
OPTIONS com 204, sempre com ``Access-Control-Allow-Origin: *`` (sem
credenciais). Nunca lança exceção para fora.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, List, Tuple, Union

ALLOW_ORIGIN = "*"
ALLOW_METHODS = "GET, POST, OPTIONS"
ALLOW_HEADERS = "Content-Type, Accept, X-Requested-With, Authorization, Cache-Control"

_PENDING_ATTR = "_driverhub_mw_extra_headers"
_PATCHED_ATTR = "_driverhub_mw_end_headers"

_Header = Tuple[str, str]


def default_headers() -> List[_Header]:
    """Lista padrão de cabeçalhos CORS adicionados às respostas."""
    return [
        ("Access-Control-Allow-Origin", ALLOW_ORIGIN),
        ("Access-Control-Allow-Methods", ALLOW_METHODS),
        ("Access-Control-Allow-Headers", ALLOW_HEADERS),
        ("Vary", "Origin"),
    ]


def _install_headers(handler: Any, headers: Iterable[_Header]) -> None:
    """Registra cabeçalhos extras para serem enviados junto com ``end_headers``.

    Instala um único patch em ``end_headers`` (idempotente por instância), de
    forma que os cabeçalhos entram no buffer antes do término da resposta,
    sem depender da ordem de ``send_response``/``send_header`` do handler.
    """
    try:
        extra = getattr(handler, _PENDING_ATTR, None)
        if extra is None:
            extra = []
            setattr(handler, _PENDING_ATTR, extra)
        extra.extend((name, value) for name, value in headers)
        if getattr(handler, _PATCHED_ATTR, False):
            return
        base_end_headers = handler.end_headers

        def end_headers(*args: Any, **kwargs: Any) -> None:
            try:
                for name, value in getattr(handler, _PENDING_ATTR, []) or []:
                    handler.send_header(name, value)
            except Exception:
                pass
            try:
                setattr(handler, _PENDING_ATTR, [])
            except Exception:
                pass
            return base_end_headers(*args, **kwargs)

        handler.end_headers = end_headers  # type: ignore[assignment]
        setattr(handler, _PATCHED_ATTR, True)
    except Exception:
        pass


def _request_handler(args: tuple) -> Any:
    """Extrai o objeto de requisição HTTP (self) do primeiro argumento."""
    try:
        return args[0] if args else None
    except Exception:
        return None


def _is_options(handler: Any) -> bool:
    """True quando o método da requisição for OPTIONS."""
    try:
        return str(getattr(handler, "command", "") or "").upper() == "OPTIONS"
    except Exception:
        return False


def _handle_error(handler: Any) -> None:
    try:
        if handler is not None:
            handler.send_error(500, "erro interno no handler")
    except Exception:
        pass


def _call_safe(handler: Callable[..., Any], rq: Any,
               args: tuple, kwargs: dict) -> Any:
    """Invoca o handler interno capturando exceções (nunca lança para fora)."""
    try:
        return handler(*args, **kwargs)
    except Exception:
        _handle_error(rq)
        return None


def add_cors_headers(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Envolve um handler adicionando cabeçalhos CORS a toda resposta.

    O primeiro argumento do handler é tratado como o objeto de requisição HTTP
    (padrão ``BaseHTTPRequestHandler``).
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        rq = _request_handler(args)
        if rq is not None:
            try:
                _install_headers(rq, default_headers())
            except Exception:
                pass
        return _call_safe(handler, rq, args, kwargs)

    return wrapper


def preflight_allowed(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Responde 204 (sem corpo) para requisições OPTIONS e delega o resto.

    Preflights de navegador não devem cair na cadeia de roteamento real.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        rq = _request_handler(args)
        if rq is not None and _is_options(rq):
            try:
                _install_headers(rq, default_headers())
                rq.send_response(204, "No Content")
                rq.send_header("Content-Length", "0")
                rq.end_headers()
            except Exception:
                pass
            return None
        return _call_safe(handler, rq, args, kwargs)

    return wrapper