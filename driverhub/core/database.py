# -*- coding: utf-8 -*-
"""Persistência SQLite: catálogo de fontes oficiais, inventário, drivers e histórico."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .. import __version__


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Camada de acesso ao SQLite (thread-safe, um por processo)."""

    def __init__(self, path: Optional[str] = None):
        if path is None:
            base = os.path.join(os.path.expanduser("~"), ".driverhub")
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "driverhub.db")
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor TEXT, category TEXT, device TEXT,
                    os TEXT, url TEXT, notes TEXT, added_at TEXT
                );
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT, name TEXT, vendor TEXT,
                    driver_id TEXT, driver_version TEXT, status TEXT,
                    scan_at TEXT
                );
                CREATE TABLE IF NOT EXISTS drivers (
                    id TEXT PRIMARY KEY,
                    name TEXT, provider TEXT, version TEXT,
                    date TEXT, class TEXT, inf_file TEXT,
                    original_name TEXT, publisher TEXT,
                    status TEXT, source TEXT, scanned_at TEXT
                );
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, action TEXT, target TEXT, detail TEXT, ok INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_catalog_vendor ON catalog(vendor);
                CREATE INDEX IF NOT EXISTS idx_catalog_cat ON catalog(category);
                CREATE INDEX IF NOT EXISTS idx_devices_kind ON devices(kind);
                CREATE INDEX IF NOT EXISTS idx_drivers_class ON drivers(class);
                """
            )
            cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','1')")
            cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('app_version',?)", (__version__,))
            self._conn.commit()
            self._seed_catalog_once()

    def _seed_catalog_once(self) -> None:
        """Semeia o catálogo de fontes oficiais na primeira execução (idempotente)."""
        try:
            if self.get_meta("catalog_seeded"):
                return
            with self._lock:
                from . import catalog as catalog_mod  # import local (evita ciclo)
                catalog_mod.seed(self)
                self.set_meta("catalog_seeded", "yes")
        except Exception:
            pass

    # ---------- genérico ----------
    def set_meta(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                               (key, json.dumps(value) if not isinstance(value, str) else value))
            self._conn.commit()

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        v = row["value"]
        try:
            return json.loads(v)
        except Exception:
            return v

    # ---------- catálogo ----------
    def catalog_upsert(self, entries: Iterable[Dict[str, Any]]) -> int:
        n = 0
        with self._lock:
            for e in entries:
                exists = self._conn.execute(
                    "SELECT id FROM catalog WHERE vendor=? AND category=? AND device=? AND os=? AND url=?",
                    (e.get("vendor", ""), e.get("category", ""), e.get("device", ""),
                     e.get("os", ""), e.get("url", ""))).fetchone()
                if exists:
                    self._conn.execute(
                        "UPDATE catalog SET notes=?, added_at=? WHERE id=?",
                        (e.get("notes", ""), _now(), exists["id"]))
                else:
                    self._conn.execute(
                        "INSERT INTO catalog(vendor,category,device,os,url,notes,added_at) VALUES(?,?,?,?,?,?,?)",
                        (e.get("vendor", ""), e.get("category", ""), e.get("device", ""),
                         e.get("os", ""), e.get("url", ""), e.get("notes", ""), _now()))
                    n += 1
            self._conn.commit()
        return n

    def catalog_search(self, term: str = "", category: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            q = "SELECT * FROM catalog WHERE 1=1"
            args: List[Any] = []
            if term:
                q += " AND (vendor LIKE ? OR device LIKE ? OR category LIKE ? OR notes LIKE ?)"
                like = f"%{term}%"
                args += [like, like, like, like]
            if category:
                q += " AND category=?"
                args.append(category)
            q += " ORDER BY vendor, category, device LIMIT 500"
            return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    def catalog_categories(self) -> List[str]:
        with self._lock:
            return [r["category"] for r in self._conn.execute(
                "SELECT DISTINCT category FROM catalog ORDER BY category").fetchall()]

    def catalog_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) AS c FROM catalog").fetchone()["c"]

    # ---------- inventário ----------
    def save_devices(self, devices: Iterable[Dict[str, Any]]) -> int:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("DELETE FROM devices")
            n = 0
            for d in devices:
                cur.execute(
                    "INSERT INTO devices(kind,name,vendor,driver_id,driver_version,status,scan_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (d.get("kind", ""), d.get("name", ""), d.get("vendor", ""),
                     d.get("driver_id", ""), d.get("driver_version", ""),
                     d.get("status", ""), _now()))
                n += 1
            self._conn.commit()
        return n

    def list_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(
                "SELECT * FROM devices ORDER BY kind, name").fetchall()]

    # ---------- drivers ----------
    def save_drivers(self, drivers: Iterable[Dict[str, Any]]) -> int:
        with self._lock:
            cur = self._conn.cursor()
            n = 0
            for d in drivers:
                did = d.get("id") or d.get("inf_file") or d.get("name") or f"d{n}"
                cur.execute(
                    "INSERT OR REPLACE INTO drivers(id,name,provider,version,date,class,inf_file,"
                    "original_name,publisher,status,source,scanned_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (did, d.get("name", ""), d.get("provider", ""), d.get("version", ""),
                     d.get("date", ""), d.get("class", ""), d.get("inf_file", ""),
                     d.get("original_name", ""), d.get("publisher", ""),
                     d.get("status", "installed"), d.get("source", ""), _now()))
                n += 1
            self._conn.commit()
        return n

    def list_drivers(self, cls: str = "", term: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            q = "SELECT * FROM drivers WHERE 1=1"
            args: List[Any] = []
            if cls:
                q += " AND class=?"
                args.append(cls)
            if term:
                like = f"%{term}%"
                q += " AND (name LIKE ? OR provider LIKE ? OR version LIKE ?)"
                args += [like, like, like]
            q += " ORDER BY class, provider, name"
            return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    def get_driver(self, did: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM drivers WHERE id=?", (did,)).fetchone()
        return dict(row) if row else None

    def delete_driver_row(self, did: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM drivers WHERE id=?", (did,))
            self._conn.commit()

    def driver_classes(self) -> List[str]:
        with self._lock:
            return [r["class"] for r in self._conn.execute(
                "SELECT DISTINCT class FROM drivers ORDER BY class").fetchall()]

    # ---------- histórico ----------
    def log(self, action: str, target: str = "", detail: str = "", ok: bool = True) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO history(ts,action,target,detail,ok) VALUES(?,?,?,?,?)",
                (_now(), action, target, detail, 1 if ok else 0))
            self._conn.commit()

    def history(self, limit: int = 100, term: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            q = "SELECT * FROM history WHERE 1=1"
            args: List[Any] = []
            if term:
                like = f"%{term}%"
                q += " AND (action LIKE ? OR target LIKE ? OR detail LIKE ?)"
                args += [like, like, like]
            q += " ORDER BY id DESC LIMIT ?"
            args.append(limit)
            return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            def one(q: str) -> int:
                return self._conn.execute(q).fetchone()[0]
            return {
                "catalog": one("SELECT COUNT(*) FROM catalog"),
                "devices": one("SELECT COUNT(*) FROM devices"),
                "drivers": one("SELECT COUNT(*) FROM drivers"),
                "history": one("SELECT COUNT(*) FROM history"),
            }

    def close(self) -> None:
        try:
            with self._lock:
                self._conn.close()
        except Exception:
            pass