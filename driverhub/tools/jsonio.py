# -*- coding: utf-8 -*-
"""Leitura/escrita de JSON com tolerância a erros e suporte multilíngue."""
from __future__ import annotations

import json
import os
from typing import Any, Optional


def load(path: str, default: Any = None) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default


def load_text(path: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except Exception:
        return None


def save(path: str, data: Any, indent: Optional[int] = 2) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception:
        return False


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None