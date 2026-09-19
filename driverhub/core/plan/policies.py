# -*- coding: utf-8 -*-
"""Políticas de atualização pré-configuradas.

Cada fábrica retorna uma ``Policy``. ``policy_from_config`` lê as preferências
do usuário (``driverhub.config.Config`` ou dict) e nunca lança exceções.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def default_policy() -> Any:
    """Política padrão: médio, todas as categorias, reinicia se preciso."""
    from .base import Policy
    try:
        return Policy(
            name="default", strict=False, categories=[], dry_run=False,
            reboot=True, priority="medium",
            schedule={"interval_h": 24, "auto": False}, blacklist=[],
        )
    except Exception:
        return Policy()


def quiet_policy() -> Any:
    """Política silenciosa: só planejar, sem reiniciar, prioridade baixa."""
    from .base import Policy
    try:
        return Policy(
            name="quiet", strict=False, categories=[], dry_run=True,
            reboot=False, priority="low",
            schedule={"interval_h": 168, "auto": False, "notify": False}, blacklist=[],
        )
    except Exception:
        return Policy()


def power_policy() -> Any:
    """Política completa: full auto, atualiza tudo sem perguntar."""
    from .base import Policy
    try:
        return Policy(
            name="power", strict=False, categories=[], dry_run=False,
            reboot=True, priority="high",
            schedule={"interval_h": 24, "auto": True, "notify": False}, blacklist=[],
        )
    except Exception:
        return Policy()


def conservative_policy() -> Any:
    """Política conservadora: somente itens críticos de origem oficial."""
    from .base import Policy
    try:
        return Policy(
            name="conservative", strict=True, categories=["critical"],
            dry_run=False, reboot=True, priority="medium",
            schedule={"interval_h": 72, "auto": False, "notify": True},
            blacklist=["beta", "preview", "experimental"],
        )
    except Exception:
        return Policy()


def _resolve(cfg: Any, key: str, default: Any = None) -> Any:
    """Lê ``key`` com suporte a chaves pontuadas (dict ou objeto .get)."""
    try:
        if isinstance(cfg, dict):
            node: Any = cfg
            for part in str(key).split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return default
            return node
        if hasattr(cfg, "get"):
            return cfg.get(key, default)
    except Exception:
        return default
    return default


def _flag(cfg: Any, key: str, default: bool = False) -> bool:
    v = _resolve(cfg, key, default)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on", "sim")
    return bool(v)


def policy_from_config(cfg: Any = None) -> Any:
    """Compõe uma ``Policy`` a partir das configurações do usuário.

    Aceita uma instância de ``Config`` (driverhub.config) ou um dict. Em caso
    de erro, retorna a política padrão — nunca lança.
    """
    try:
        if cfg is None:
            try:
                from ...config import Config
                cfg = Config()
            except Exception:
                cfg = {}
        force = _flag(cfg, "security.force", False)
        allow_unsigned = _flag(cfg, "security.allow_unsigned", False)
        require_confirm = _flag(cfg, "security.require_confirm", True)
        interval_h = float(_resolve(cfg, "scan.interval_hours", 24) or 24)
        channel = str(_resolve(cfg, "updates.channel", "stable") or "stable")
        auto = _flag(cfg, "scan.auto", False)
        blacklist = _resolve(cfg, "security.blacklist", [])
        if not isinstance(blacklist, list):
            blacklist = []
        from .base import Policy
        return Policy(
            name="config",
            strict=not allow_unsigned,
            categories=[],
            dry_run=not force and require_confirm,
            reboot=True,
            priority="high" if force else "medium",
            schedule={"interval_h": interval_h, "auto": bool(auto),
                      "channel": channel},
            blacklist=[str(b) for b in blacklist],
        )
    except Exception:
        return default_policy()