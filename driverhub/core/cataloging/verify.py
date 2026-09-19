# -*- coding: utf-8 -*-
from __future__ import annotations

"""Verificação de drivers: checksum, origem oficial e assinatura heurística."""

import hashlib
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

OFFICIAL_DOMAINS: tuple = (
    "nvidia.com",
    "amd.com",
    "intel.com",
    "realtek.com",
    "broadcom.com",
    "samsung.com",
    "sandisk.com",
    "westerndigital.com",
    "synaptics.com",
    "elan-touch.com",
    "mediatek.com",
    "qualcomm.com",
    "tp-link.com",
    "microsoft.com",
)

_SIGNED_EXTS = frozenset({".cat", ".sys", ".dll", ".exe"})
_SIGN_MARKERS = (b"Microsoft Windows", b"Digital Signature", b"SignedData", b"PKCS#7")
_SIGNED_ATTRS = 64  # bytes a partir do início procurando por headers de assinatura


def _digest(path: str, algo: str, chunk: int = 65536) -> Optional[str]:
    try:
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            while True:
                block = f.read(chunk)
                if not block:
                    break
                h.update(block)
        return h.hexdigest()
    except Exception:
        return None


def verify_checksum(file: str, algo: str, expected: str) -> bool:
    """Compara o hash do arquivo com o esperado. Nunca lança."""
    if not file or not os.path.isfile(str(file)):
        return False
    expected = str(expected or "").strip().lower()
    if not expected or not algo:
        return True
    digest = _digest(str(file), str(algo))
    return bool(digest and digest == expected)


def is_official(url: str) -> bool:
    """True se a URL aponta para um domínio oficial conhecido."""
    try:
        host = (urlparse(str(url)).hostname or "").lower()
    except Exception:
        host = ""
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def signature_check(cat_path: str) -> Dict[str, Any]:
    """Inspeção heurística de assinatura em .cat/.dll/.sys. Nunca lança."""
    base = {
        "ok": False,
        "reason": "Arquivo não encontrado.",
        "extension": "",
        "size": 0,
        "method": "",
    }
    try:
        path = str(cat_path)
        if not os.path.isfile(path):
            return base
        stat = os.stat(path)
        base["size"] = stat.st_size
        ext = os.path.splitext(path)[1].lower()
        base["extension"] = ext
        if stat.st_size == 0:
            base["reason"] = "Arquivo vazio, sem assinatura aparente."
            return base
        with open(path, "rb") as f:
            head = f.read(512 * 1024)
        if ext not in _SIGNED_EXTS:
            base["reason"] = f"Extensão '{ext or 'desconhecida'}' não é alvo de assinatura."
            return base
        if ext == ".cat":
            if b"Microsoft Windows" in head or b"CATALOG" in head:
                base.update(ok=True, reason="Catálogo de segurança da Microsoft encontrado.", method="catalog-marker")
                return base
        for marker in _SIGN_MARKERS:
            if marker in head:
                base.update(ok=True, reason=f"Marcador de assinatura '{marker.decode(errors='ignore')}' presente.", method="marker")
                return base
        if _SIGNED_ATTRS <= len(head) and (b"\x30\x82" in head[: _SIGNED_ATTRS + 8]):
            base.update(ok=True, reason="Estrutura PKCS#7 (DER) detectada no cabeçalho.", method="pkcs7-header")
            return base
        base["reason"] = "Nenhum marcador de assinatura heurística encontrado."
        return base
    except Exception:
        base["reason"] = "Falha ao inspecionar o arquivo."
        return base