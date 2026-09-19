# -*- coding: utf-8 -*-
"""Middlewares de segurança para o servidor web do DriverHub.

Adiciona cabeçalhos de proteção (nosniff, frame, referrer e CSP simples para
os assets do frontend), limita o tamanho do corpo das requisições e valida /
sanea entradas de caminhos e parâmetros. Nunca lança exceção para fora: as
funções auxiliares retornam dicts ou None.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

_PENDING_ATTR = "_driverhub_mw_extra_headers"
_PATCHED_ATTR = "_driverhub_mw_end_headers"

_Header = Tuple[str, str]

SECURITY_HEADERS: List[_Header] = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy",
     "default-src 'self'; script-src 'self' 'unsafe-inline'; "
     "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
     "font-src 'self'; connect-src 'self'; object-src 'none'; "
     "base-uri 'self'; form-action 'self'"),
]

_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _install_headers(handler: Any, headers: Iterable[_Header]) -> None:
    """Registra cabeçalhos extras para envio junto com ``end_headers``.

    Patch único e idempotente por instância: os cabeçalhos entram no buffer
    da resposta logo antes do término, independente da ordem do handler.
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
    try:
        return args[0] if args else None
    except Exception:
        return None


def security_headers(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Envolve um handler adicionando cabeçalhos de segurança às respostas."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        rq = _request_handler(args)
        if rq is not None:
            try:
                _install_headers(rq, SECURITY_HEADERS)
            except Exception:
                pass
        try:
            return handler(*args, **kwargs)
        except Exception:
            try:
                if rq is not None:
                    rq.send_error(500, "erro interno no handler")
            except Exception:
                pass
            return None

    return wrapper


def _content_length(handler: Any) -> Optional[int]:
    """Tamanho declarado via Content-Length, ou None quando ausente."""
    try:
        headers = getattr(handler, "headers", None)
        if headers is None:
            return None
        raw = (headers.get("Content-Length") or "").strip()
        if not raw:
            return None
        length = int(raw)
        return max(length, 0)
    except Exception:
        return 0


def _reject_413(handler: Any, received: int, limit: int) -> None:
    try:
        if handler is None:
            return
        body = json.dumps(
            {"ok": False, "error": "corpo da requisição excede o limite permitido"},
            ensure_ascii=False,
        ).encode("utf-8")
        handler.send_response(413)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except Exception:
        pass


def max_body_size(handler: Callable[..., Any],
                  limit: Union[int, float]) -> Callable[..., Any]:
    """Rejeita com 413 requisições cujo corpo declarado exceda ``limit`` bytes.

    Retorna um dict de erro quando rejeita; caso contrário, apenas delega.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        rq = _request_handler(args)
        size = limit
        try:
            size = int(limit) if isinstance(limit, (int, float)) else 0
        except Exception:
            size = 0
        if size > 0:
            length = _content_length(rq)
            if length is not None and length > size:
                _reject_413(rq, length, size)
                return {
                    "ok": False,
                    "error": "corpo da requisição excede o limite permitido",
                    "limit": size,
                    "received": length,
                }
        try:
            return handler(*args, **kwargs)
        except Exception:
            try:
                if rq is not None:
                    rq.send_error(500, "erro interno no handler")
            except Exception:
                pass
            return None

    return wrapper


def block_path_traversal(path: Any) -> Optional[Dict[str, Any]]:
    """Rejeita caminhos com segmento ``..`` (traversal, inclusive codificado).

    Retorna None quando seguro; dict de bloqueio quando contém ``..``.
    Falha interna também bloqueia (fail-closed).
    """
    try:
        decoded = urllib.parse.unquote(urllib.parse.unquote(str(path or "")))
        parts = [p for p in re.split(r"[\\/]+", decoded) if p]
        if ".." in parts:
            return {
                "ok": False,
                "reason": "sequência '..' não é permitida no caminho",
                "path": decoded,
            }
        return None
    except Exception:
        return {
            "ok": False,
            "reason": "não foi possível validar o caminho",
            "path": str(path or ""),
        }


def sanitize_input(value: Any,
                   max_len: Optional[int] = 1024) -> Optional[Dict[str, Any]]:
    """Remove caracteres de controle, espaços das pontas e limita o tamanho.

    Retorna dict ``{"sanitized": str, "safe": bool}`` para strings e None
    para outros tipos. Nunca lança exceção para fora.
    """
    try:
        if not isinstance(value, str):
            return None
        original = value
        cleaned = _CTRL_RE.sub("", value).strip()
        changed = cleaned != original
        if max_len is not None and max_len >= 0 and len(cleaned) > max_len:
            cleaned = cleaned[:max_len]
            changed = True
        return {"sanitized": cleaned, "safe": not changed}
    except Exception:
        return None