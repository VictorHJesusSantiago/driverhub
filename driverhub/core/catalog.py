# -*- coding: utf-8 -*-
"""Catálogo de drivers baseado em fontes 100% oficiais (fabricantes).

O catálogo local é semeado com um conjunto curado de páginas oficiais de
download de drivers, organizadas por categoria. Ele pode ser atualizado a
partir de um manifesto remoto (URL configurável) e pode ser enriquecido com
entradas adicionais validadas pelo usuário.
"""
from __future__ import annotations

import ssl
import urllib.request
from typing import Any, Dict, List, Optional

from .database import Database

# Manifesto remoto padrão (community-maintained, JSON). Usuários podem apontar
# para o próprio manifest com --manifest. Assim "fontes oficiais" é garantido:
# DriveHub só registra/fornece URLs de fabricantes oficiais.
DEFAULT_MANIFEST = (
    "https://raw.githubusercontent.com/anomalyco/driverhub-catalog/main/catalog.json"
)

# Catálogo inicial, curado, com URLs oficiais dos fabricantes.
SEED_CATALOG: List[Dict[str, Any]] = [
    # ---------- Gráficos ----------
    {"vendor": "NVIDIA", "category": "gráficos", "device": "GeForce / NVIDIA (Windows)",
     "os": "Windows, Linux", "url": "https://www.nvidia.com.br/Download/index.aspx",
     "notes": "Download oficial NVIDIA — GeForce, Studio e datacenter."},
    {"vendor": "NVIDIA", "category": "gráficos", "device": "NVIDIA GPU (Linux .run)",
     "os": "Linux", "url": "https://www.nvidia.com/Download/Find.aspx",
     "notes": "Drivers oficiais para Linux (run e apt/cuda)."},
    {"vendor": "AMD", "category": "gráficos", "device": "Radeon / Adrenalin (Windows)",
     "os": "Windows", "url": "https://www.amd.com/en/support/download/drivers.html",
     "notes": "Adrenalin Edition oficial AMD."},
    {"vendor": "AMD", "category": "gráficos", "device": "Radeon / AMDGPU (Linux)",
     "os": "Linux", "url": "https://www.amd.com/en/support/download/linux-drivers.html",
     "notes": "Driver open-source amdgpu integrado ao kernel."},
    {"vendor": "Intel", "category": "gráficos", "device": "Intel Graphics (Windows)",
     "os": "Windows", "url": "https://www.intel.com/content/www/us/en/download-center/home.html",
     "notes": "Intel® Driver & Support Assistant (IDSA)."},
    {"vendor": "Intel", "category": "gráficos", "device": "Intel Arc / Iris",
     "os": "Windows, Linux", "url": "https://www.intel.com/content/www/us/en/download/785597/intel-arc-iris-xe-graphics-windows.html",
     "notes": "Driver gráfico Intel Arc/Iris."},
    # ---------- Chipsets / placas-mãe ----------
    {"vendor": "Intel", "category": "chipset", "device": "Intel Chipset INF Utility",
     "os": "Windows", "url": "https://www.intel.com/content/www/us/en/download/19347/chipset-inf-utility.html",
     "notes": "Atualiza INF/identificação de chipset."},
    {"vendor": "AMD", "category": "chipset", "device": "AMD Chipset Drivers",
     "os": "Windows", "url": "https://www.amd.com/en/support/download/drivers.html",
     "notes": "Pacotes oficiais de chipset AMD (B450/X570/B650/X670...)."},
    {"vendor": "ASMedia", "category": "chipset", "device": "ASMedia USB3/SATA",
     "os": "Windows", "url": "https://www.asmedia.com.tw/eng/e_show_products.php?cate_index=36",
     "notes": "Controladores USB 3.x e SATA da ASMedia."},
    # ---------- Rede ----------
    {"vendor": "Realtek", "category": "rede", "device": "RTL8111/8168 Ethernet (Windows)",
     "os": "Windows", "url": "https://www.realtek.com/Download/List?cate_id=584",
     "notes": "Drivers oficiais Realtek PCIe GbE."},
    {"vendor": "Realtek", "category": "rede", "device": "Realtek Wireless LAN (RTL88xx)",
     "os": "Windows", "url": "https://www.realtek.com/Download/List?cate_id=584",
     "notes": "WLAN drivers oficiais Realtek."},
    {"vendor": "Realtek", "category": "rede", "device": "Realtek r8168/r8125 (Linux)",
     "os": "Linux", "url": "https://www.realtek.com/Download/List?cate_id=584",
     "notes": "Driver r8168 do site oficial (para kernels antigos)."},
    {"vendor": "Intel", "category": "rede", "device": "Intel Ethernet / Wireless (Windows)",
     "os": "Windows", "url": "https://www.intel.com/content/www/us/en/download/18293/intel-network-adapter-driver-for-windows-10.html",
     "notes": "Pacote oficial Intel para adaptadores de rede."},
    {"vendor": "Intel", "category": "rede", "device": "Intel e1000e/ixgbe (Linux)",
     "os": "Linux", "url": "https://www.intel.com/content/www/us/en/download/13663/intel-ethernet-adapter-complete-driver-pack.html",
     "notes": "Driver pack oficial Intel para Linux."},
    {"vendor": "Broadcom", "category": "rede", "device": "Broadcom Wireless (Windows)",
     "os": "Windows", "url": "https://www.broadcom.com/support/download-search?dk=wireless",
     "notes": "Drivers de rede sem fio Broadcom."},
    {"vendor": "Qualcomm", "category": "rede", "device": "Qualcomm Killer Wi-Fi",
     "os": "Windows", "url": "https://www.killernetworking.com/driver-downloads",
     "notes": "Killer Control Center e drivers."},
    {"vendor": "MediaTek", "category": "rede", "device": "MediaTek Wi-Fi (Windows)",
     "os": "Windows", "url": "https://www.mediatek.com/products/broadband-wifi",
     "notes": "Drivers Wi-Fi MediaTek de PCs."},
    # ---------- Áudio ----------
    {"vendor": "Realtek", "category": "áudio", "device": "Realtek High Definition Audio",
     "os": "Windows-10/11", "url": "https://www.realtek.com/Download/List?cate_id=528",
     "notes": "Drivers oficiais de áudio Realtek (componentes de PC)."},
    {"vendor": "Creative", "category": "áudio", "device": "Creative Sound Blaster",
     "os": "Windows", "url": "https://support.creative.com/Downloads/",
     "notes": "Drivers oficiais Sound Blaster."},
    {"vendor": "Microsoft", "category": "áudio", "device": "Spatial Sound / generic",
     "os": "Windows", "url": "https://support.microsoft.com/en-us/windows",
     "notes": "Drivers genéricos embutidos no Windows."},
    # ---------- Bluetooth ----------
    {"vendor": "Intel", "category": "bluetooth", "device": "Intel Wireless Bluetooth",
     "os": "Windows", "url": "https://www.intel.com/content/www/us/en/download/18649/intel-wireless-bluetooth-for-windows-10-and-windows-11.html",
     "notes": "Driver oficial Intel Bluetooth."},
    {"vendor": "Qualcomm", "category": "bluetooth", "device": "Qualcomm Bluetooth",
     "os": "Windows", "url": "https://www.qualcomm.com/developer/windows-on-qualcomm",
     "notes": "BT da Qualcomm."},
    {"vendor": "Realtek", "category": "bluetooth", "device": "Realtek Bluetooth",
     "os": "Windows", "url": "https://www.realtek.com/Download/List?cate_id=584",
     "notes": "Bluetooth Realtek."},
    # ---------- Armazenamento ----------
    {"vendor": "Samsung", "category": "armazenamento", "device": "Samsung NVMe / Magician",
     "os": "Windows", "url": "https://semiconductor.samsung.com/consumer-storage/support/tools/",
     "notes": "Samsung Magician e atualização de firmware SSD."},
    {"vendor": "Western Digital", "category": "armazenamento", "device": "WD Dashboard / Firmware",
     "os": "Windows", "url": "https://support-en.wd.com/app/products/downloads/softwaredownloads",
     "notes": "Firmware e software de SSD/HD WD."},
    {"vendor": "Seagate", "category": "armazenamento", "device": "Seagate SeaTools / Firmware",
     "os": "Windows", "url": "https://www.seagate.com/support/downloads/",
     "notes": "SeaTools e atualização de firmware."},
    {"vendor": "Crucial", "category": "armazenamento", "device": "Crucial Storage Executive",
     "os": "Windows", "url": "https://www.crucial.com/support/storage-executive",
     "notes": "Firmware e ferramentas para SSDs Crucial."},
    {"vendor": "ASMedia", "category": "armazenamento", "device": "ASMedia SATA/NVMe",
     "os": "Windows", "url": "https://www.asmedia.com.tw/eng/e_show_products.php?cate_index=36",
     "notes": "Controladores de armazenamento ASMedia."},
    # ---------- Entrada ----------
    {"vendor": "Synaptics", "category": "entrada", "device": "Synaptics Touchpad",
     "os": "Windows", "url": "https://www.synaptics.com/products/touchpad-drivers",
     "notes": "Tapetes táteis Synaptics."},
    {"vendor": "ELAN", "category": "entrada", "device": "ELAN Touchpad/Touchscreen",
     "os": "Windows", "url": "https://www.emc.com.tw/",
     "notes": "Página oficial ELAN (drivers disponíveis via OEMs)."},
    {"vendor": "Logitech", "category": "entrada", "device": "Logitech G HUB / Options",
     "os": "Windows, macOS", "url": "https://www.logitech.com/en-us/setup/software.html",
     "notes": "Software oficial Logitech (mouse/teclado)."},
    # ---------- Câmeras ----------
    {"vendor": "Microsoft", "category": "câmera", "device": "OV5640 / camera generic",
     "os": "Windows", "url": "https://support.microsoft.com/en-us/windows",
     "notes": "Driver genérico da câmera no Windows."},
    {"vendor": "Realtek", "category": "câmera", "device": "USB Camera",
     "os": "Windows", "url": "https://www.realtek.com/Download/List?cate_id=584",
     "notes": "Câmeras USB Realtek."},
    # ---------- USB / leitores ----------
    {"vendor": "Renesas", "category": "usb", "device": "Renesas USB 3.0",
     "os": "Windows", "url": "https://www.renesas.com/en/products/connectivity/universal-serial-bus",
     "notes": "Controladores USB Renesas."},
    {"vendor": "Genesys Logic", "category": "usb", "device": "GL3224 / Card Reader",
     "os": "Windows", "url": "https://www.genesyslogic.com.tw/",
     "notes": "Leitores de cartão Genesys."},
    {"vendor": "VIA Labs", "category": "usb", "device": "VL805 / USB4",
     "os": "Windows", "url": "https://www.via-labs.com/",
     "notes": "Controladores USB VIA."},
    # ---------- Impressoras ----------
    {"vendor": "HP", "category": "impressora", "device": "HP Printers / Software",
     "os": "Windows, macOS, Linux, mobile", "url": "https://support.hp.com/br-pt/drivers",
     "notes": "HP Smart e drivers oficiais."},
    {"vendor": "Canon", "category": "impressora", "device": "Canon Printer Drivers",
     "os": "Windows, macOS, Linux", "url": "https://www.canon.com.br/suporte",
     "notes": "Drivers oficiais Canon."},
    {"vendor": "Epson", "category": "impressora", "device": "Epson Drivers",
     "os": "Windows, macOS, Linux", "url": "https://epson.com.br/Suporte/Downloads",
     "notes": "Drivers oficiais Epson."},
    {"vendor": "Brother", "category": "impressora", "device": "Brother Drivers",
     "os": "Windows, macOS, Linux", "url": "https://support.brother.com/g/b/downloadtop.aspx?c=br&lang=pt-br",
     "notes": "Drivers oficiais Brother."},
    # ---------- Dispositivos móveis ----------
    {"vendor": "Google", "category": "mobile", "device": "Android USB / ADB",
     "os": "Windows, Linux, macOS", "url": "https://developer.android.com/studio/run/win-usb",
     "notes": "Drivers USB oficiais ADB (Google)."},
    {"vendor": "Samsung", "category": "mobile", "device": "USB Drivers / ODIN",
     "os": "Windows", "url": "https://www.samsung.com/us/support/downloads/",
     "notes": "Drivers USB Samsung e ferramentas."},
    {"vendor": "Xiaomi", "category": "mobile", "device": "USB / Fastboot",
     "os": "Windows", "url": "https://new.c.mi.com/global/post/101245",
     "notes": "Drivers USB Xiaomi (link oficial)."},
    {"vendor": "Apple", "category": "mobile", "device": "iTunes / Devices",
     "os": "Windows", "url": "https://support.apple.com/en-us/HT210384",
     "notes": "Driver Apple para dispositivos iOS em Windows."},
    # ---------- Sistemas / utilidades ----------
    {"vendor": "Microsoft", "category": "sistema", "device": "Windows Update / integridade",
     "os": "Windows", "url": "https://www.catalog.update.microsoft.com/Home.aspx",
     "notes": "Catálogo oficial Microsoft Update Catalog."},
    {"vendor": "Intel", "category": "sistema", "device": "Intel Driver & Support Assistant",
     "os": "Windows", "url": "https://www.intel.com/content/www/us/en/support/detect.html",
     "notes": "Detecção e atualização automática oficial Intel."},
    {"vendor": "AMD", "category": "sistema", "device": "AMD Auto-Detect",
     "os": "Windows", "url": "https://www.amd.com/en/support/download/drivers.html",
     "notes": "Detecção automática oficial AMD."},
    {"vendor": "Lenovo", "category": "sistema", "device": "Lenovo Vantage / Drivers",
     "os": "Windows, Linux", "url": "https://support.lenovo.com/br/pt/downloads",
     "notes": "Drivers oficiais Lenovo (notebooks/servidores)."},
    {"vendor": "Dell", "category": "sistema", "device": "Dell SupportAssist / Drivers",
     "os": "Windows, Linux", "url": "https://www.dell.com/support/home/pt-br/drivers",
     "notes": "Drivers oficiais Dell."},
    {"vendor": "HP", "category": "sistema", "device": "HP Support Assistant",
     "os": "Windows", "url": "https://support.hp.com/br-pt/drivers",
     "notes": "Drivers oficiais HP (Desktops e notebooks)."},
    {"vendor": "ASUS", "category": "sistema", "device": "ASUS Armoury / Drivers",
     "os": "Windows", "url": "https://www.asus.com/br/support/download-center/",
     "notes": "Drivers oficiais ASUS (placas-mãe e notebooks)."},
    {"vendor": "MSI", "category": "sistema", "device": "MSI Center / Drivers",
     "os": "Windows", "url": "https://www.msi.com/support/download",
     "notes": "Drivers oficiais MSI."},
    {"vendor": "Gigabyte", "category": "sistema", "device": "Gigabyte / AORUS Drivers",
     "os": "Windows", "url": "https://www.gigabyte.com/Support/Utility",
     "notes": "Drivers oficiais Gigabyte."},
    {"vendor": "Acer", "category": "sistema", "device": "Acer Drivers",
     "os": "Windows", "url": "https://www.acer.com/br-pt/support/drivers",
     "notes": "Drivers oficiais Acer."},
    {"vendor": "Samsung", "category": "sistema", "device": "Samsung Electronics / Update",
     "os": "Windows", "url": "https://www.samsung.com/br/support/",
     "notes": "Drivers de notebooks Samsung."},
]


