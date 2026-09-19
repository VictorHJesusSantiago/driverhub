# -*- coding: utf-8 -*-
from __future__ import annotations

"""Cache LRU em memória/disca com TTL, persistência JSON e thread-safe."""

import json
import os
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

_EMPTY = object()


class TTLCache:
    """Cache LRU com tempo de vida (TTL) e persistência JSON opcional."""

    def __init__(self, maxsize: int = 128, ttl: float = 300.0):
        self.maxsize = max(1, int(maxsize or 1))
        self.ttl = max(0.0, float(ttl or 0.0))
        self._data: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()

    def _now(self) -> float:
        return time.time()

    def _expired(self, key: str) -> bool:
        item = self._data.get(key)
        if item is None:
            return True
        value, expires = item
        if expires is None:
            return False
        return self._now() > expires

    def _purge_expired(self):
        now = self._now()
        for key in list(self._data.keys()):
            item = self._data.get(key)
            if item is not None and item[1] is not None and now > item[1]:
                self._data.pop(key, None)

    def _evict(self):
        self._purge_expired()
        while len(self._data) > self.maxsize:
            try:
                oldest = next(iter(self._data))
                self._data.pop(oldest, None)
            except StopIteration:
                break

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            skey = str(key)
            with self._lock:
                if skey not in self._data or self._expired(skey):
                    self._data.pop(skey, None)
                    return default
                value, expires = self._data.pop(skey)
                self._data[skey] = (value, expires)
                return value
        except Exception:
            return default

    def set(self, key: Any, value: Any, ttl: Optional[float] = None):
        try:
            skey = str(key)
            lifetime = self.ttl if ttl is None else max(0.0, float(ttl))
            expires = self._now() + lifetime if lifetime > 0 else None
            with self._lock:
                self._data[skey] = (value, expires)
                self._evict()
        except Exception:
            pass

    def has(self, key: Any) -> bool:
        try:
            with self._lock:
                skey = str(key)
                if skey in self._data and not self._expired(skey):
                    return True
                self._data.pop(skey, None)
                return False
        except Exception:
            return False

    def delete(self, key: Any) -> bool:
        try:
            with self._lock:
                return self._data.pop(str(key), None) is not None
        except Exception:
            return False

    def clear(self):
        try:
            with self._lock:
                self._data.clear()
        except Exception:
            pass

    def get_or_set(self, key: Any, factory: Callable[[], Any], ttl: Optional[float] = None) -> Tuple[Any, bool]:
        """Devolve o valor em cache ou calcula via `factory` (flag: nova)."""
        cached = self.get(key, _EMPTY)
        if cached is not _EMPTY:
            return cached, False
        value = factory()
        self.set(key, value, ttl)
        return value, True

    def size(self) -> int:
        try:
            with self._lock:
                self._purge_expired()
                return len(self._data)
        except Exception:
            return 0

    def __len__(self) -> int:
        return self.size()

    def save(self, path: str) -> bool:
        """Persiste o cache em JSON (chaves viram strings). Nunca lança."""
        try:
            with self._lock:
                payload = {
                    "version": 1,
                    "ttl": self.ttl,
                    "maxsize": self.maxsize,
                    "items": {key: {"exp": item[1], "value": item[0]} for key, item in self._data.items()},
                }
            parent = os.path.dirname(os.path.abspath(str(path))) or "."
            os.makedirs(parent, exist_ok=True)
            with open(str(path), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load(self, path: str) -> int:
        """Carrega itens válidos de um JSON persistido. Nunca lança."""
        try:
            if not os.path.isfile(str(path)):
                return 0
            with open(str(path), "r", encoding="utf-8-sig") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return 0
            self.ttl = max(0.0, float(payload.get("ttl", self.ttl)))
            self.maxsize = max(1, int(payload.get("maxsize", self.maxsize)))
            now = self._now()
            count = 0
            with self._lock:
                for key, item in (payload.get("items") or {}).items():
                    try:
                        expires = item.get("exp")
                        if expires is not None and now > float(expires):
                            continue
                        self._data[str(key)] = (item.get("value"), expires)
                        count += 1
                    except Exception:
                        continue
                self._evict()
            return count
        except Exception:
            return 0