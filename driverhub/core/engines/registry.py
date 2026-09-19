# -*- coding: utf-8 -*-
"""Registro central de motores de driver por nome de sistema operacional.

Registro simples em memória (dict global) acessível por qualquer módulo do
DriverHub. Os motores são classes derivadas de ``DriverEngine`` registradas
pelo nome do SO (ex.: ``windows``, ``linux``, ``macos``).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

#: dict nome_do_so -> classe do motor.
_REGISTRY: Dict[str, Any] = {}


def register(name: str, engine_cls: Any) -> Any:
    """Registra (ou substitui) um motor pelo nome do SO.

    Também pode ser usado como decorator. Mantém a classe registrada.
    """
    key = (name or "").strip().lower()
    if not key or not engine_cls:
        return engine_cls
    _REGISTRY[key] = engine_cls
    return engine_cls


def get(name: str) -> Optional[Any]:
    """Retorna a classe do motor registrada para ``name`` (ou None).

    Tenta correspondência exata e, na falha, prefixo (ex.: ``windows`` para
    ``windows-11``). Nunca lança.
    """
    key = (name or "").strip().lower()
    if not key:
        return None
    if key in _REGISTRY:
        return _REGISTRY[key]
    for registered in _REGISTRY:
        if key.startswith(registered) or registered.startswith(key):
            return _REGISTRY[registered]
    return None


def available() -> List[Dict[str, str]]:
    """Lista os motores registrados como [{name, label}, ...] (ordena name)."""
    result: List[Dict[str, str]] = []
    for name in sorted(_REGISTRY):
        engine_cls = _REGISTRY[name]
        label = getattr(engine_cls, "label", name)
        result.append({"name": name, "label": str(label)})
    return result


def names() -> List[str]:
    """Nomes (sorted) de todos os motores registrados."""
    return sorted(_REGISTRY)


def size() -> int:
    """Quantidade de motores registrados."""
    return len(_REGISTRY)


def clear() -> None:
    """Remove todos os motores do registro (útil em testes)."""
    _REGISTRY.clear()