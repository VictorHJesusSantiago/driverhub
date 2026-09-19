# -*- coding: utf-8 -*-
"""Hashing e verificações de integridade (MD5, SHA-1, SHA-256)."""
from __future__ import annotations

import hashlib
import os
from typing import Optional


def _digest(path: str, algo: str, chunk: int = 65536) -> Optional[str]:
    h = hashlib.new(algo)
    try:
        with open(path, "rb") as f:
            while True:
                block = f.read(chunk)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def md5(path: str) -> Optional[str]:
    return _digest(path, "md5")


def sha1(path: str) -> Optional[str]:
    return _digest(path, "sha1")


def sha256(path: str) -> Optional[str]:
    return _digest(path, "sha256")


def verify_file(path: str, expected: str, algo: Optional[str] = None) -> bool:
    """Compara o hash do arquivo com o esperado (auto-detecção do algoritmo)."""
    if not os.path.isfile(path):
        return False
    exp = (expected or "").strip().lower()
    if not exp:
        return True
    if algo is None:
        algo = "sha256" if len(exp) == 64 else "sha1" if len(exp) == 40 else "md5"
    return _digest(path, algo) == exp


def data_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()