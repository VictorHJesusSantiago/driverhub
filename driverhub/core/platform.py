# -*- coding: utf-8 -*-
"""Detecção de plataforma, sistema operacional e inventário de hardware.

Compatível com Windows, Linux, macOS e sistemas móveis (Android via Termux,
iOS com ferramentas limitadas). Nenhuma dependência externa é obrigatória;
se ``psutil`` estiver instalado, informações extras são usadas.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None
    _HAS_PSUTIL = False


def _run(cmd: List[str], timeout: int = 30) -> str:
    """Executa um comando e retorna stdout+stderr tratado (sem exceção)."""
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        return (p.stdout or "").strip()
    except Exception:
        return ""


def _is_admin() -> bool:
    """True se o processo atual tem privilégios administrativos/root."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0  # type: ignore[attr-defined]


def _full_cmd(name: str, args: Any = ""):
    exe = shutil.which(name or "")
    if not exe:
        return None
    if args:
        return [exe, args]
    return [exe]


def detect_os() -> Dict[str, Any]:
    system = platform.system().lower()  # windows | linux | darwin
    if system == "windows":
        os_name = "Windows"
        release = platform.release() or ""
        ver = platform.version() or ""
        if "10.0" in ver and int((release or "0").split(".")[0]) >= 10:
            build = ver.split(".")[-1] if "." in ver else ""
            try:
                if int(build) >= 22000:
                    os_name = "Windows 11"
                else:
                    os_name = f"Windows 10 ({release})"
            except Exception:
                os_name = f"Windows 10/11 ({release})"
    elif system == "linux":
        os_name = "Linux"
        release = platform.libc_ver() or ""
        with open("/etc/os-release", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PRETTY_NAME="):
                    os_name = line.split("=", 1)[1].strip().strip('"')
                    break
        ver = platform.release()
    elif system == "darwin":
        os_name = "macOS"
        release = platform.mac_ver()[0]
        ver = release
    else:
        os_name = system.capitalize() or platform.system()
        release = platform.release()
        ver = release
    return {
        "system": system,
        "name": os_name,
        "release": release,
        "version": ver,
        "arch": platform.machine() or platform.architecture()[0] or "unknown",
        "python": platform.python_version(),
        "hostname": platform.node() or os.getenv("COMPUTERNAME", "unknown"),
        "admin": _is_admin(),
        "is_mobile": _is_mobile(),
        "kernel": platform.release(),
        "libc": _run(["ldd", "--version"])[:80] if system == "linux" else "",
    }


def _is_mobile() -> bool:
    if platform.system().lower() == "linux":
        # Android (Termux) tem variáveis características
        if os.getenv("PREFIX", "").startswith("/data/user"):
            return True
        if os.path.exists("/system/bin/app_process"):
            return True
    if os.getenv("ANDROID_ROOT") or os.getenv("ANDROID_DATA"):
        return True
    if sys.platform.startswith("ios"):  # prática: nada confiável em iOS
        return True
    return False


def detect_device_class() -> str:
    """Classifica o dispositivo: pc / notebook / mobile / server / vm."""
    info = detect_os()
    if info["is_mobile"]:
        return "mobile"
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
                data = f.read().lower()
            if "hypervisor" in data:
                return "vm"
        if sys.platform.startswith("win"):
            output = _run(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_ComputerSystem).Manufacturer"])
            if "vmware" in output.lower() or "virtualbox" in output.lower() or "microsoft" in output.lower() and "virtual" in output.lower():
                return "vm"
        if os.path.exists("/sys/class/dmi/id/product_name"):
            prod = open("/sys/class/dmi/id/product_name", encoding="utf-8", errors="replace").read().strip().lower()
            if prod in ("vmware virtual platform", "virtualbox", "kvm", "qemu"):
                return "vm"
    except Exception:
        pass
    return "pc"


def detect_ram() -> Dict[str, Any]:
    try:
        if _HAS_PSUTIL:
            vm = psutil.virtual_memory()
            return {
                "total": vm.total,
                "used": vm.used,
                "available": vm.available,
            }
    except Exception:
        pass
    if sys.platform.startswith("win"):
        out = _run(["wmic", "OS", "get", "TotalVisibleMemorySize", "/value"])
        m = re.search(r"TotalVisibleMemorySize=(\d+)", out)
        if m:
            total = int(m.group(1)) * 1024
            return {"total": total, "used": 0, "available": 0}
    elif os.path.exists("/proc/meminfo"):
        try:
            total = 0
            for line in open("/proc/meminfo", encoding="utf-8", errors="replace"):
                if line.lower().startswith("memtotal"):
                    total = int(line.split()[1]) * 1024
            return {"total": total, "used": 0, "available": 0}
        except Exception:
            pass
    return {"total": 0, "used": 0, "available": 0}


def detect_cpu() -> Dict[str, Any]:
    cpu: Dict[str, Any] = {"name": platform.processor() or "unknown", "cores": 0, "threads": 0}
    try:
        if _HAS_PSUTIL:
            cpu["threads"] = psutil.cpu_count(logical=True) or 0
            cpu["cores"] = psutil.cpu_count(logical=False) or 0
            f = psutil.cpu_freq()
            cpu["freq_mhz"] = round(f.current, 0) if f else None
    except Exception:
        pass
    if sys.platform.startswith("win"):
        out = _run(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Processor).Name"])
        if out:
            cpu["name"] = out.strip()
    elif sys.platform.startswith("linux"):
        name = _run(["sh", "-c", "grep -m1 'model name' /proc/cpuinfo | sed 's/.*: //'"])
        if name:
            cpu["name"] = name.strip()
        cores = _run(["sh", "-c", "grep -c '^processor' /proc/cpuinfo"])
        if cores.isdigit():
            cpu["threads"] = int(cores)
    return cpu


def detect_gpu() -> List[Dict[str, Any]]:
    gpus: List[Dict[str, Any]] = []
    if sys.platform.startswith("win"):
        out = _run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_VideoController | "
                    "Select-Object Name,AdapterCompatibility,DriverVersion,DriverDate,VideoProcessor | "
                    "Format-List"])
        blocks = re.split(r"\n\s*\n", out)
        for block in blocks:
            name = re.search(r"Name\s*:\s*(.*)", block)
            if not name:
                continue
            gpu = {
                "name": name.group(1).strip(),
                "vendor": (re.search(r"AdapterCompatibility\s*:\s*(.*)", block).group(1).strip()
                           if re.search(r"AdapterCompatibility\s*:\s*(.*)", block) else ""),
                "driver_version": (re.search(r"DriverVersion\s*:\s*(.*)", block).group(1).strip()
                                   if re.search(r"DriverVersion\s*:\s*(.*)", block) else ""),
                "driver_date": (re.search(r"DriverDate\s*:\s*(.*)", block).group(1).strip()
                                if re.search(r"DriverDate\s*:\s*(.*)", block) else ""),
            }
            gpus.append(gpu)
    elif sys.platform.startswith("linux"):
        out = _run(["lspci", "-nn", "-D"])
        for line in out.splitlines():
            low = line.lower()
            if "vga" in low or "3d controller" in low or "display controller" in low:
                gpus.append({
                    "name": re.sub(r"\[[0-9a-f]{4}:[0-9a-f]{4}\]", "", line).strip(),
                    "pci_id": line.split()[0] if line else "",
                    "vendor": "Unknown", "driver_version": "", "driver_date": "",
                })
        glx = _run(["glxinfo", "-B"])
        m = re.search(r"OpenGL renderer string:\s*(.*)", glx)
        if m and not gpus:
            gpus.append({"name": m.group(1).strip(), "vendor": "", "driver_version": "", "driver_date": ""})
    elif sys.platform.startswith("darwin"):
        out = _run(["system_profiler", "SPDisplaysDataType"])
        for line in out.splitlines():
            if "Chipset Model" in line:
                gpus.append({"name": line.split(":", 1)[1].strip(), "vendor": "Apple",
                             "driver_version": "", "driver_date": ""})
    return gpus


