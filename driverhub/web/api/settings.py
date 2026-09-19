# -*- coding: utf-8 -*-
"""Rotas de configurações da API: leitura, escrita pontual e reset.

A serialização é segura: só tipos básicos (str/int/float/bool/None) são aceitos
e há um teto de 50 chaves para evitar crescimento descontrolado.
"""
from __future__ import annotations

MAX_SETTINGS_KEYS = 50
_META_KEY = "web_settings"
_BASIC = (str, int, float, bool, type(None))


def _sanitize_value(value):
    if isinstance(value, _BASIC):
        return value
    raise ValueError("tipo não permitido em configuração (aceito: texto, número, booleano)")


def get_settings(store):
    """Lê as configurações da API persistidas no banco (meta)."""
    try:
        data = store.get_meta(_META_KEY, default={})
        if not isinstance(data, dict):
            data = {}
        return {"settings": data, "total": len(data), "max_keys": MAX_SETTINGS_KEYS}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao ler configurações: {exc}"}


def set_setting(key, value, store=None):
    """Salva uma configuração pontual (só tipos básicos, máx. 50 chaves)."""
    try:
        if not isinstance(key, str) or not str(key).strip():
            return {"error": "chave inválida"}
        key = str(key).strip()[:64]
        try:
            _sanitize_value(value)
        except ValueError as exc:
            return {"error": str(exc)}
        data = dict(store.get_meta(_META_KEY, default={}) or {})
        if key not in data and len(data) >= MAX_SETTINGS_KEYS:
            return {"error": f"limite de {MAX_SETTINGS_KEYS} configurações atingido"}
        data[key] = value
        store.set_meta(_META_KEY, data)
        return {"ok": True, "key": key, "value": value}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao salvar configuração: {exc}"}


def reset_settings(store):
    """Restaura as configurações da API para o estado padrão (vazio)."""
    try:
        store.set_meta(_META_KEY, {})
        return {"ok": True, "detail": "Configurações da API restauradas para o padrão."}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao restaurar configurações: {exc}"}