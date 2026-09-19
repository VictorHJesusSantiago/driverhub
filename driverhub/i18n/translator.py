# -*- coding: utf-8 -*-
"""Tradutor simples (dicionário + fallback pt-BR). Carrega os códigos de
idioma em ``en``/``pt_br`` dinamicamente para facilitar novos idiomas."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .pt_br import MSGS as PT_BR
from .en import MSGS as EN_US

_STRINGS: Dict[str, Dict[str, str]] = {"pt-BR": PT_BR, "en-US": EN_US}
_current: str = "pt-BR"


class Translator:
    def __init__(self, language: str = "pt-BR"):
        self.language = language

    def tr(self, key: str, **kwargs: Any) -> str:
        table = _STRINGS.get(self.language) or PT_BR
        tmpl = table.get(key) or PT_BR.get(key, key)
        try:
            return tmpl.format(**kwargs)
        except Exception:
            return tmpl

    def set_language(self, language: str) -> None:
        if language in _STRINGS:
            self.language = language


def set_language(language: str) -> None:
    global _current
    if language in _STRINGS:
        _current = language


def t(key: str, **kwargs: Any) -> str:
    """Tradução curta e global."""
    table = _STRINGS.get(_current) or PT_BR
    tmpl = table.get(key) or PT_BR.get(key, key)
    try:
        return tmpl.format(**kwargs)
    except Exception:
        return tmpl