def detect_disks() -> List[Dict[str, Any]]:
    disks: List[Dict[str, Any]] = []
    if _HAS_PSUTIL:
        try:
            for p in psutil.disk_partitions():
                try:
                    u = psutil.disk_usage(p.mountpoint)
                except Exception:
                    u = None
                disks.append({
                    "mount": p.mountpoint, "fstype": p.fstype, "device": p.device,
                    "total": u.total if u else 0, "used": u.used if u else 0,
                })
            return disks
        except Exception:
            pass
    if sys.platform.startswith("win"):
        out = _run(["wmic", "logicaldisk", "get", "DeviceID,Size,FileSystem", "/format:csv"])
        for line in out.splitlines()[1:]:
            parts = [x.strip() for x in line.split(",") if x.strip()]
            if len(parts) >= 3:
                disks.append({"mount": parts[1], "fstype": parts[2],
                              "device": parts[1], "total": _safe_int(parts[-1]), "used": 0})
    return disks


def _safe_int(v: Any) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def detect_network() -> List[Dict[str, Any]]:
    nics: List[Dict[str, Any]] = []
    try:
        if _has_psutil():
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            for name, st in stats.items():
                ip = ""
                for a in addrs.get(name, []):
                    if a.family.name == "AF_INET":
                        ip = a.address
                nics.append({"name": name, "up": bool(st.isup), "speed_mbps": st.speed,
                             "mac": "", "ip": ip})
    except Exception:
        pass
    if sys.platform.startswith("win"):
        out = _run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_NetworkAdapter | Where-Object {$_.PhysicalAdapter -eq $true} | "
                    "Select-Object Name,MACAddress,NetEnabled,Speed | Format-List"])
        blocks = re.split(r"\n\s*\n", out)
        for block in blocks:
            m = re.search(r"Name\s*:\s*(.*)", block)
            if m:
                nics.append({
                    "name": m.group(1).strip(),
                    "mac": (re.search(r"MACAddress\s*:\s*(.*)", block).group(1).strip()
                            if re.search(r"MACAddress\s*:\s*(.*)", block) else ""),
                    "up": (re.search(r"NetEnabled\s*:\s*(\w+)", block).group(1) == "True"
                           if re.search(r"NetEnabled\s*:\s*(\w+)", block) else None),
                    "speed_mbps": (re.search(r"Speed\s*:\s*(\d+)", block).group(1)
                                   if re.search(r"Speed\s*:\s*(\d+)", block) else 0),
                    "ip": "",
                })
    return nics


