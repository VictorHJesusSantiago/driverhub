# -*- coding: utf-8 -*-
"""Sondas kextstat (macOS): extensões de kernel carregadas.

Parsing das colunas ``Index Refs Address Size Wired Name (Version) UUID``.
Inclui uma tabela das kexts Apple mais comuns para auxílio na descrição.
"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, List

from .base import Probe, Result, register, run_command

APPLE_KEXTS: Dict[str, str] = {
    "com.apple.iokit.IO80211Family": "Wi-Fi (AirPort)",
    "com.apple.iokit.IONetworkingFamily": "Rede",
    "com.apple.iokit.IOBluetoothFamily": "Bluetooth",
    "com.apple.iokit.IOBluetoothHostControllerUSBTransport": "Bluetooth USB",
    "com.apple.iokit.IOUSBHostFamily": "USB",
    "com.apple.iokit.IONVMeFamily": "NVMe",
    "com.apple.iokit.IOAHCIBlockStorage": "Discos SATA/AHCI",
    "com.apple.iokit.IOGraphicsFamily": "Gráficos",
    "com.apple.driver.AppleIntelKBLGraphics": "Gráficos Intel KBL",
    "com.apple.driver.AppleIntelICLGraphics": "Gráficos Intel ICL",
    "com.apple.driver.AppleIntelTGLGraphics": "Gráficos Intel TGL",
    "com.apple.kext.AMDRadeonX6000": "Gráficos AMD",
    "com.apple.iokit.IOAudioFamily": "Áudio",
    "com.apple.iokit.IOHIDFamily": "HID",
    "com.apple.security.sandbox": "Sandbox",
    "com.apple.kext.CoreTrust": "Integridade (CoreTrust)",
}


def kextstat_all() -> Dict[str, Any]:
    """Executa ``kextstat`` e devolve a lista de kexts carregadas."""
    if sys.platform not in ("darwin",):
        return {"ok": False, "detail": "kextstat disponível apenas no macOS.",
                "data": []}
    res = run_command(["kextstat"], 30)
    kexts = _parse_kextstat(res["data"])
    return {"ok": bool(kexts), "detail": res["detail"], "data": kexts}


def kext_loaded(name: str) -> Dict[str, Any]:
    """Verifica se uma kext (substring) está carregada."""
    res = kextstat_all()
    needle = (name or "").lower()
    found = None
    for item in res["data"]:
        if needle in (item.get("name") or "").lower():
            found = item
            break
    return {"ok": found is not None,
            "detail": f"Kext carregada: {found.get('name') if found else (name or '?')}",
            "data": found}


def _parse_kextstat(text: str) -> List[Dict[str, Any]]:
    """Interpreta linhas terminadas em ``(Version) UUID``."""
    kexts: List[Dict[str, Any]] = []
    for line in text.splitlines():
        match = re.search(r"\s\(([^()]+)\)\s+([0-9A-Fa-f-]{36})\s*$", line)
        if not match:
            continue
        version, uuid = match.group(1), match.group(2)
        head = line[: match.start()].strip()
        tokens = head.split()
        if len(tokens) < 3:
            continue
        rest = tokens[2:]
        while rest and rest[0].startswith("0x"):
            rest.pop(0)
        name = " ".join(rest)
        kexts.append({
            "index": tokens[0], "refs": tokens[1], "name": name,
            "version": version, "uuid": uuid,
            "kind": APPLE_KEXTS.get(name, ""),
        })
    return kexts


def _run_all_probe() -> Result:
    res = kextstat_all()
    return Result(res["ok"], res["detail"], res["data"], "kextstat.all")


def _run_apple_probe() -> Result:
    res = kextstat_all()
    known = [k for k in res["data"] if k.get("kind")]
    return Result(bool(known), f"{len(known)} kexts Apple conhecidas carregadas",
                  known, "kextstat.apple")


register(Probe("kextstat.all", "Kexts carregadas no macOS",
               _run_all_probe, priority=30))
register(Probe("kextstat.apple", "Kexts Apple conhecidas carregadas",
               _run_apple_probe, priority=70))