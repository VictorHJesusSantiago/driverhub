# -*- coding: utf-8 -*-
from __future__ import annotations

"""CSV simples: conversão para texto e persistência em arquivo."""

import csv
import io
import os
from typing import Any, List, Optional

_ENCODINGS = ("utf-8", "iso-8859-1")


def to_csv(rows: List[Any]) -> str:
    """Serializa linhas (listas/iteráveis) em texto CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    for row in rows or []:
        try:
            writer.writerow([_cell(v) for v in row])
        except Exception:
            continue
    return buffer.getvalue()


def _cell(value: Any) -> str:
    return "" if value is None else str(value)


def _decode(data: bytes) -> Optional[str]:
    bom = b"\xef\xbb\xbf"
    raw = data[len(bom):] if data.startswith(bom) else data
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return None


def from_csv(text: Any) -> List[List[str]]:
    """Interpreta texto/bytes CSV (utf-8 ou ISO-8859-1). Nunca lança."""
    try:
        if text is None:
            return []
        if isinstance(text, bytes):
            decoded = _decode(text)
            if decoded is None:
                return []
            text = decoded
        else:
            text = str(text)
        text = text.lstrip("\ufeff")
        reader = csv.reader(io.StringIO(text), strict=False)
        return [list(row) for row in reader]
    except Exception:
        return []


def append_row(path: str, row: Any, encoding: str = "utf-8") -> bool:
    """Adiciona uma linha ao arquivo CSV (cria diretório se preciso). Nunca lança."""
    try:
        target = os.path.abspath(str(path))
        parent = os.path.dirname(target) or "."
        os.makedirs(parent, exist_ok=True)
        enc = encoding if encoding in _ENCODINGS else "utf-8"
        with open(target, "a", encoding=enc, newline="") as f:
            writer = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            writer.writerow([_cell(v) for v in (row or [])])
        return True
    except Exception:
        return False


def read_rows(path: str) -> List[List[str]]:
    """Lê todas as linhas do arquivo CSV. Nunca lança."""
    try:
        if not os.path.isfile(str(path)):
            return []
        with open(str(path), "rb") as f:
            raw = f.read()
        return from_csv(raw)
    except Exception:
        return []