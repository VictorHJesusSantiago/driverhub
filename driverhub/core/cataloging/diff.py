# -*- coding: utf-8 -*-
from __future__ import annotations

"""Comparação de versões e detecção de mudanças entre catálogos."""

from typing import Any, Dict, List

from .base import as_dict


def diff_versions(old: Any, new: Any) -> Dict[str, Any]:
    """Classifica a diferença entre duas versões. Nunca lança."""
    from driverhub.tools import semver  # lazy: utilitário genérico

    result = {
        "old": str(old or ""),
        "new": str(new or ""),
        "status": "equal",
        "up_to_date": True,
    }
    try:
        a = semver.parse(old)
        b = semver.parse(new)
        cmp = semver.compare(old, new) if (a is not None and b is not None) else None
        if cmp is None:
            if str(old or "") == str(new or ""):
                status = "equal"
            else:
                status = "unknown"
        elif cmp == 0:
            status = "equal"
        elif cmp < 0:
            status = "downgrade"
        else:
            a_major = a.get("major", 0) if a else 0
            b_major = b.get("major", 0) if b else 0
            a_minor = a.get("minor", 0) if a else 0
            b_minor = b.get("minor", 0) if b else 0
            if b_major > a_major:
                status = "major"
            elif b_minor > a_minor:
                status = "minor"
            else:
                status = "patch"
        result["status"] = status
        result["up_to_date"] = status in ("equal",)
        return result
    except Exception:
        result["status"] = "unknown"
        result["up_to_date"] = False
        return result


def compare_entries(a: Any, b: Any) -> Dict[str, Any]:
    """Detecta mudanças de versão/url/checksum entre duas entradas."""
    da = as_dict(a)
    db_catalog = as_dict(b)
    version_a = str(da.get("version") or "")
    version_b = str(db_catalog.get("version") or "")
    url_a = str(da.get("url") or "")
    url_b = str(db_catalog.get("url") or "")
    ca = dict(da.get("checksums") or {})
    cb = dict(db_catalog.get("checksums") or {})

    checksums = set(ca.items()) ^ set(cb.items())
    changed = bool(
        (version_a != version_b)
        or (url_a != url_b)
        or bool(checksums)
        or da.get("official", True) != db_catalog.get("official", True)
    )
    return {
        "changed": changed,
        "vendor": (str(da.get("vendor") or ""), str(db_catalog.get("vendor") or "")),
        "model": (str(da.get("model") or ""), str(db_catalog.get("model") or "")),
        "version_changed": version_a != version_b,
        "version": (version_a, version_b),
        "version_diff": diff_versions(version_a, version_b),
        "url_changed": url_a != url_b,
        "url": (url_a, url_b),
        "checksum_changed": bool(checksums),
        "checksums": (ca, cb),
    }


def summarize_changes(changes: List[Dict[str, Any]], limit: int = 20) -> List[str]:
    """Resumo em português das mudanças detectadas. Nunca lança."""
    lines: List[str] = []
    try:
        if not changes:
            return ["Nenhuma mudança detectada."]
        for entry in changes:
            if not isinstance(entry, dict):
                continue
            if not entry.get("changed"):
                continue
            label = "{0} {1}".format(
                str(entry.get("vendor", ("", ""))[0] if isinstance(entry.get("vendor"), tuple) else entry.get("vendor", "")),
                str(entry.get("model", ("", ""))[0] if isinstance(entry.get("model"), tuple) else entry.get("model", "")),
            ).strip()
            parts = []
            vold, vnew = entry.get("version", ("", ""))
            if entry.get("version_changed"):
                if vold and vnew:
                    parts.append(f"versão {vold} -> {vnew}")
                elif vnew:
                    parts.append(f"nova versão {vnew}")
            uold, unew = entry.get("url", ("", ""))
            if entry.get("url_changed"):
                parts.append("endereço atualizado")
            if entry.get("checksum_changed"):
                parts.append("checksum alterado")
            lines.append("{0}: {1}".format(label, ", ".join(parts) if parts else "atualizada"))
        lines = lines[: max(1, int(limit or 20))]
        return lines or ["Nenhuma mudança detectada."]
    except Exception:
        return ["Não foi possível resumir as mudanças."]