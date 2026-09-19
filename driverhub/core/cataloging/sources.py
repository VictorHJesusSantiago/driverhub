# -*- coding: utf-8 -*-
from __future__ import annotations

"""Fontes remotas: manifest via urllib com falha segura e filtro oficial."""

import json
from typing import Any, Dict, List, Optional
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

_USER_AGENT = "DriverHub/1.0 (gerenciador universal de drivers)"


def fetch(url: str, timeout: float = 8.0) -> Optional[str]:
    """Baixa a URL e devolve o texto (utf-8). Nunca lança."""
    if not url:
        return None
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=max(1.0, float(timeout))) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def fetch_json(url: str, timeout: float = 8.0) -> Any:
    """Baixa a URL e interpreta como JSON. Nunca lança."""
    text = fetch(url, timeout)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def official_host(url: str) -> Optional[str]:
    """Domínio oficial permitido do host da URL, ou None."""
    try:
        host = (urlparse(str(url)).hostname or "").lower()
    except Exception:
        return None
    for domain in OFFICIAL_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return domain
    return None


def is_official(url: str) -> bool:
    """True se a URL pertence a um host da lista oficial."""
    return bool(official_host(url))


def filter_official(entries: List[Any]) -> List[Any]:
    """Filtra entradas deixando apenas as de URLs oficiais."""
    out: List[Any] = []
    for entry in entries or []:
        try:
            url = ""
            if isinstance(entry, dict):
                url = str(entry.get("url") or "")
            else:
                url = str(getattr(entry, "url", "") or "")
            if url and is_official(url):
                out.append(entry)
        except Exception:
            continue
    return out