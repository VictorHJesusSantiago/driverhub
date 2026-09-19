# -*- coding: utf-8 -*-
"""Parsing de ``lsmod`` e tabela de referência módulo -> hardware.

Inclui :func:`parse_lsmod` (que aceita saída textual), :func:`loaded_modules`
e uma tabela real de módulos comuns mapeados para o hardware/uso que
representam (usada como referência pelo DriverHub).
"""
from __future__ import annotations

from typing import Any, Dict, List

#: Tabela de referência: módulos comuns de hardware/drivers no Linux.
REFERENCE_MODULES: Dict[str, Dict[str, str]] = {
    "nvidia": {"hardware": "GPU NVIDIA (proprietário)", "vendor": "NVIDIA"},
    "nouveau": {"hardware": "GPU NVIDIA (livre)", "vendor": "NVIDIA"},
    "amdgpu": {"hardware": "GPU/APU AMD", "vendor": "AMD"},
    "radeon": {"hardware": "GPU AMD antiga", "vendor": "AMD"},
    "i915": {"hardware": "GPU Intel integrada", "vendor": "Intel"},
    "i965": {"hardware": "GPU Intel (antiga)", "vendor": "Intel"},
    "e1000e": {"hardware": "Ethernet Intel", "vendor": "Intel"},
    "igb": {"hardware": "Ethernet Intel Gigabit", "vendor": "Intel"},
    "r8169": {"hardware": "Ethernet Realtek", "vendor": "Realtek"},
    "r8125": {"hardware": "Ethernet Realtek 2.5G", "vendor": "Realtek"},
    "rthwifi": {"hardware": "Wi-Fi Realtek", "vendor": "Realtek"},
    "rtl8821ce": {"hardware": "Wi-Fi Realtek 8821CE", "vendor": "Realtek"},
    "8812au": {"hardware": "Wi-Fi Realtek 8812AU", "vendor": "Realtek"},
    "iwlwifi": {"hardware": "Wi-Fi Intel", "vendor": "Intel"},
    "ath9k": {"hardware": "Wi-Fi Atheros", "vendor": "Qualcomm Atheros"},
    "ath10k_pci": {"hardware": "Wi-Fi Qualcomm", "vendor": "Qualcomm"},
    "mt76": {"hardware": "Wi-Fi MediaTek", "vendor": "MediaTek"},
    "btusb": {"hardware": "Bluetooth USB", "vendor": "Broadcom/Intel"},
    "xhci_hcd": {"hardware": "Controlador USB 3.0", "vendor": "Genérico"},
    "ehci_hcd": {"hardware": "Controlador USB 2.0", "vendor": "Genérico"},
    "nvme": {"hardware": "Armazenamento NVMe", "vendor": "Genérico"},
    "ahci": {"hardware": "Controlador SATA AHCI", "vendor": "Genérico"},
    "snd_hda_intel": {"hardware": "Áudio HD Intel", "vendor": "Intel"},
    "snd_hda_codec_realtek": {"hardware": "Codec de áudio Realtek", "vendor": "Realtek"},
    "v4l2loopback": {"hardware": "Dispositivo de vídeo virtual", "vendor": "Software"},
    "zfs": {"hardware": "Sistema de arquivos ZFS", "vendor": "OpenZFS"},
    "wireguard": {"hardware": "VPN WireGuard", "vendor": "Software"},
    "kvm_intel": {"hardware": "Virtualização KVM Intel", "vendor": "Intel"},
    "kvm_amd": {"hardware": "Virtualização KVM AMD", "vendor": "AMD"},
}


def parse_lsmod(output: str) -> List[Dict[str, Any]]:
    """Converte a saída textual do ``lsmod`` em lista de dicts.

    Formato esperado: ``colunas [Module, Size, Used by]`` no topo e linhas
    ``nome tamanho refs dependencias`` abaixo.
    """
    rows: List[Dict[str, Any]] = []
    output = (output or "").strip()
    if not output:
        return rows
    lines = output.splitlines()
    start = 1 if lines and lines[0].lower().startswith("module") else 0
    for line in lines[start:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[0]
        used_by = parts[-1].rstrip(",") if len(parts) > 3 else ""
        rows.append({
            "id": name, "name": name,
            "size": parts[1], "refs": parts[2] if len(parts) > 2 else "0",
            "used_by": used_by,
            "hardware": (REFERENCE_MODULES.get(name, {}) or {}).get("hardware", ""),
            "vendor": (REFERENCE_MODULES.get(name, {}) or {}).get("vendor", ""),
            "status": "loaded",
            "source": "linux:lsmod",
        })
    return rows


def loaded_modules() -> List[str]:
    """Nomes dos módulos carregados atualmente (via /proc/modules)."""
    names: List[str] = []
    try:
        with open("/proc/modules", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if parts:
                    names.append(parts[0])
    except Exception:
        pass
    return names


def module_hardware(module: str) -> Dict[str, str]:
    """Retorna hardware/vendor de referência para um módulo."""
    return dict(REFERENCE_MODULES.get(module, {"hardware": "", "vendor": ""}))


def known_modules() -> List[str]:
    """Lista os módulos presentes na tabela de referência."""
    return sorted(REFERENCE_MODULES)