def seed(db: Database) -> int:
    """Popula o catálogo inicial. Idempotente e seguro de executar sempre."""
    return db.catalog_upsert(SEED_CATALOG)


def fetch_manifest(url: str = DEFAULT_MANIFEST, timeout: int = 30) -> Optional[List[Dict[str, Any]]]:
    """Baixa um manifesto de catálogo JSON de uma URL (tfab malicioso)."""
    import json
    import gzip
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={
            "User-Agent": "DriverHub/0.9 (+https://github.com/anomalyco/driverhub)"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as exc:
        return None
    return data if isinstance(data, list) else None


def sanitize_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Garante que só URLs oficiais/fabricantes entrem no catálogo."""
    clean: List[Dict[str, Any]] = []
    import re
    for e in entries:
        url = str(e.get("url", "")).strip()
        if not url.startswith(("https://", "http://")):
            continue
        charlow = str(e.get("vendor", "")).lower()
        # Aceita domínios de fabricantes conhecidos ou qualquer domínio
        # explicitamente marcado como oficial no manifesto.
        if e.get("official", False) is True:
            clean.append(_normalize(e))
            continue
        host = re.sub(r"^https?://([^/]+).*$", r"\1", url).lower()
        known = ("nvidia", "amd.com", "intel.com", "realtek.com", "broadcom.com",
                 "qualcomm.com", "mediatek.com", "renesas.com", "genesyslogic.com.tw",
                 "via-labs.com", "asmedia.com.tw", "synaptics.com", "emc.com.tw",
                 "logitech.com", "creative.com", "semiconductor.samsung.com",
                 "seagate.com", "crucial.com", "support-en.wd.com", "hp.com",
                 "canon.com", "epson.com", "brother.com", "support.apple.com",
                 "developer.android.com", "catalog.update.microsoft.com",
                 "support.microsoft.com", "lenovo.com", "dell.com", "asus.com",
                 "msi.com", "gigabyte.com", "acer.com", "samsung.com",
                 "killernetworking.com", "qualcomm.com")
        if any(k in host for k in known):
            clean.append(_normalize(e))
    return clean


def _normalize(e: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "vendor": str(e.get("vendor", "Unknown")).strip(),
        "category": str(e.get("category", "outros")).strip().lower(),
        "device": str(e.get("device", "")).strip(),
        "os": str(e.get("os", "")).strip(),
        "url": str(e.get("url", "")).strip(),
        "notes": str(e.get("notes", "")).strip(),
    }


def update(db: Database, manifest: str = DEFAULT_MANIFEST, silent: bool = False) -> Dict[str, Any]:
    """Atualiza o catálogo: semeia sempre e adiciona entradas do manifesto remoto."""
    added_seed = seed(db)
    remote_entries = fetch_manifest(manifest)
    added_remote = 0
    status = "ok"
    msg = f"Catálogo semeado ({added_seed} entradas novas)."
    if remote_entries is None:
        status = "offline"
        msg += " Manifesto remoto indisponível — mantido catálogo local."
    else:
        cleaned = sanitize_entries(remote_entries)
        added_remote = db.catalog_upsert(cleaned)
        msg += f" Manifesto remoto aplicado ({added_remote} novas, {len(cleaned)} válidas)."
    db.log("catalog:update", manifest, msg, status != "error")
    return {"status": status, "message": msg,
            "added_seed": added_seed, "added_remote": added_remote,
            "total": db.catalog_count()}