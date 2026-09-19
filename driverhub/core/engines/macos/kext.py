# -*- coding: utf-8 -*-
"""Kernel Extensions (KEXTs) no macOS: kextstat + consultas de versão.

Fornece ``kextstat()`` (tabela), ``kext_version()`` (via ``kextstat -l -b
<id>``) e uma tabela de KEXTs da Apple ligadas a drivers de hardware
(gpu, audio, rede, storage). Nunca lança exceção.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Dict, List

#: KEXTs da Apple associadas a hardware (id -> categoria).
APPLE_KEXT_TABLE: Dict[str, str] = {
    "com.apple.driver.AppleIntelKBLGraphics": "GPU (Intel Gen9+)",
    "com.apple.driver.AppleIntelSKLGraphics": "GPU (Intel Skylake)",
    "com.apple.driver.AppleIntelBDWGraphics": "GPU (Intel Broadwell)",
    "com.apple.driver.AppleIntelCFLGraphics": "GPU (Intel Coffee Lake)",
    "com.apple.driver.AGPXVDisplayHWLib": "GPU (AMD)",
    "com.apple.nvidia.web.NVDAGF100Hal": "GPU (NVIDIA Web)",
    "com.apple.driver.AppleMCCSControl": "GPU/monitor",
    "com.apple.driver.AppleTopCaseHIDEventDriver": "Teclado/touchpad",
    "com.apple.driver.AppleUSBHostTPCController": "USB Thunderbolt",
    "com.apple.driver.AppleThunderboltPCIUpAdapter": "Thunderbolt/PCIe",
    "com.apple.driver.Apple16X50Serial": "Serial",
    "com.apple.driver.AudioHigh": "Áudio (HDMI/DisplayPort)",
    "com.apple.driver.AudioAUUC": "Áudio (DP/HDMI controller)",
    "com.apple.driver.AppleHDA": "Áudio (codec)",
    "com.apple.driver.AppleSmartBatteryManager": "Bateria",
    "com.apple.driver.AppleAHCIPort": "Storage (SATA AHCI)",
    "com.apple.iokit.IOAHCIBlockStorage": "Storage (AHCI)",
    "com.apple.iokit.IOStorageFamily": "Storage (framework)",
    "com.apple.driver.AppleUSBXHCI": "USB 3.x",
    "com.apple.driver.usb.AppleUSBHostCompositeDevice": "USB (composite)",
    "com.apple.iokit.IOUSBHostFamily": "USB (framework)",
    "com.apple.driver.AppleBCMWLANCore": "Rede/Wi-Fi (Broadcom)",
    "com.apple.driver.AirPort.Brcm4360": "Rede/Wi-Fi (Broadcom 4360)",
    "com.apple.driver.AppleIntelI210Ethernet": "Rede (Intel I210)",
    "com.apple.iokit.IONVMeFamily": "Storage (NVMe)",
}


def _run(args: List[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, timeout=timeout, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              errors="replace")
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def kextstat() -> List[Dict[str, Any]]:
    """Lista KEXTs carregadas (``kextstat``) como lista de dicts."""
    if not shutil.which("kextstat"):
        return []
    out = _run(["kextstat"], timeout=30)
    kexts: List[Dict[str, Any]] = []
    for line in (out or "").splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        index, reffs, addr, size, version = parts[0], parts[1], parts[2], parts[3], parts[4]
        bundle_id = (parts[5:] and parts[5]) or ""
        short_name = " ".join(parts[6:])
        kexts.append({
            "index": index, "refs": reffs, "address": addr,
            "size": size, "kext_version": version,
            "bundle_id": bundle_id, "name": short_name,
            "category": APPLE_KEXT_TABLE.get(bundle_id, ""),
            "source": "macos:kextstat",
        })
    return kexts


def kext_version(bundle_id: str) -> Dict[str, Any]:
    """Versão de uma KEXT específica (``kextstat -l -b <bundle_id>``)."""
    if not bundle_id:
        return {"ok": False, "bundle_id": "", "version": "",
                "detail": "bundle_id vazio."}
    if not shutil.which("kextstat"):
        return {"ok": False, "bundle_id": bundle_id, "version": "",
                "detail": "kextstat não encontrado."}
    out = _run(["kextstat", "-l", "-b", bundle_id], timeout=30)
    version = ""
    for line in (out or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 5:
            version = parts[4]
            break
    return {"ok": bool(version), "bundle_id": bundle_id, "version": version,
            "category": APPLE_KEXT_TABLE.get(bundle_id, ""),
            "detail": f"{bundle_id} {version}." if version else
                      "KEXT não carregada."}


def third_party_kexts() -> List[Dict[str, Any]]:
    """Subconjunto de KEXTs que não são da Apple (hipotético 3rd-party).

    Recebem acesso primordial na configuração do macOS (Proteção de
    Integridade do Sistema). Requer análise de assinatura que aqui é feita
    apenas por heurística de bundle_id.
    """
    return [k for k in kextstat()
            if k.get("bundle_id") and not k["bundle_id"].startswith("com.apple.")]


def find_kext(regex: str = "") -> List[Dict[str, Any]]:
    """Procura KEXTs por expressão regular no bundle_id/nome ("" = todas)."""
    if not regex:
        return kextstat()
    try:
        pattern = re.compile(regex, re.IGNORECASE)
    except re.error:
        return []
    return [k for k in kextstat()
            if pattern.search(k.get("bundle_id", "") or k.get("name", ""))]