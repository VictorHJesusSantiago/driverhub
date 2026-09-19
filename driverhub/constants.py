# -*- coding: utf-8 -*-
"""Constantes globais do DriverHub (versão, caminhos, URLs oficiais, limites)."""
from __future__ import annotations

import os

APP_NAME = "DriverHub"
APP_SLUG = "driverhub"
APP_VERSION = "0.9.0"
APP_AUTHOR = "DriverHub contributors"
APP_URL = "https://github.com/anomalyco/driverhub"
APP_LICENSE = "MIT"

DEFAULT_WEB_PORT = 8000
DEFAULT_WEB_HOST = "0.0.0.0"
DEFAULT_SCAN_TIMEOUT = 180
DEFAULT_CATALOG_MANIFEST = (
    "https://raw.githubusercontent.com/anomalyco/driverhub-catalog/main/catalog.json"
)

MAX_CATALOG_RESULTS = 500
MAX_DEVICE_LOG = 10000
MAX_HISTORY_KEEP = 10000

DOWNLOAD_CHUNK = 65536
DOWNLOAD_MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2 GiB
DOWNLOAD_TIMEOUT = 120

AUTO_SCAN_INTERVAL_HOURS = 24
AUTO_SCAN_ENABLED_DEFAULT = True

BACKUP_DIR_NAME = "driverhub-backups"
CONFIG_DIR_NAME = "driverhub"
LOG_FILE_NAME = "driverhub.log"


def user_home() -> str:
    return os.path.expanduser("~")


def config_dir() -> str:
    base = os.environ.get("DRIVERHUB_HOME")
    if base:
        return os.path.join(base, CONFIG_DIR_NAME)
    return os.path.join(user_home(), "." + CONFIG_DIR_NAME)


def backups_dir() -> str:
    return os.path.join(config_dir(), BACKUP_DIR_NAME)


def log_file() -> str:
    return os.path.join(config_dir(), LOG_FILE_NAME)


OFFICIAL_HOSTS = (
    "nvidia", "amd.com", "intel.com", "realtek.com", "broadcom.com",
    "qualcomm.com", "mediatek.com", "renesas.com", "genesyslogic.com.tw",
    "via-labs.com", "asmedia.com.tw", "synaptics.com", "emc.com.tw",
    "logitech.com", "creative.com", "semiconductor.samsung.com",
    "seagate.com", "crucial.com", "support-en.wd.com", "hp.com",
    "canon.com", "epson.com", "brother.com", "support.apple.com",
    "developer.android.com", "catalog.update.microsoft.com",
    "support.microsoft.com", "lenovo.com", "dell.com", "asus.com",
    "msi.com", "gigabyte.com", "acer.com", "samsung.com",
    "killernetworking.com", "ti.com", "monster.com", "razer.com",
    "steelseries.com", "corsair.com", "sony.com", "motorola.com",
    "xiaomi.com", "huawei.com", "qualcomm.com",
)

DEVICE_KINDS = (
    "cpu", "gpu", "audio", "network", "storage", "usb", "input",
    "camera", "printer", "power", "chipset", "pci", "bluetooth",
    "sensors", "bios", "fingerprint", "other",
)

DRIVER_STATUSES = ("installed", "loaded", "published", "problem", "outdated",
                   "pending", "error", "ok")

LANGUAGES = ("pt-BR", "en-US")

THEMES = ("dark", "light", "highcontrast")

EVENT_SCAN = "scan"
EVENT_DRIVER_INSTALL = "driver.install"
EVENT_DRIVER_REMOVE = "driver.remove"
EVENT_DRIVER_UPDATE = "driver.update"
EVENT_CATALOG_UPDATE = "catalog.update"
EVENT_BACKUP = "backup"
EVENT_RESTORE = "restore"
EVENT_CHECK = "check"
EVENT_APP_START = "app.start"
EVENT_APP_STOP = "app.stop"