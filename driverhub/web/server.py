# -*- coding: utf-8 -*-
"""Servidor HTTP (biblioteca padrão) + API JSON do DriverHub.

Interface web acessível de qualquer navegador (PC, celular, TV) na mesma rede.
A API é read/write com proteção em operações destrutivas (exigem query param
``confirm=1`` e são registradas no histórico).
"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from ..core import actions, platform
from ..core.database import Database

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class _Api:
    def __init__(self, db: Database):
        self.db = db

    # ---------- read ----------
    def boot(self) -> Dict[str, Any]:
        info = platform.detect_all()
        return {
            "version": "0.9.0",
            "os": info["os"],
            "device_class": info.get("device_class", ""),
            "admin": info["os"]["admin"],
            "stats": self.db.stats(),
            "recent": self.db.history(limit=8),
        }

    def dashboard(self) -> Dict[str, Any]:
        return {
            "stats": self.db.stats(),
            "drivers_classes": _top(db_drivers_class_counts(self.db), 12),
            "devices_kinds": _top(db_device_kind_counts(self.db), 12),
            "recent": self.db.history(limit=12),
            "os": platform.detect_os(),
        }

    def devices(self, kind: str = "") -> Dict[str, Any]:
        rows = self.db.list_devices()
        if kind:
            rows = [r for r in rows if r.get("kind") == kind]
        return {"devices": rows, "kinds": db_device_kind_counts(self.db)}

    def drivers(self, cls: str = "", term: str = "") -> Dict[str, Any]:
        rows = self.db.list_drivers(cls=cls, term=term)
        return {"drivers": rows, "classes": self.db.driver_classes()}

    def driver(self, did: str) -> Dict[str, Any]:
        row = self.db.get_driver(did)
        if row is None and platform.detect_os()["system"] == "windows":
            row = actions.engine().driver_details(did)
        return {"driver": row or {}}

    def catalog(self, category: str = "", term: str = "") -> Dict[str, Any]:
        rows = self.db.catalog_search(term=term, category=category)
        return {"catalog": rows, "categories": self.db.catalog_categories()}

    def history(self, limit: int = 100, term: str = "") -> Dict[str, Any]:
        return {"history": self.db.history(limit=limit, term=term)}

    def hardware(self) -> Dict[str, Any]:
        return {"hardware": platform.detect_all()}

    # ---------- write (todas exigem confirm=1) ----------
    def action_scan(self) -> Dict[str, Any]:
        return actions.run_scan(self.db)

    def action_install(self, target: str) -> Dict[str, Any]:
        return actions.run_install(self.db, target)

    def action_remove(self, target: str, force: bool = False) -> Dict[str, Any]:
        return actions.run_remove(self.db, target, force=force)

    def action_update(self, target: str) -> Dict[str, Any]:
        return actions.run_update(self.db, target)

    def action_catalog_update(self, manifest: str = "") -> Dict[str, Any]:
        from ..core import catalog as cat
        return actions.catalog_sync(self.db, manifest or cat.DEFAULT_MANIFEST)


def db_drivers_class_counts(db: Database) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in db.list_drivers():
        c = r.get("class") or "outros"
        counts[c] = counts.get(c, 0) + 1
    return counts


def db_device_kind_counts(db: Database) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in db.list_devices():
        k = r.get("kind") or "outros"
        counts[k] = counts.get(k, 0) + 1
    return counts


def _top(d: Dict[str, int], n: int) -> Dict[str, int]:
    return dict(sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n])


class DriverHubHandler(BaseHTTPRequestHandler):
    api: _Api = None  # type: ignore[assignment]
    server_version = "DriverHub/0.9"

    # ---------- helpers ----------
    def _json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg: str, status: int = 400) -> None:
        self._json({"error": msg}, status)

    def _static(self, path: str) -> None:
        safe = os.path.normpath(path).lstrip("\\/")
        full = os.path.join(STATIC_DIR, safe)
        if not os.path.isfile(full) or not full.startswith(STATIC_DIR):
            self._error("not found", 404)
            return
        mt = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if mt and mt.startswith("text/") or mt in ("application/javascript",
                                                   "application/json",
                                                   "image/svg+xml"):
            mt += "; charset=utf-8" if mt.startswith("text/") else ""
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mt)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # ---------- routing ----------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        path = parsed.path.rstrip("/") or "/"
        try:
            if path in ("/", "/index.html"):
                self._static("index.html")
            elif path == "/static/app.js":
                self._static("app.js")
            elif path == "/static/style.css":
                self._static("style.css")
            elif path == "/api/boot":
                self._json(self.api.boot())
            elif path == "/api/dashboard":
                self._json(self.api.dashboard())
            elif path == "/api/devices":
                self._json(self.api.devices(q.get("kind", "")))
            elif path == "/api/drivers":
                self._json(self.api.drivers(q.get("class", ""), q.get("term", "")))
            elif path.startswith("/api/drivers/"):
                self._json(self.api.driver(urllib.parse.unquote(path.split("/")[-1])))
            elif path == "/api/catalog":
                self._json(self.api.catalog(q.get("category", ""), q.get("term", "")))
            elif path == "/api/history":
                self._json(self.api.history(int(q.get("limit", 100)), q.get("term", "")))
            elif path == "/api/hardware":
                self._json(self.api.hardware())
            else:
                self._error("endpoint não encontrado", 404)
        except Exception as exc:  # noqa: BLE001
            self.db_log("web:get_error", path, str(exc), False)
            self._error(f"erro interno: {exc}", 500)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {}
        if q.get("confirm") not in ("1", "true", "yes"):
            self._error("confirmação obrigatória: adicione ?confirm=1", 400)
            return
        try:
            if parsed.path == "/api/actions/scan":
                self.db_log("web:action", "scan", "", True)
                self._json(self.api.action_scan())
            elif parsed.path == "/api/actions/install":
                target = body.get("target", "")
                if not target:
                    self._error("target obrigatório", 400)
                    return
                res = self.api.action_install(target)
                self._json(res, 200 if res.get("ok") else 500)
            elif parsed.path == "/api/actions/remove":
                target = body.get("target", "")
                if not target:
                    self._error("target obrigatório", 400)
                    return
                res = self.api.action_remove(target, force=bool(body.get("force")))
                self._json(res, 200 if res.get("ok") else 500)
            elif parsed.path == "/api/actions/update":
                target = body.get("target", "")
                inf = body.get("inf")
                res = actions.run_update(self.db, target, inf)
                self._json(res, 200 if res.get("ok") else 500)
            elif parsed.path == "/api/actions/catalog-update":
                res = self.api.action_catalog_update(body.get("manifest", ""))
                self._json(res, 200 if res.get("status") != "error" else 500)
            else:
                self._error("endpoint não encontrado", 404)
        except Exception as exc:  # noqa: BLE001
            self.db_log("web:action_error", parsed.path, str(exc), False)
            self._error(f"erro interno: {exc}", 500)

    def db_log(self, action: str, target: str, detail: str, ok: bool) -> None:
        try:
            self.api.db.log(action, target, detail, ok)
        except Exception:
            pass

    def log_message(self, fmt: str, *args: Any) -> None:
        pass


def start_server(db: Database,
                 host: str = "0.0.0.0",
                 port: int = 8000,
                 open_browser: bool = True,
                 blocking: bool = True) -> None:
    """Inicia o servidor web. Se ``blocking`` for False, roda em thread."""
    # garante catálogo semeado
    from ..core.catalog import seed
    seed(db)

    DriverHubHandler.api = _Api(db)
    srv = ThreadingHTTPServer((host, port), DriverHubHandler)

    via = f"http://127.0.0.1:{port}"
    ips = _local_ips()

    print("\n" + "═" * 58)
    print("  DriverHub — interface gráfica web")
    print("═" * 58)
    print(f"  Local:    {via}")
    if ips:
        print(f"  Celular:  http://{ips[0]}:{port}   (mesma rede Wi-Fi)")
    print("  Para sair: Ctrl+C")
    print("═" * 58 + "\n")

    if open_browser:
        threading.Timer(0.6, _open_browser, args=(via,)).start()

    if blocking:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()


def _open_browser(url: str) -> None:
    import webbrowser
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _local_ips() -> list[str]:
    ips: list[str] = []
    try:
        import socket
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips