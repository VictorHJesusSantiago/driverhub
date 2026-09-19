# -*- coding: utf-8 -*-
from __future__ import annotations

"""Árvore de diretórios em texto com box-drawing (usando apenas os.walk)."""

import os
from typing import List, Optional

_BRANCH = "\u251c\u2500\u2500 "  # ├──
_LAST = "\u2514\u2500\u2500 "  # └──
_PIPE = "\u2502   "  # │
_BLANK = "    "
_ELLIPSIS = "\u2026"  # …

_DEFAULT_MAX_DEPTH = 3
_DEFAULT_MAX_ITEMS = 50


def _entries_at(path: str) -> List[str]:
    """Nomes imediatos (pastas e arquivos) via os.walk. Nunca lança."""
    try:
        if not os.path.isdir(str(path)):
            return []
        walker = os.walk(str(path))
        root, dirs, files = next(walker)
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        return dirs + files
    except Exception:
        return []


def node(path: str, depth: int = 0, is_last: bool = False) -> str:
    """Linha única com box-drawing para um caminho na profundidade dada."""
    try:
        name = os.path.basename(os.path.abspath(str(path))) or str(path)
        depth = max(0, int(depth or 0))
        if depth == 0:
            return name
        connector = _LAST if is_last else _BRANCH
        prefix = (_PIPE * (depth - 1)) + connector
        return prefix + name
    except Exception:
        return str(path)


def tree(path: str, max_depth: Optional[int] = None, max_items: Optional[int] = None) -> List[str]:
    """Lista de linhas com box-drawing descrevendo a árvore de `path`.

    Nunca lança; erros de permissão viram linhas vazias ou conteúdo parcial.
    """
    lines: List[str] = []
    try:
        depth_limit = max(0, int(max_depth if max_depth is not None else _DEFAULT_MAX_DEPTH))
        limit = max(1, int(max_items if max_items is not None else _DEFAULT_MAX_ITEMS))
        counter = [0]

        def walk(current: str, depth: int, is_last: bool, prefix: str):
            if counter[0] >= limit:
                return
            counter[0] += 1
            lines.append(prefix + node(current, depth, is_last) if depth else node(current, 0))
            if depth >= depth_limit:
                return
            children = _entries_at(current)
            if not children:
                return
            child_prefix = prefix + (_BLANK if is_last else _PIPE)
            last_index = len(children) - 1
            for i, name in enumerate(children):
                if counter[0] >= limit:
                    lines.append(child_prefix + _BRANCH + _ELLIPSIS + " (limite atingido)")
                    break
                walk(os.path.join(current, name), depth + 1, i == last_index, child_prefix)

        if os.path.isdir(str(path)):
            walk(str(path), 0, False, "")
        else:
            lines.append(node(str(path) if path else "", 0))
    except Exception:
        pass
    return lines