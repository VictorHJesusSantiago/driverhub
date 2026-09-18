# -*- coding: utf-8 -*-
"""Ações de alto nível: escaneamento, instalação, atualização e remoção."""
from __future__ import annotations

import os
import shutil
import sys
import time
from typing import Any, Dict, List, Optional

from . import catalog as catalog_mod
from . import linux, macos, platform, windows
from .database import Database


def engine():
    """Retorna o dispatcher correto para o SO atual."""
    sys_ = platform.detect_os()["system"]
    if sys_ == "windows":
        return windows
    if sys_ == "linux":
        return linux
    if sys_ == "darwin":
        return macos
    return None


def check_admin() -> Dict[str, Any]:
    info = platform.detect_os()
    return {
        "admin": info["admin"],
        "system": info["system"],
        "name": info["name"],
        "hint": ("" if info["admin"] else
                 "Operações de instalação/remoção exigem privilégios de administrador "
                 "(Windows: executar como Administrador; Linux/macOS: usar sudo)."),
    }


def doctor(db: Database) -> Dict[str, Any]:
    """Diagnóstico completo do ambiente (para logs e solução de problemas)."""
    check = check_admin()
    os_info = platform.detect_os()
    sys_ = os_info["system"]
    report: Dict[str, Any] = {
        "os": os_info,
        "admin": check,
        "engines": {},
        "tools": {},
        "catalog": db.catalog_count(),
    }
    for tool in (["pnputil", "powershell", "wmic"] if sys_ == "windows" else
                 (["lspci", "lsusb", "lsmod", "modinfo", "modprobe", "dkms",
                   "apt", "dnf", "pacman", "nvidia-smi", "glxinfo"] if sys_ == "linux" else
                  ["kextstat", "system_profiler", "brew"])):
        exe = shutil.which(tool)
        report["tools"][tool] = "ok" if exe else "missing"
    return report


def run_scan(db: Database) -> Dict[str, Any]:
    """Escaneia o sistema inteiro: inventário + drivers + catálogo."""
    eng = engine()
    result: Dict[str, Any] = {"os": platform.detect_os(), "device_class": platform.detect_device_class()}
    if eng is None:
        result["error"] = "SO não suportado para varredura de drivers."
        db.log("scan", platform.detect_os()["name"], result.get("error", ""), ok=False)
        return result
    data = eng.scan_devices_and_drivers()
    devices = data.get("devices", [])
    drivers = data.get("drivers", [])
    # enriquece devices com info de driver quando possível
    n_dev, n_drv = db.save_devices(devices), db.save_drivers(drivers)
    result["devices"] = devices
    result["drivers"] = drivers
    result["devices_count"] = n_dev
    result["drivers_count"] = n_drv
    result["catalog"] = db.catalog_count()
    result["timestamp"] = time.time()
    db.log("scan", f"{n_dev} devices, {n_drv} drivers",
           f"SO: {result['os']['name']}", ok=True)
    return result


def run_install(db: Database, target: str, force_package: bool = False) -> Dict[str, Any]:
    """Instala um driver a partir de um INF (Windows) ou módulo (Linux)."""
    eng = engine()
    if eng is None:
        return {"ok": False, "detail": "SO não suportado."}
    os_info = platform.detect_os()
    if not os_info["admin"]:
        db.log("install", target, "sem admin", ok=False)
        return {"ok": False, "detail": check_admin()["hint"]}
    if os_info["system"] == "windows":
        if not os.path.isfile(target) or not target.lower().endswith(".inf"):
            return {"ok": False, "detail": f"{target} não é um arquivo .inf válido."}
        res = eng.install_driver_inf(target)
    elif os_info["system"] == "linux":
        if target.endswith(".run"):
            cmd = f'sh "{target}" '
            r = platform._run([cmd], timeout=600)
            res = {"ok": "error" not in r.lower(), "detail": r[:500]}
        elif os.path.isfile(target):
            r = platform._run(["insmod", target], timeout=60)
            res = {"ok": "error" not in r.lower() and r != "", "detail": r[:500]}
        else:
            res = eng.install_module(target, permanent=force_package)
    else:
        return {"ok": False, "detail": "Instalação manual não suportada neste SO."}
    db.log("install", target, res.get("detail", "")[:300], res.get("ok", False))
    return res


def run_remove(db: Database, target: str, force: bool = False) -> Dict[str, Any]:
    """Remove um driver (Windows: pnputil; Linux: módulo)."""
    eng = engine()
    if eng is None:
        return {"ok": False, "detail": "SO não suportado."}
    os_info = platform.detect_os()
    if not os_info["admin"]:
        db.log("remove", target, "sem admin", ok=False)
        return {"ok": False, "detail": check_admin()["hint"]}
    if os_info["system"] == "windows":
        res = eng.remove_driver(target, force=force)
        if res.get("ok"):
            db.delete_driver_row(target)
    elif os_info["system"] == "linux":
        res = eng.unload_module(target, persistent=force)
    else:
        return {"ok": False, "detail": "Remoção não suportada neste SO."}
    db.log("remove", target, res.get("detail", "")[:300], res.get("ok", False))
    return res


def run_update(db: Database, target: str, inf_path: Optional[str] = None) -> Dict[str, Any]:
    """Atualiza (recarrega) um driver. Se um .inf novo for dado, re-instala."""
    eng = engine()
    if eng is None:
        return {"ok": False, "detail": "SO não suportado."}
    os_info = platform.detect_os()
    if inf_path:
        if not os_info["admin"]:
            return {"ok": False, "detail": check_admin()["hint"]}
        result = run_install(db, inf_path)
        result["action"] = "update"
        db.log("update", target, result.get("detail", "")[:300], result.get("ok", False))
        return result
    if os_info["system"] == "linux":
        if eng.module_details(target):
            res = eng.install_module(target)
            db.log("update", target, res.get("detail", "")[:300], res.get("ok", False))
            return res
    row = db.get_driver(target)
    db.log("update", target, "recarga solicitada", ok=True)
    return {"ok": True, "detail": f"Recarga registrada para {target} (mantido versão atual).",
            "row": row}


def catalog_sync(db: Database, manifest: str = catalog_mod.DEFAULT_MANIFEST) -> Dict[str, Any]:
    return catalog_mod.update(db, manifest)


def catalog_list(db: Database, category: str = "", term: str = "") -> List[Dict[str, Any]]:
    return db.catalog_search(term=term, category=category)


def catalog_categories(db: Database) -> List[str]:
    return db.catalog_categories()