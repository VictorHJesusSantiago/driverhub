# -*- coding: utf-8 -*-
"""Drivers gráficos Mesa no Linux: detecção de pacotes e renderer OpenGL.

Verifica pacotes Mesa instalados (mesa, mesa-utils, vulkan-icd), consulta o
renderer via ``glxinfo`` quando disponível e mapeia fornecedores OpenGL.
Nenhuma função lança exceção.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List

#: Marcas OpenGL -> fornecedor de driver gráfico.
VENDOR_TABLE: List[Dict[str, str]] = [
    {"mark": "nvidia", "vendor": "NVIDIA"},
    {"mark": "amd", "vendor": "AMD"},
    {"mark": "ati", "vendor": "AMD (ATI)"},
    {"mark": "intel", "vendor": "Intel"},
    {"mark": "mesa", "vendor": "Mesa"},
    {"mark": "x.org", "vendor": "X.org"},
    {"mark": "vmware", "vendor": "VMware"},
    {"mark": "microsoft", "vendor": "Microsoft (WSL)"},
    {"mark": "qualcomm", "vendor": "Qualcomm"},
    {"mark": "arm", "vendor": "ARM (Mali)"},
]

_MESA_PKG_HINTS = ("mesa", "libgl1", "libgl1-mesa", "mesa-utils",
                   "vulkan-icd", "mesa-vulkan-drivers",
                   "vulkan-intel", "vulkan-radeon",
                   "libglx-mesa0", "libegl-mesa0")


def _run(args: List[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def detect_installed() -> Dict[str, Any]:
    """Detecta pacotes Mesa instalados por binário/arquivo.

    Também consulta o gerenciador de pacotes quando viável. Retorna dict.
    """
    found: List[Dict[str, str]] = []

    if shutil.which("glxinfo"):
        found.append({"name": "glxinfo", "source": "bin", "detail": "mesa-utils"})
    if shutil.which("eglinfo"):
        found.append({"name": "eglinfo", "source": "bin", "detail": "mesa-utils"})
    if shutil.which("vulkaninfo"):
        found.append({"name": "vulkaninfo", "source": "bin", "detail": "vulkan-tools"})

    for path in ("/usr/lib/dri", "/usr/lib64/dri"):
        if os.path.isdir(path):
            found.append({"name": os.path.basename(path), "source": "dir",
                          "detail": path})

    for icd in ("/usr/share/vulkan/icd.d", "/usr/lib/x86_64-linux-gnu/glvnd/egl_vendor.d"):
        if os.path.isdir(icd):
            try:
                files = [os.path.join(icd, f) for f in os.listdir(icd)
                         if f.endswith(".json")]
            except Exception:
                files = []
            found.extend({"name": os.path.basename(f), "source": "icd",
                          "detail": f} for f in files)

    found.extend(_detect_by_package_manager())

    return {"ok": bool(found), "found": found, "count": len(found),
            "detail": f"{len(found)} indicação(ões) de Mesa/Vulkan."}


def _detect_by_package_manager() -> List[Dict[str, str]]:
    from .base import detect_package_manager  # lazy

    pm = detect_package_manager()
    found: List[Dict[str, str]] = []
    if not pm:
        return found
    try:
        if pm == "apt":
            lines = _run(["dpkg", "-l"]).splitlines()
        elif pm == "dnf":
            lines = _run(["dnf", "list", "installed"]).splitlines()
        elif pm == "pacman":
            lines = _run(["pacman", "-Q"]).splitlines()
        else:
            return found
    except Exception:
        return found
    for line in lines:
        name = (line.split()[0] if line.split() else "").lower()
        if any(hint in name for hint in _MESA_PKG_HINTS):
            found.append({"name": name, "source": pm, "detail": "pacote instalado"})
    return found


def renderer() -> Dict[str, Any]:
    """Consulta o renderer OpenGL via ``glxinfo -B`` (se instalado)."""
    exe = shutil.which("glxinfo")
    if not exe:
        return {"ok": False, "renderer": "", "version": "", "vendor": "",
                "detail": "glxinfo (mesa-utils) não instalado."}
    out = _run([exe, "-B"], timeout=30)
    fields: Dict[str, str] = {}
    for line in (out or "").splitlines():
        match = re.match(r"^\s*([^:]+):\s*(.*)$", line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            fields[key] = match.group(2).strip()
    renderer_str = (fields.get("opengl_renderer_string")
                    or fields.get("renderer") or "")
    version = fields.get("opengl_version_string", "")
    return {
        "ok": bool(renderer_str),
        "renderer": renderer_str,
        "version": version,
        "vendor": vendor_of(renderer_str),
        "detail": renderer_str or "Nenhum renderer detectado.",
        "raw": out,
    }


def vendor_of(renderer: str) -> str:
    """Mapeia o nome do renderer para o fornecedor de driver OpenGL."""
    low = (renderer or "").lower()
    for entry in VENDOR_TABLE:
        if entry["mark"] in low:
            return entry["vendor"]
    return "desconhecido"


def vulkan_support() -> Dict[str, Any]:
    """Verifica suporte Vulkan (ICD presenti)."""
    icd_dirs = ("/usr/share/vulkan/icd.d", "/etc/vulkan/icd.d",
                "/usr/lib/x86_64-linux-gnu/glvnd/vulkan")
    icds: List[str] = []
    for folder in icd_dirs:
        if os.path.isdir(folder):
            try:
                icds.extend(os.path.join(folder, f) for f in os.listdir(folder)
                            if f.endswith(".json"))
            except Exception:
                continue
    return {"ok": bool(icds), "icds": icds, "count": len(icds),
            "detail": f"{len(icds)} ICD Vulkan encontrado(s)."}