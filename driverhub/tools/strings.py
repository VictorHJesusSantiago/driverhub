# -*- coding: utf-8 -*-
"""Manipulação de strings: trims, diffs, IDs de hardware e normalização."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple


def clean(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def short(s: str, limit: int = 60) -> str:
    s = clean(s)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def normalize_hardware_id(hwid: Optional[str]) -> str:
    """PCI\\VEN_1234&DEV_5678&SUBSYS... -> \VEN_1234&DEV_5678 (limpo)."""
    hw = clean(hwid).upper()
    if not hw:
        return ""
    hw = hw.replace("PCI\\", "").replace("USB\\", "")
    m = re.search(r"VEN_?([0-9A-F]{4})&DEV_?([0-9A-F]{4})", hw)
    if m:
        return f"VEN{m[1]}&DEV{m[2]}"
    m = re.search(r"VID_?([0-9A-F]{4})&PID_?([0-9A-F]{4})", hw)
    if m:
        return f"VID{m[1]}&PID{m[2]}"
    return hw.split("&")[0] if hw else ""


def extract_hex_pairs(hwid: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(r"VEN_?([0-9A-F]{4}).*?DEV_?([0-9A-F]{4})", hwid.upper())
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"VID_?([0-9A-F]{4}).*?PID_?([0-9A-F]{4})", hwid.upper())
    if m:
        return m.group(1), m.group(2)
    return None, None


def hex_label(value: str) -> str:
    try:
        return f"0x{int(value, 16):04X}"
    except Exception:
        return value


def slug(value: str) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def first_lines(text: Optional[str], n: int = 5) -> List[str]:
    return [ln for ln in (text or "").splitlines() if ln.strip()][:n]