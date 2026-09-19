# -*- coding: utf-8 -*-
"""Motores de driver por sistema operacional.

Este pacote expõe a fábrica :func:`create_engine`, a listagem
:func:`all_engines` e o carregamento preguiçoso :func:`load_engines`, além de
reexportar a classe base :class:`DriverEngine`. O registro de motores fica em
:mod:`driverhub.core.engines.registry`.

Todas as importações internas são feitas dentro de funções (lazy) para evitar
ciclos e manter cada módulo importável isoladamente.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

__all__ = [
    "DriverEngine",
    "create_engine",
    "all_engines",
    "load_engines",
]

#: Mapeamento sys.platform -> nome de motor.
_PLATFORM_MAP = {
    "win32": "windows",
    "cygwin": "windows",
    "msys": "windows",
    "linux": "linux",
    "linux2": "linux",
    "darwin": "macos",
}


def __getattr__(name: str) -> Any:
    """Reexportação preguiçosa de :class:`DriverEngine` (PEP 562)."""
    if name == "DriverEngine":
        from .base import DriverEngine  # lazy
        return DriverEngine
    raise AttributeError(f"módulo {__name__!r} não tem atributo {name!r}")


def load_engines() -> List[str]:
    """Importa (lazy) os motores padrão e os registra.

    Retorna a lista de nomes de motores disponíveis após o carregamento.
    Nunca lança exceção: falhas de import são silenciadas.
    """
    from . import registry  # lazy

    factories = (
        ("windows", "windows.base", "WindowsEngine"),
        ("linux", "linux.base", "LinuxEngine"),
        ("macos", "macos.base", "MacOSEngine"),
    )
    for name, module, attr in factories:
        try:
            mod = __import__(f"{__name__}.{module}", fromlist=[attr])
            registry.register(name, getattr(mod, attr))
        except Exception:
            continue
    return registry.names()


def create_engine(os_name: Optional[str] = None,
                  db: Optional[Any] = None) -> Optional[Any]:
    """Cria uma instância de motor para o SO indicado (padrão: SO atual).

    Retorna ``None`` quando o motor não pôde ser criado. Nunca lança.
    """
    from . import registry  # lazy

    if not registry.available():
        load_engines()
    name = (os_name or _current_os()).lower()
    factory = registry.get(name)
    if factory is None:
        return None
    try:
        return factory(db=db)
    except TypeError:
        pass
    except Exception:
        pass
    try:
        return factory()
    except Exception:
        return None


def all_engines() -> Dict[str, Any]:
    """Retorna {nome_do_so: classe_do_motor} para todos os motores conhecidos."""
    from . import registry  # lazy

    if not registry.available():
        load_engines()
    return {name: registry.get(name) for name in registry.names()}


def _current_os() -> str:
    return _PLATFORM_MAP.get(sys.platform, "unknown")