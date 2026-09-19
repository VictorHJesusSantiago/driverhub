# -*- coding: utf-8 -*-
"""Coletor de BIOS/firmware: versão, fabricante e estado de atualização."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Device
from ...tools import compat


def collect(raw: List[Dict[str, Any]], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    if compat.IS_WINDOWS:
        from ...tools import shell
        r = shell.run(["powershell", "-NoProfile", "-Command",
                       "(Get-CimInstance Win32_BIOS) | "
                       "Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | Format-List"],
                      timeout=60)
        mfr = _grep(r.output, "Manufacturer")
        ver = _grep(r.output, "SMBIOSBIOSVersion")
        date = _grep(r.output, "ReleaseDate")
        out.append(Device(
            id="firmware:bios",
            name="BIOS/UEFI",
            vendor=mfr or "",
            kind="bios",
            hwid="",
            status="ok",
            driver=ver or "",
            detail=f"Versão {ver or '—'} · {date or '—'}",
        ).to_dict())
    elif compat.IS_LINUX:
        from ...tools import shell
        r = shell.run(["sh", "-c", "cat /sys/class/dmi/id/bios_vendor 2>/dev/null; "
                                   "cat /sys/class/dmi/id/bios_version 2>/dev/null"],
                      timeout=10)
        lines = r.output.splitlines()
        mfr = lines[0].strip() if lines else ""
        ver = lines[1].strip() if len(lines) > 1 else ""
        out.append(Device(
            id="firmware:bios",
            name="BIOS/UEFI",
            vendor=mfr,
            kind="bios",
            hwid="",
            status="ok",
            driver=ver,
            detail=f"Firmware {ver or '—'}",
        ).to_dict())

    if compat.IS_LINUX:
        from ...tools import shell
        r = shell.run(["fwupdmgr", "--version"], timeout=30)
        if r.ok:
            out.append(Device(
                id="firmware:fwupd",
                name="fwupd (LVFS)",
                vendor="",
                kind="bios",
                hwid="",
                status="ok",
                driver="",
                detail="Service disponível para firmware via LVFS.",
            ).to_dict())
    return out


def _grep(text: str, key: str) -> str:
    for line in text.splitlines():
        if key.lower() in line.lower() and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""