# -*- coding: utf-8 -*-
"""Sondas Linux via /sys e /proc (apenas leitura de arquivos, sem execução).

Nenhuma função lança exceção: caminhos ausentes retornam listas vazias.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .base import Probe, Result, register


def sysfs_class(class_: str) -> List[str]:
    """Lista os dispositivos presentes em ``/sys/class/<class_>``."""
    path = "/sys/class/" + class_.lstrip("/")
    try:
        return sorted(e for e in os.listdir(path) if not e.startswith("."))
    except OSError:
        return []


def proc_cpuinfo() -> List[Dict[str, Any]]:
    """Lê /proc/cpuinfo e devolve um registro de campos por processador."""
    text = _read("/proc/cpuinfo")
    if not text:
        return []
    cpus: List[Dict[str, Any]] = []
    current: Dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                cpus.append(current)
                current = {}
            continue
        key, _, value = line.partition(":")
        current[key.strip()] = value.strip()
    if current:
        cpus.append(current)
    return cpus


def proc_modules() -> List[Dict[str, str]]:
    """Lê /proc/modules: nome, tamanho, refs, dependências, estado."""
    text = _read("/proc/modules")
    if not text:
        return []
    modules: List[Dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        modules.append({
            "name": parts[0], "size": parts[1], "refcount": parts[2],
            "used_by": parts[3].rstrip(","), "state": parts[4], "path": parts[5],
        })
    return modules


def sys_block() -> List[Dict[str, Any]]:
    """Lê /sys/block: discos com tamanho, modelo e rotação quando presentes."""
    try:
        names = sorted(os.listdir("/sys/block"))
    except OSError:
        return []
    devices: List[Dict[str, Any]] = []
    for name in names:
        base = "/sys/block/" + name
        sectors = _to_int(_read(os.path.join(base, "size")))
        devices.append({
            "name": name,
            "size_sectors": sectors,
            "size_bytes": sectors * 512,
            "model": _read(os.path.join(base, "device", "model")).strip(),
            "rotational": _to_int(_read(os.path.join(base, "queue", "rotational"))),
        })
    return devices


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:  # noqa: BLE001
        return ""


def _to_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except Exception:  # noqa: BLE001
        return 0


def _run_classes_probe() -> Result:
    classes = ("block", "net", "sound", "usb", "input", "drm", "gpio", "hwmon")
    data = {c: sysfs_class(c)[:50] for c in classes}
    return Result(bool(data), "Classes sysfs inspecionadas", data, "sysfs.classes")


def _run_cpuinfo_probe() -> Result:
    cpus = proc_cpuinfo()
    first = cpus[0] if cpus else {}
    detail = (f"{len(cpus)} processador(es): "
              + (first.get("model name") or first.get("Processor") or "desconhecido"))
    return Result(bool(cpus), detail,
                  {"count": len(cpus), "cpuinfo": cpus}, "sysfs.cpuinfo")


def _run_modules_probe() -> Result:
    modules = proc_modules()
    return Result(bool(modules), f"{len(modules)} módulos do kernel",
                  {"count": len(modules), "modules": modules}, "sysfs.modules")


def _run_block_probe() -> Result:
    disks = sys_block()
    return Result(bool(disks), f"{len(disks)} dispositivos de bloco",
                  {"count": len(disks), "disks": disks}, "sysfs.block")


register(Probe("sysfs.cpuinfo", "Processadores via /proc/cpuinfo",
               _run_cpuinfo_probe, priority=25))
register(Probe("sysfs.block", "Discos via /sys/block",
               _run_block_probe, priority=35))
register(Probe("sysfs.classes", "Dispositivos por classe /sys/class",
               _run_classes_probe, priority=65))
register(Probe("sysfs.modules", "Módulos de kernel via /proc/modules",
               _run_modules_probe, priority=55))