# -*- coding: utf-8 -*-
"""Sonda de discos, partições e volumes (Linux e Windows).

Linux: ``/proc/partitions`` + ``lsblk -J`` quando presente.
Windows: ``Get-Disk``/``Get-Partition``/``Get-Volume`` (PowerShell), com
fallback ``wmic diskdrive get``. Nunca lança exceção.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command


def probe_disks() -> Dict[str, Any]:
    """Lista os dispositivos de armazenamento do sistema atual."""
    if sys.platform.startswith("win"):
        disks = windows_disks()
        if not disks:
            disks = wmic_disks()
    elif sys.platform.startswith("linux"):
        disks = linux_disks()
    else:
        disks = []
    return {"ok": bool(disks),
            "detail": f"{len(disks)} dispositivo(s) de armazenamento",
            "data": disks}


def linux_disks() -> List[Dict[str, Any]]:
    """Discos via /proc/partitions, enriquecidos por ``lsblk -J``."""
    disks = _proc_partitions()
    extras = _lsblk_json()
    by_name = {d.get("name"): d for d in extras}
    for disk in disks:
        extra = by_name.get(disk["name"], {})
        disk["model"] = extra.get("model", "")
        disk["serial"] = extra.get("serial", "")
        disk["type"] = extra.get("type", "disk")
        disk["mountpoint"] = extra.get("mountpoint", "")
    return disks


def _proc_partitions() -> List[Dict[str, Any]]:
    try:
        with open("/proc/partitions", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:  # noqa: BLE001
        return []
    disks: List[Dict[str, Any]] = []
    for line in lines:
        parts = line.split()
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        name = parts[3]
        if name.startswith(("loop", "ram", "sr", "zram")):
            continue
        blocks = _to_int(parts[2])
        disks.append({"name": name, "major": parts[0], "minor": parts[1],
                      "blocks": blocks, "size_bytes": blocks * 1024})
    return disks


def _lsblk_json() -> List[Dict[str, Any]]:
    res = run_command(["lsblk", "-J", "-o", "NAME,SIZE,MODEL,SERIAL,TYPE,MOUNTPOINT"], 30)
    if not res["ok"] or not res["data"].strip():
        return []
    try:
        payload = json.loads(res["data"])
        return [d for d in payload.get("blockdevices", []) if isinstance(d, dict)]
    except Exception:  # noqa: BLE001
        return []


def windows_disks() -> List[Dict[str, Any]]:
    """Discos via Get-Disk, com volumes associados via Get-Partition."""
    script = ("Get-Disk | Select-Object Number,FriendlyName,SerialNumber,Size,"
              "PartitionStyle,OperationalStatus | ConvertTo-Json -Compress")
    res = run_command(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                       script], 60)
    disks = _json_payload(res["data"])
    if disks:
        vols = _windows_volumes()
        for disk in disks:
            disk["volumes"] = [v for v in vols
                               if v.get("disk") == disk.get("number")]
    return disks


def _windows_volumes() -> List[Dict[str, Any]]:
    script = (
        "Get-Partition | ForEach-Object { "
        "$v = Get-Volume -Partition $_; "
        "[PSCustomObject]@{ disk=$_.DiskNumber; part=$_.PartitionNumber; "
        "drive=$v.DriveLetter; label=$v.FileSystemLabel; fs=$v.FileSystem; "
        "size=$v.Size; free=$v.SizeRemaining } "
        "} | ConvertTo-Json -Compress")
    res = run_command(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                       script], 60)
    return _json_payload(res["data"])


def wmic_disks() -> List[Dict[str, Any]]:
    """Fallback Windows: `wmic diskdrive get Model,SerialNumber,Size`."""
    res = run_command(["wmic", "diskdrive", "get",
                       "Model,SerialNumber,Size,InterfaceType", "/format:csv"], 30)
    lines = [ln.strip() for ln in res["data"].splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    headers = [h.strip().lower() for h in lines[0].split(",")]
    try:
        index = headers.index("node")
        headers.pop(index)
    except ValueError:
        return []
    disks: List[Dict[str, Any]] = []
    for line in lines[1:]:
        values = line.split(",")
        if len(values) == len(headers) + 1:
            values.pop(index)
        if len(values) != len(headers):
            continue
        row = dict(zip(headers, (v.strip() for v in values)))
        disks.append({"model": row.get("model", ""),
                      "serial": row.get("serialnumber", ""),
                      "size_bytes": _to_int(row.get("size", "")),
                      "interface": row.get("interfacetype", "")})
    return disks


def _json_payload(text: str) -> List[Dict[str, Any]]:
    if not text.strip():
        return []
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _to_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:  # noqa: BLE001
        return 0


def _run_disk_probe() -> Result:
    res = probe_disks()
    return Result(res["ok"], res["detail"], res["data"], "disk.devices")


register(Probe("disk.devices", "Discos, partições e volumes",
               _run_disk_probe, priority=30))