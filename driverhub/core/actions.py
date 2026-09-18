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


def relaunch_admin(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    """Reexecuta o DriverHub com privilégios elevados (UAC / pkexec / sudo)."""
    import shlex
    os_info = platform.detect_os()
    args = argv or sys.argv[1:]
    cmd = shlex.join(["python", "-m", "driverhub"] + args) if args else shlex.join(["python", "-m", "driverhub"])
    try:
        if os_info["system"] == "windows":
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                                " -m driverhub " + " ".join(args),
                                                None, 1)
            return {"ok": True, "detail": "Solicitação de elevação enviada (UAC)."}
        if os_info["system"] == "linux":
            for elev in (_full_cmd_sh("pkexec"), _full_cmd_sh("sudo")):
                if elev:
                    r = platform._run([elev] + ["python", "-m", "driverhub"] + args, timeout=300)
                    return {"ok": r != "", "detail": (r or f"Executado via {elev}").strip()[:300]}
            return {"ok": False, "detail": "Nenhum elevador (pkexec/sudo) disponível."}
        if os_info["system"] == "darwin":
            r = platform._run(_full_cmd_sh("sudo") + ["python", "-m", "driverhub"] + args or [])
            return {"ok": r != "", "detail": r[:300]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": f"Falha ao elevar: {exc}"}
    return {"ok": False, "detail": check_admin()["hint"]}


def _full_cmd_sh(name: str) -> Optional[str]:
    return shutil.which(name)


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


def run_check(db: Database) -> Dict[str, Any]:
    """Verificação de saúde: dispositivos com problema + sugestões do catálogo."""
    devices = db.list_devices()
    problems = [d for d in devices if d.get("status") == "problem"]
    from ..core import catalog as cat_mod
    catalog_entries = db.catalog_search()
    suggestions: List[Dict[str, Any]] = []
    for dev in problems:
        v = (dev.get("vendor") or "").lower()
        for e in catalog_entries:
            if any(k in v for k in ("intel", "amd", "nvidia", "realtek", "broadcom",
                                    "qualcomm", "mediatek", "lenovo", "dell", "hp",
                                    "acer", "asus", "msi", "gigabyte", "sonix")):
                ev = e["vendor"].lower()
                if any(k in v for k in ("amd",)) and ev == "amd":
                    suggestions.append({"device": dev["name"], "catalog": e})
                    break
                if any(k in v for k in ("nvidia",)) and ev == "nvidia":
                    suggestions.append({"device": dev["name"], "catalog": e})
                    break
                if any(k in v for k in ("realtek",)) and ev == "realtek":
                    suggestions.append({"device": dev["name"], "catalog": e})
                    break
    # deduplica sugestões
    seen = set()
    uniq = []
    for s in suggestions:
        key = (s["catalog"]["vendor"], s["catalog"]["url"])
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    report = {
        "os": platform.detect_os(),
        "admin": check_admin(),
        "devices": len(devices),
        "problems": problems,
        "problems_count": len(problems),
        "suggestions": uniq[:20],
        "suggestions_count": len(uniq),
        "catalog": db.catalog_count(),
        "drivers": len(db.list_drivers()),
    }
    db.log("check", f"{len(problems)} problema(s), {len(uniq)} sugestão(ões)",
           "verificação de saúde", ok=(len(problems) == 0))
    return report


def run_backup(db: Database, dest: Optional[str] = None) -> Dict[str, Any]:
    """Backup completo: banco de dados + drivers publicados (Windows) exportados."""
    import json
    os_info = platform.detect_os()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = dest or os.path.join(os.path.expanduser("~"), f"driverhub-backup-{stamp}")
    os.makedirs(dest, exist_ok=True)
    files = []
    try:
        import shutil as _sh
        db_src = db.path
        db_dst = os.path.join(dest, "driverhub.db")
        _sh.copy2(db_src, db_dst)
        files.append(db_dst)
    except Exception as exc:
        return {"ok": False, "detail": f"Falha ao copiar o banco: {exc}"}
    payload: Dict[str, Any] = {
        "created": stamp, "os": os_info["name"], "version": "0.9.0",
        "devices": db.list_devices(), "drivers": db.list_drivers(),
        "catalog": db.catalog_search(term=""), "history": db.history(limit=10000),
    }
    manifest_path = os.path.join(dest, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    files.append(manifest_path)
    db.log("backup", dest, f"{len(files)} arquivos", ok=True)
    return {"ok": True, "dest": dest, "files": files, "detail": f"Backup criado em {dest}"}


def run_restore(db: Database, source: str) -> Dict[str, Any]:
    """Restaura um backup (base de dados). O restante do SO não é alterado."""
    import glob
    if os.path.isdir(source):
        candidates = glob.glob(os.path.join(source, "driverhub.db"))
        if not candidates:
            return {"ok": False, "detail": f"Backup '{source}' não contém driverhub.db."}
        source = candidates[0]
    if not os.path.isfile(source):
        return {"ok": False, "detail": f"Arquivo de backup '{source}' não encontrado."}
    os_info = platform.detect_os()
    if not os_info["admin"]:
        return {"ok": False, "detail": check_admin()["hint"]}
    try:
        db.close()
        import shutil as _sh
        _sh.copy2(source, db.path)
        restored = Database(db.path)
        count = restored.stats()
        restored.log("restore", source, "base restaurada do backup", ok=True)
        restored.close()
        return {"ok": True, "detail": f"Base restaurada: {count}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": f"Falha ao restaurar: {exc}"}


def run_upgrade() -> Dict[str, Any]:
    """Auto-atualização do DriverHub a partir do repositório git local."""
    if not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), ".git")):
        return {"ok": False,
                "detail": "Não é um checkout git. Use 'pip install -U driverhub' ou atualize manualmente."}
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    r = platform._run(["git", "-C", repo, "pull", "--ff-only"], timeout=120)
    ok = "already up to date" in r.lower() or "atualizado" in r.lower() or "fast-forward" in r.lower()
    return {"ok": ok or "error" not in r.lower(), "detail": r.strip()[:300], "output": r}