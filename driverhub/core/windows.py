# -*- coding: utf-8 -*-
"""Motor de drivers nativo do Windows.

Usa ``pnputil`` (Windows 10/11) e, como fallback, ``wmic``/PowerShell/WMI.
Todas as funções são seguras contra falhas (nunca lançam exceção).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .platform import _run, _full_cmd


def _pnputil(args: str, timeout: int = 60) -> str:
    cmd = _full_cmd("pnputil", args)
    if not cmd:
        return ""
    return _run(cmd, timeout=timeout)


def drivers_list() -> List[Dict[str, Any]]:
    """Lista drivers de terceiros instalados via pnputil."""
    out = _pnputil("/enum-drivers", timeout=120)
    result: List[Dict[str, Any]] = []
    block: Dict[str, Any] = {}
    for raw in out.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Published Name"):
            if block:
                result.append(block)
            block = {"inf_file": line.split(":", 1)[1].strip() if ":" in line else ""}
            continue
        for key in ("Original Name", "Provider Name", "Class Name",
                    "Class Guid", "Driver Version", "Driver Date",
                    "Untrusted Publisher Name"):
            if line.startswith(key):
                block[key.lower().replace(" ", "_")] = line.split(":", 1)[1].strip() if ":" in line else ""
                break
    if block:
        result.append(block)

    # enriquecimento: estado da publicação (publicado no sistema)
    for d in result:
        d.setdefault("status", "published")
        d["id"] = d.get("inf_file") or d.get("original_name", "")
        d["name"] = _pretty_name(d)
        d["provider"] = d.get("provider_name", "")
        v = d.get("driver_version", "")
        date, version = _split_date_version(v)
        d["version"] = version
        d["date"] = date or d.get("date", "")
        d["class"] = d.get("class_name", "")
        d["source"] = "windows:pnputil"
    return result


def _split_date_version(v: str) -> tuple[str, str]:
    """Separa '05/19/2026 15.11.30.14' em (data, versão)."""
    m = re.match(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(.*)$", v.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", v.strip()


def _pretty_name(d: Dict[str, Any]) -> str:
    orig = d.get("original_name", "") or d.get("inf_file", "")
    return orig


def drivers_system() -> List[Dict[str, Any]]:
    """Lista drivers do sistema (driverquery)."""
    out = _run(["driverquery", "/v", "/fo", "csv"], timeout=120)
    rows: List[Dict[str, Any]] = []
    if not out:
        return rows
    lines = out.splitlines()
    if not lines:
        return rows
    header = lines[0].split(",")
    header = [h.strip().strip('"') for h in header]
    for line in lines[1:]:
        parts = _split_csv(line)
        if len(parts) < len(header):
            continue
        d = dict(zip(header, parts))
        d["source"] = "windows:driverquery"
        d["id"] = d.get("Module Name", "") or d.get("Display Name", "")
        d["name"] = d.get("Display Name", "")
        d["version"] = d.get("Link Date", "")
        d["provider"] = d.get("Version", "")
        rows.append(d)
    return rows


def _split_csv(line: str) -> List[str]:
    row: List[str] = []
    cur, quote = "", False
    for ch in line:
        if ch == '"':
            quote = not quote
        elif ch == "," and not quote:
            row.append(cur.strip().strip('"'))
            cur = ""
        else:
            cur += ch
    row.append(cur.strip().strip('"'))
    return row


def devices_pnp() -> List[Dict[str, Any]]:
    """Dispositivos PnP usando PowerShell/WMI (robusto em qualquer Win)."""
    script = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.Name -ne $null } | "
        "Select-Object Name,Manufacturer,DeviceID,Status,ConfigManagerErrorCode | "
        "ConvertTo-Json -Compress"
    )
    out = _run(["powershell", "-NoProfile", "-Command", script], timeout=180)
    items = _parse_json_list(out)
    devices: List[Dict[str, Any]] = []
    for it in items:
        name = it.get("Name") or ""
        if not name.strip():
            continue
        did = it.get("DeviceID") or ""
        status_ok = it.get("Status") == "OK" and it.get("ConfigManagerErrorCode") in (0, None)
        devices.append({
            "kind": _guess_kind(name, did),
            "name": name.strip(),
            "vendor": (it.get("Manufacturer") or "Unknown").strip(),
            "driver_id": did,
            "driver_version": "",
            "status": "ok" if status_ok else "problem",
            "raw": it,
        })
    return devices


def _guess_kind(name: str, did: str) -> str:
    low = name.lower()
    if "video" in low or "display" in low or "graphics" in low or "gpu" in low:
        return "gpu"
    if "processor" in low or "cpu" in low or "apic" in low:
        return "cpu"
    if "audio" in low or "sound" in low or "realtek high definition" in low:
        return "audio"
    if "network" in low or "ethernet" in low or "wi-fi" in low or "wireless" in low or "bluetooth" in low:
        return "network"
    if "disk" in low or "storage" in low or "nvme" in low or "raid" in low or "ahci" in low or "sata" in low:
        return "storage"
    if "usb" in low:
        return "usb"
    if "camera" in low or "webcam" in low:
        return "camera"
    if "mouse" in low or "keyboard" in low or "hud" in low or "input" in low:
        return "input"
    if "chipset" in low or "pci" in low or "smbus" in low or "system" in low:
        return "chipset"
    if "printer" in low or "print" in low:
        return "printer"
    if "battery" in low or "acpi" in low:
        return "power"
    return "other"


def _parse_json_list(out: str) -> List[Dict[str, Any]]:
    import json
    if not out:
        return []
    try:
        data = json.loads(out)
    except Exception:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def devices_audio() -> List[Dict[str, Any]]:
    out = _run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_SoundDevice | Select-Object Name,Manufacturer,Status | ConvertTo-Json -Compress"],
               timeout=90)
    items = _parse_json_list(out)
    return [{"kind": "audio", "name": (i.get("Name") or "").strip(),
             "vendor": (i.get("Manufacturer") or "Unknown").strip(),
             "status": "ok" if i.get("Status") == "OK" else "problem",
             "driver_id": "", "driver_version": ""} for i in items if i.get("Name")]


def driver_details(did: str) -> Dict[str, Any]:
    """Busca detalhes de um driver publicado via pnputil."""
    for d in drivers_list():
        if d.get("id") == did or d.get("inf_file") == did:
            return d
    out = _run(["powershell", "-NoProfile", "-Command",
                f"Get-WindowsDriver -Online | Where-Object {{ $_.OriginalFileName -like '*{did}*' }} | "
                f"Select-Object -First 1 | ConvertTo-Json -Compress"], timeout=180)
    items = _parse_json_list(out)
    if items:
        it = items[0]
        return {
            "id": did, "inf_file": it.get("DriverInfo", ""),
            "name": it.get("DriverInfo", ""), "provider": it.get("ProviderName", ""),
            "version": it.get("DriverVersion", ""), "date": it.get("Date", ""),
            "class": it.get("ClassName", ""), "status": "published",
            "original_name": it.get("OriginalFileName", ""),
        }
    return {"id": did, "name": did, "status": "unknown"}


def scan_devices_and_drivers() -> Dict[str, Any]:
    """Coleta completa: PnP + áudio + drivers publicados."""
    devices = devices_pnp()
    devices.extend(devices_audio())
    drivers = drivers_list()
    return {"devices": devices, "drivers": drivers}


def install_driver_inf(inf_path: str) -> Dict[str, Any]:
    """Instala driver a partir de um arquivo INF (requer admin)."""
    out = _pnputil(f"/add-driver \"{inf_path}\" /install", timeout=180)
    ok = ("successfully" in out.lower() or "instalado" in out.lower()
          or "concluído" in out.lower() or "concluído" in out.lower())
    detail = out.strip() or "Sem saída do pnputil"
    return {"ok": ok, "detail": detail, "output": out}


def remove_driver(did_or_inf: str, force: bool = False) -> Dict[str, Any]:
    """Remove um driver publicado (requer admin)."""
    inf = did_or_inf
    if not inf.lower().endswith(".inf"):
        for d in drivers_list():
            if d.get("id") == did_or_inf:
                inf = d.get("inf_file", did_or_inf)
                break
    out = _pnputil(f"/delete-driver {inf} /uninstall /force" if force else
                   f"/delete-driver {inf} /uninstall", timeout=180)
    ok = ("successfully" in out.lower() or "exclu" in out.lower()
          or "remov" in out.lower() or "conclu" in out.lower())
    return {"ok": ok, "detail": out.strip() or "Sem saída do pnputil", "output": out}


def update_driver_family(family_name: str, inf_path: str) -> Dict[str, Any]:
    """Substitui um driver de mesma família/ID de hardware por uma nova versão."""
    return install_driver_inf(inf_path)


def windows_update_scan() -> List[Dict[str, Any]]:
    """Lista atualizações de driver pendentes no Windows Update (via PS).

    Requer o módulo PSWindowsUpdate; falha graciosa se não estiver disponível.
    """
    out = _run(["powershell", "-NoProfile", "-Command",
                "Get-Module -ListAvailable PSWindowsUpdate | Out-Null; "
                "if ($?) { Get-WindowsUpdate -IsNotInstalled -MicrosoftUpdate | "
                "Select-Object Title,Status,KB | ConvertTo-Json -Compress } else { '' }"],
               timeout=180)
    items = _parse_json_list(out)
    return [{"title": i.get("Title", ""), "status": i.get("Status", ""),
             "kb": i.get("KB", ""), "source": "windows-update"} for i in items]