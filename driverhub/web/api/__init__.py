# -*- coding: utf-8 -*-
"""API modular e framework-free do DriverHub.

Cada rota é uma função leve que aceita ``store`` (Database) e/ou um ``handler``
HTTP; nenhum módulo aqui depende de framework. O :class:`Router` apenas casa
método + caminho com um handler e entrega os parâmetros capturados; o
consumidor (ex.: ``web.server``) decide como serializar o ``dict`` retornado.
"""
from __future__ import annotations

API_VERSION = "1.0.0"


def _split(path: str) -> list[str]:
    return [p for p in str(path or "").split("/") if p]


def _param(part: str) -> bool:
    return part.startswith("<") and part.endswith(">") and len(part) > 2


class Router:
    """Roteador mínimo: ``register(method, path, handler)`` e ``match(...)``.

    Suporta um parâmetro nomeado no fim do caminho (ex.: ``/api/drivers/<driver_id>``).
    """

    def __init__(self):
        self._routes: list = []

    def register(self, method: str, path: str, handler) -> object:
        self._routes.append((str(method).upper(), _split(path), handler))
        return handler

    def match(self, method: str, path: str):
        method = str(method).upper()
        parts = _split(path)
        for m, pat, handler in self._routes:
            if m != method:
                continue
            if pat == parts:
                return handler, {}
            if (len(pat) == len(parts) and pat and _param(pat[-1])
                    and pat[:-1] == parts[:-1]):
                return handler, {pat[-1][1:-1]: parts[-1]}
        return None, {}

    def paths(self) -> list:
        return ["%s /%s" % (m, "/".join(pat)) for m, pat, _ in self._routes]


def build_router():
    """Cria um :class:`Router` pré-registrado com todas as rotas da API."""
    router = Router()
    register_routes(router)
    return router


def handle(router, method: str, path: str, store=None, query=None, body=None):
    """Casa método+caminho e executa o handler, devolvendo um ``dict``.

    Se nenhuma rota casar, devolve ``{"error": "endpoint não encontrado"}``.
    """
    handler, params = router.match(method, path)
    if handler is None:
        return {"error": "endpoint não encontrado"}
    return handler(store, query or {}, body or {}, params)


def register_routes(router):
    """Registra as rotas modulares da API no ``router`` informado.

    Handlers seguem o contrato ``(store, query, body, params)`` — ``query`` é
    o dict de parâmetros de URL, ``body`` o corpo JSON (POST) e ``params`` os
    valores capturados do caminho (ex.: ``/api/drivers/<driver_id>``).
    """
    from . import (actions, backups, catalog, check, dashboard, devices,
                   drivers, hardware, history, qr, settings)
    from .base import ApiError

    def safe(fn):
        def wrapped(store, query, body, params):
            try:
                return fn(store, query, body, params)
            except ApiError as exc:
                return {"error": exc.message}
            except Exception as exc:  # noqa: BLE001
                return {"error": f"erro interno: {exc}"}
        return wrapped

    def _get(path, fn):
        router.register("GET", path, safe(fn))

    def _post(path, fn):
        router.register("POST", path, safe(fn))

    # ---------- leitura ----------
    _get("/api/boot", lambda store, q, b, p: dashboard.get_boot(store))
    _get("/api/dashboard", lambda store, q, b, p: dashboard.get_dashboard(store))

    _get("/api/devices", lambda store, q, b, p: devices.get_devices(
        store, q.get("q", ""), q.get("category", "")))
    _get("/api/devices/problems", lambda store, q, b, p: devices.device_problems(store))
    _get("/api/devices/<device_id>", lambda store, q, b, p: devices.get_device(
        store, p.get("device_id", "")))

    _get("/api/drivers", lambda store, q, b, p: drivers.get_drivers(
        store, q.get("q", ""), q.get("status", "")))
    _get("/api/drivers/<driver_id>", lambda store, q, b, p: drivers.get_driver(
        p.get("driver_id", ""), store=store))

    _get("/api/catalog/search", lambda store, q, b, p: catalog.catalog_search(
        q.get("text", ""), store=store))
    _get("/api/catalog/categories", lambda store, q, b, p: catalog.catalog_categories(store))
    _get("/api/catalog/<id>", lambda store, q, b, p: catalog.get_catalog_entry(
        p.get("id", ""), store=store))
    _get("/api/catalog", lambda store, q, b, p: catalog.get_catalog(
        store, q.get("q", ""), q.get("category", "")))

    _get("/api/history/<eid>", lambda store, q, b, p: history.get_event(
        p.get("eid", ""), store=store))
    _get("/api/history", lambda store, q, b, p: history.get_history(
        store, q.get("limit", 100)))

    _get("/api/settings", lambda store, q, b, p: settings.get_settings(store))

    _get("/api/hardware/sensors", lambda store, q, b, p: hardware.get_sensors())
    _get("/api/hardware/disks", lambda store, q, b, p: hardware.get_disks())
    _get("/api/hardware", lambda store, q, b, p: hardware.get_hardware(store))

    _get("/api/check", lambda store, q, b, p: check.get_check_summary(store))
    _get("/api/backups", lambda store, q, b, p: backups.list_backups(store))
    _get("/api/qr", lambda store, q, b, p: qr.qr_content(store))

    # ---------- escrita (todas exigem ?confirm=1; ver actions.require_confirm) ----------
    _post("/api/actions/scan", lambda store, q, b, p: actions.dispatch_action("scan", b, store=store))
    _post("/api/actions/install", lambda store, q, b, p: actions.dispatch_action("install", b, store=store))
    _post("/api/actions/remove", lambda store, q, b, p: actions.dispatch_action("remove", b, store=store))
    _post("/api/actions/update", lambda store, q, b, p: actions.dispatch_action("update", b, store=store))
    _post("/api/actions/catalog-update", lambda store, q, b, p: actions.dispatch_action(
        "catalog-update", b, store=store))
    _post("/api/actions/check", lambda store, q, b, p: actions.dispatch_action("check", b, store=store))
    _post("/api/actions/backup", lambda store, q, b, p: backups.create_backup(store))
    _post("/api/actions/restore", lambda store, q, b, p: backups.restore_backup(
        b.get("source", ""), store))
    _post("/api/actions/delete-backup", lambda store, q, b, p: backups.delete_backup(
        b.get("name", ""), store))
    _post("/api/history/clear", lambda store, q, b, p: history.clear_history(
        store, q.get("confirm", "") or b.get("confirm", "")))
    _post("/api/settings/set", lambda store, q, b, p: settings.set_setting(
        b.get("key", ""), b.get("value"), store=store))
    _post("/api/settings/reset", lambda store, q, b, p: settings.reset_settings(store))