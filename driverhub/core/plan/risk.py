# -*- coding: utf-8 -*-
"""Avaliação de risco de ações de atualização de drivers.

Reduzem o risco: origem oficial, assinatura válida, categoria crítica e modo
simulação (dry_run). ``risk_level``, ``categorize`` e ``explain`` nunca lançam
exceções.
"""
from __future__ import annotations

from typing import Any, Dict

LEVELS = ("low", "medium", "high")


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on", "sim",
                                     "oficial", "official", "assinado", "signed")
    return bool(v)


def _lower(text: Any) -> str:
    try:
        return str(text or "").lower()
    except Exception:
        return ""


def categorize(detail: Any) -> str:
    """Infere a categoria de um detalhe/descrição (dicts, listas aceitas)."""
    try:
        if isinstance(detail, dict):
            text = " ".join(_lower(v) for v in detail.values() if not isinstance(v, (dict, list)))
            text += " " + _lower(detail.get("name")) + " " + _lower(detail.get("kind"))
        elif isinstance(detail, (list, tuple)):
            text = " ".join(_lower(v) for v in detail if not isinstance(v, (dict, list)))
        else:
            text = _lower(detail)
        rules = (
            ("critical", ("crítico", "critico", "critical", "segurança", "security", "urgente", "boot")),
            ("graphics", ("gráfico", "grafico", "gpu", "vídeo", "video", "display",
                          "nvidia", "radeon", "placa de vídeo", " placa de video", "iris", "geforce")),
            ("network", ("rede", "wi-fi", "wifi", "wireless", "ethernet", " lan ", "lan,",
                         "network", "adaptador de rede", "adaptador")),
            ("audio", ("áudio", "audio", "som", "sound", "hd audio", "codec")),
            ("bluetooth", ("bluetooth", "bt wireless")),
            ("storage", ("armazen", "ssd", "nvme", "sata", "storage", "hdd", "raid", "disco")),
            ("usb", ("usb", "universal serial", "hub usb", "controlador usb")),
            ("chipset", ("chipset", "placa-mãe", "placa mae", "motherboard",
                         "firmware", "bios", "uefi")),
            ("input", ("touchpad", "teclado", "mouse", "input", "hid", "keyboard")),
            ("camera", ("câmera", "camera", "webcam", "web cam")),
            ("printer", ("impress", "printer", "scanner")),
            ("mobile", ("android", "adb", "iphone", "ios", "mobile")),
        )
        for cat, terms in rules:
            if any(t in text for t in terms):
                return cat
        return "other"
    except Exception:
        return "other"


def risk_level(action: Any) -> str:
    """Classifica o risco de uma ação como ``low``, ``medium`` ou ``high``.

    Aceita um dict (com chaves ``official``, ``signed``, ``category``,
    ``dry_run``...) ou um ``PlanAction``.
    """
    try:
        from .base import PlanAction
        if isinstance(action, PlanAction):
            d: Dict[str, Any] = {
                "detail": action.detail,
                "target": action.target,
                "category": categorize(action.detail),
                "official": False,
                "signed": False,
                "dry_run": False,
            }
        elif isinstance(action, dict):
            d = action
        else:
            d = {}
        detail = _lower(d.get("detail")) + " " + _lower(d.get("target"))
        cat = _lower(d.get("category"))
        if not cat:
            cat = categorize(d.get("detail") or d.get("target"))
        lowers = 0
        official = (_truthy(d.get("official")) or _truthy(d.get("official_source"))
                    or _truthy(d.get("origin_official")) or _truthy(d.get("is_official")))
        src = _lower(d.get("source"))
        if "oficial" in src or "official" in src:
            official = True
        if official:
            lowers += 1
        signed = (_truthy(d.get("signed")) or _truthy(d.get("is_signed"))
                  or _truthy(d.get("signature")))
        if signed:
            lowers += 1
        if cat == "critical" or "crítico" in detail or "critical" in detail:
            lowers += 1
        if _truthy(d.get("dry_run")):
            lowers += 1
        if lowers >= 2:
            return "low"
        if lowers == 1:
            return "medium"
        return "high"
    except Exception:
        return "medium"


def explain(level: Any) -> str:
    """Explicação em pt-BR para um nível de risco."""
    try:
        lv = _lower(level)
        if lv in ("low", "baixo"):
            return ("Risco baixo: origem oficial, assinatura válida ou modo "
                    "simulação. Pode aplicar com segurança e pouca supervisão.")
        if lv in ("high", "alto"):
            return ("Risco alto: origem não confirmada ou sem assinatura. Revise "
                    "manualmente, confirme o fabricante e faça backup antes de aplicar.")
        return ("Risco médio: aplique com confirmação, verificando origem e "
                "assinatura antes de prosseguir.")
    except Exception:
        return "Risco médio: aplique com confirmação."