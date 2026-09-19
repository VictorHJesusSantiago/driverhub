# -*- coding: utf-8 -*-
"""Helpers HTTP comuns à API web do DriverHub (biblioteca padrão).

Estas funções são framework-free: recebem um ``handler`` (objeto no estilo
``BaseHTTPRequestHandler``, ou uma string de caminho) e devolvem dados/erros
sem depender de nenhuma biblioteca externa.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass

MAX_BODY_BYTES = 1024 * 1024  # 1 MiB
CONFIRM_VALUES = ("1", "true", "yes")


@dataclass
class ApiError(Exception):
    """Erro de API com mensagem em pt-BR e status HTTP sugerido."""

    message: str = "erro"
    status: int = 400

    def __str__(self) -> str:
        return self.message


def json_response(data, status: int = 200, handler=None):
    """Serializa ``data`` como JSON UTF-8.

    Se ``handler`` for informado, grava a resposta HTTP diretamente; caso
    contrário devolve um objeto ``{"status", "body", "content_type"}`` pronto
    para o chamador escrever (mantém a função pura).
    """
    if isinstance(data, ApiError):
        data, status = {"error": data.message}, data.status
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    ctype = "application/json; charset=utf-8"
    if handler is not None:
        handler.send_response(status)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(body)
        return None
    return {"status": status, "body": body, "content_type": ctype}


def read_body(handler):
    """Lê o corpo JSON de um POST respeitando Content-Length e o limite de bytes.

    Devolve um ``dict`` (vazio se não houver corpo) e levanta :class:`ApiError`
    se o corpo for grande demais ou o JSON inválido.
    """
    try:
        length = int(handler.headers.get("Content-Length") or 0)
    except (AttributeError, TypeError, ValueError):
        length = 0
    if length <= 0:
        return {}
    if length > MAX_BODY_BYTES:
        raise ApiError("corpo da requisição excede o limite de 1 MiB", 413)
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ApiError("corpo JSON inválido", 400)  # noqa: B904


def parse_query(handler):
    """Converte a query string do caminho em um ``dict`` de parâmetros."""
    path = getattr(handler, "path", None)
    if path is None:
        path = handler if isinstance(handler, str) else ""
    parsed = urllib.parse.urlparse(str(path))
    return dict(urllib.parse.parse_qsl(parsed.query))


def method_guard(handler, name: str):
    """Exige que o método HTTP do handler seja ``name`` (senão 405)."""
    method = getattr(handler, "command", None)
    if method is None:
        method = handler if isinstance(handler, str) else ""
    if str(method).upper() != str(name).upper():
        raise ApiError("método não permitido", 405)
    return True