def _has_psutil() -> bool:
    return _HAS_PSUTIL


def detect_sensors() -> Dict[str, Any]:
    sensors: Dict[str, Any] = {}
    try:
        if _HAS_PSUTIL:
            temps = psutil.sensors_temperatures()
            for key, entries in temps.items():
                for e in entries:
                    sensors.setdefault("temperatures", {})[key] = round(e.current, 1)
            fans = psutil.sensors_fans()
            for key, entries in (fans or {}).items():
                for e in entries:
                    sensors.setdefault("fans", {})[key] = e.current
            if hasattr(psutil, "sensors_battery"):
                b = psutil.sensors_battery()
                if b:
                    sensors["battery"] = {"percent": round(b.percent, 1), "plugged": bool(b.power_plugged)}
    except Exception:
        pass
    return sensors


def detect_all() -> Dict[str, Any]:
    """Inventário completo em um único dicionário."""
    return {
        "os": detect_os(),
        "device_class": detect_device_class(),
        "cpu": detect_cpu(),
        "gpu": detect_gpu(),
        "ram": detect_ram(),
        "disks": detect_disks(),
        "network": detect_network(),
        "sensors": detect_sensors(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def uptime_seconds() -> int:
    try:
        if _HAS_PSUTIL:
            return int(psutil.boot_time() and (int(__import__("time").time()) - psutil.boot_time()))
    except Exception:
        pass
    if os.path.exists("/proc/uptime"):
        try:
            return int(float(open("/proc/uptime").read().split()[0]))
        except Exception:
            pass
    return 0