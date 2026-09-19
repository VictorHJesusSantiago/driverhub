# -*- coding: utf-8 -*-
"""``pkgutil`` no macOS: pacotes instalados, arquivos e receitas (drivers).

Área de trabalho de receitas de pacotes .pkg de drivers de terceiros
(quando instalados via instalador). Nunca lança exceção.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List


def _run(args: List[str], timeout: int = 60) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def packages() -> List[str]:
    """Lista IDs de pacotes de receitas (``pkgutil --pkgs``)."""
    out = _run(["pkgutil", "--pkgs"], timeout=90)
    return [line for line in (out or "").splitlines() if line.strip()]


def files(pkgid: str) -> List[str]:
    """Arquivos instalados por um pacote (``pkgutil --files <id>``)."""
    if not pkgid:
        return []
    out = _run(["pkgutil", "--files", pkgid], timeout=90)
    return [line for line in (out or "").splitlines() if line.strip()]


def receipt(pkgid: str) -> Dict[str, Any]:
    """Metadados da receita do pacote (``pkgutil --pkg-info <id>``).

    Retorna dict com version/location/volume etc.
    """
    out = _run(["pkgutil", "--pkg-info", pkgid], timeout=60)
    info: Dict[str, Any] = {"ok": bool(out), "package": pkgid}
    for line in (out or "").splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            info[key.strip().lower().replace(" ", "_")] = value.strip()
    info["detail"] = f"Receita de {pkgid}" if info["ok"] else \
                     f"Pacote {pkgid} sem receita."
    return info


def driver_packages() -> List[Dict[str, Any]]:
    """Pacotes que parecem ser de drivers/kexts (pela receita)."""
    result: List[Dict[str, Any]] = []
    for pkgid in packages():
        low = pkgid.lower()
        if any(tok in low for tok in ("kext", "driver", "gpu", "display",
                                      "audio", "nvidia", "amd")):
            meta = receipt(pkgid)
            result.append({
                "id": pkgid, "name": pkgid.rsplit(".", 1)[-1],
                "version": meta.get("version", ""),
                "install_location": meta.get("install_location", ""),
                "source": "macos:pkgutil",
            })
    return result


def driver_has_kext_content(pkgid: str) -> bool:
    """Diz se um pacote contém conteúdo de KEXT (extensão .kext)."""
    f = files(pkgid)
    return any(".kext" in path for path in f) if f else False


def softwareupdate_list() -> Dict[str, Any]:
    """Lista atualizações de software pendentes (``softwareupdate -l``)."""
    out = _run(["softwareupdate", "-l"], timeout=120)
    updates: List[str] = []
    for line in (out or "").splitlines():
        stripped = line.strip()
        if stripped and (stripped.startswith("*") or ":" in stripped):
            updates.append(stripped)
    return {"ok": bool(out), "updates": updates, "count": len(updates),
            "detail": f"{len(updates)} atualização(ões) de software.",
            "raw": out}