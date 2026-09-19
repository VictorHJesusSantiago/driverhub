# -*- coding: utf-8 -*-
"""Configuração do DriverHub (armazenada em JSON no diretório do usuário).

Permite: idioma, tema, agendamento automático, limites de download, URL do
manifesto do catálogo, portas da interface web e preferências de segurança.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

from . import constants as C


def _path() -> str:
    d = C.config_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")


DEFAULTS: Dict[str, Any] = {
    "language": "pt-BR",
    "theme": "dark",
    "web": {"host": C.DEFAULT_WEB_HOST, "port": C.DEFAULT_WEB_PORT,
            "open_browser": True},
    "scan": {"auto": C.AUTO_SCAN_ENABLED_DEFAULT,
             "interval_hours": C.AUTO_SCAN_INTERVAL_HOURS},
    "download": {"max_bytes": C.DOWNLOAD_MAX_SIZE,
                 "timeout": C.DOWNLOAD_TIMEOUT,
                 "verify_checksums": True,
                 "dir": os.path.join(C.config_dir(), "downloads")},
    "catalog": {"manifest": C.DEFAULT_CATALOG_MANIFEST},
    "updates": {"channel": "stable",  # stable | beta
                "notify": True,
                "check_on_start": True},
    "security": {"require_confirm": True,
                 "allow_unsigned": False,
                 "force": False},
    "cli": {"max_table_rows": 100, "color": "auto", "quiet": False},
}


class Config:
    def __init__(self, path: Optional[str] = None):
        self.path = path or _path()
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if os.path.isfile(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        self._data = _deep_merge(_deep_copy(DEFAULTS), self._data)

    def save(self) -> None:
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self._data
            for part in key.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return default
            return node

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
        self.save()

    def delete(self, key: str) -> None:
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                if not isinstance(node, dict) or part not in node:
                    return
                node = node[part]
            if isinstance(node, dict):
                node.pop(parts[-1], None)
        self.save()

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return _deep_copy(self._data)

    def reset(self) -> None:
        with self._lock:
            self._data = _deep_copy(DEFAULTS)
        self.save()

    @property
    def language(self) -> str:
        return self.get("language", "pt-BR")

    @property
    def theme(self) -> str:
        return self.get("theme", "dark")


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = _deep_copy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = _deep_copy(v)
    return out