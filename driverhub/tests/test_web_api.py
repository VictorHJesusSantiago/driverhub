# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes da API web: helpers HTTP puros (json_response, read_body,
parse_query, method_guard), Router, autenticação por token e segurança
(block_path_traversal/sanitize_input). Nenhum servidor é iniciado: os
handlers são instanciados in-memory e os mocks evitam socket/rede.
"""

import io
import json
import unittest
from unittest import mock

from driverhub.web import api as api_pkg
from driverhub.web import server as server_mod
from driverhub.web.api import auth as api_auth
from driverhub.web.api import base as api_base
from driverhub.web.middleware import security as sec_mw


class JsonResponseTest(unittest.TestCase):
    def test_pure_response_no_handler(self):
        result = api_base.json_response({"a": 1})
        self.assertEqual(result["status"], 200)
        self.assertEqual(json.loads(result["body"]), {"a": 1})
        self.assertIn("application/json", result["content_type"])

    def test_api_error_status(self):
        result = api_base.json_response(api_base.ApiError("nada encontrado", 404))
        self.assertEqual(result["status"], 404)
        self.assertIn("nada encontrado", json.loads(result["body"])["error"])

    def test_writes_to_handler(self):
        sink = _Sink()
        sink.wfile = io.BytesIO()
        returned = api_base.json_response({"ok": True}, status=201, handler=sink)
        self.assertIsNone(returned)
        self.assertEqual(sink.status, 201)
        self.assertTrue(any(k == "Content-Type" for k, _ in sink.headers))
        self.assertEqual(json.loads(sink.wfile.getvalue()), {"ok": True})


class ReadBodyTest(unittest.TestCase):
    def test_no_content_length_returns_empty(self):
        handler = _BodySink(b"", headers={})
        self.assertEqual(api_base.read_body(handler), {})

    def test_valid_json(self):
        handler = _BodySink(b'{"a":1}', headers={"Content-Length": "7"})
        self.assertEqual(api_base.read_body(handler), {"a": 1})

    def test_empty_object(self):
        handler = _BodySink(b"{}", headers={"Content-Length": "2"})
        self.assertEqual(api_base.read_body(handler), {})

    def test_too_large_raises_413(self):
        handler = _BodySink(b"", headers={"Content-Length": str(api_base.MAX_BODY_BYTES + 1)})
        with self.assertRaises(api_base.ApiError) as ctx:
            api_base.read_body(handler)
        self.assertEqual(ctx.exception.status, 413)

    def test_invalid_json_raises_400(self):
        handler = _BodySink(b"its-not-json", headers={"Content-Length": "12"})
        with self.assertRaises(api_base.ApiError) as ctx:
            api_base.read_body(handler)
        self.assertEqual(ctx.exception.status, 400)


class ParseQueryTest(unittest.TestCase):
    def test_from_string(self):
        self.assertEqual(api_base.parse_query("/api/x?a=1&b=2"), {"a": "1", "b": "2"})

    def test_from_handler_path(self):
        handler = _BodySink(b"", {"path": "/api/drivers?class=Display"})
        self.assertEqual(api_base.parse_query(handler), {"class": "Display"})

    def test_empty(self):
        self.assertEqual(api_base.parse_query(""), {})


class MethodGuardTest(unittest.TestCase):
    def test_matching_method(self):
        self.assertTrue(api_base.method_guard("GET", "get"))

    def test_mismatch_raises_405(self):
        handler = _BodySink(b"", {"command": "GET"})
        with self.assertRaises(api_base.ApiError) as ctx:
            api_base.method_guard(handler, "POST")
        self.assertEqual(ctx.exception.status, 405)


class AuthTest(unittest.TestCase):
    def test_token_ok_valid(self):
        with mock.patch.object(api_auth, "_configured_token", return_value="sekret"):
            self.assertTrue(api_auth.token_ok("sekret"))

    def test_token_ok_invalid(self):
        with mock.patch.object(api_auth, "_configured_token", return_value="sekret"):
            self.assertFalse(api_auth.token_ok("errado"))
            self.assertFalse(api_auth.token_ok(None))

    def test_no_token_configured_passes(self):
        with mock.patch.object(api_auth, "_configured_token", return_value=""):
            self.assertTrue(api_auth.token_ok("qualquer-coisa"))
            self.assertTrue(api_auth.token_ok(""))

    def test_bearer_from_query(self):
        handler = _BodySink(b"", {"path": "/api/x?token=abc123"})
        self.assertEqual(api_auth.bearer_from(handler), "abc123")

    def test_bearer_from_header(self):
        handler = _BodySink(b"", {"path": "/api/x", "Authorization": "Bearer xyz456"})
        self.assertEqual(api_auth.bearer_from(handler), "xyz456")

    def test_issue_token(self):
        token = api_auth.issue_token()
        self.assertEqual(len(token), 43)
        self.assertNotEqual(token, api_auth.issue_token())


class SecurityMiddlewareTest(unittest.TestCase):
    def test_block_path_traversal_safe(self):
        self.assertIsNone(sec_mw.block_path_traversal("/api/drivers/oem10.inf"))

    def test_block_path_traversal_dotdot(self):
        for bad in ("../etc/passwd", "/a/../b", "%2e%2e/x", "a\\..\\b"):
            self.assertIsNotNone(sec_mw.block_path_traversal(bad), f"deveria bloquear {bad!r}")

    def test_sanitize_input_strips_controls(self):
        # _CTRL_RE remove o controle NUL/\x1f, mas preserva tab/LF/CR (0x09/0x0a/0x0d)
        # propositalmente — comportamento do middleware de segurança.
        result = sec_mw.sanitize_input("a\x00b\x1fc")
        self.assertEqual(result["sanitized"], "abc")
        self.assertFalse(result["safe"])

    def test_sanitize_input_clean(self):
        result = sec_mw.sanitize_input("abc")
        self.assertEqual(result["sanitized"], "abc")
        self.assertTrue(result["safe"])

    def test_sanitize_input_non_string(self):
        self.assertIsNone(sec_mw.sanitize_input(42))


class RouterTest(unittest.TestCase):
    def setUp(self):
        self.router = api_pkg.Router()

        def ping(store, query, body, params):
            return {"endpoint": "ping", "query": query}

        self.ping = ping
        self.router.register("GET", "/api/ping", ping)
        self.router.register("GET", "/api/drivers/<driver_id>",
                             lambda store, query, body, params: {
                                 "driver": params.get("driver_id", "")})

    def test_match_exact(self):
        handler, params = self.router.match("GET", "/api/ping")
        self.assertIs(handler, self.ping)
        self.assertEqual(params, {})

    def test_match_with_param(self):
        handler, params = self.router.match("GET", "/api/drivers/oem10.inf")
        self.assertIsNotNone(handler)
        self.assertEqual(params, {"driver_id": "oem10.inf"})

    def test_match_method_mismatch(self):
        handler, params = self.router.match("POST", "/api/ping")
        self.assertIsNone(handler)

    def test_match_unknown_path(self):
        handler, params = self.router.match("GET", "/api/unknown")
        self.assertIsNone(handler)

    def test_handle_calls_handler(self):
        result = api_pkg.handle(self.router, "GET", "/api/ping", query={"x": "1"})
        self.assertEqual(result["endpoint"], "ping")
        self.assertEqual(result["query"], {"x": "1"})

    def test_handle_unknown_route(self):
        result = api_pkg.handle(self.router, "POST", "/api/ping")
        self.assertIn("error", result)

    # Nota: build_router() registra rotas que importam módulos ausentes
    # (web.api.backups/qrt podem não existir) — portanto testamos o Router
    # diretamente, sem depender de register_routes/build_router.


class ServerHelpersTest(unittest.TestCase):
    def test_top_sorts_by_value(self):
        self.assertEqual(server_mod._top({"b": 1, "a": 3, "c": 2}, 2), {"a": 3, "c": 2})

    def test_drivers_class_counts(self):
        db = _FakeDB()
        self.assertEqual(
            server_mod.db_drivers_class_counts(db), {"Display": 2, "Network": 1})

    def test_device_kind_counts(self):
        db = _FakeDB()
        self.assertEqual(server_mod.db_device_kind_counts(db), {"gpu": 2, "audio": 1})


class DriverHubHandlerTest(unittest.TestCase):
    def test_get_known_api_route(self):
        handler = _make_handler("/api/drivers?class=Display",
                                api=_FakeApi())
        handler.do_GET()
        self.assertEqual(handler._state["status"], 200)
        payload = json.loads(handler.wfile.getvalue())
        self.assertEqual(payload["drivers"][0]["id"], "x")

    def test_get_unknown_route_404(self):
        handler = _make_handler("/api/endpoint-inexistente", api=_FakeApi())
        handler.do_GET()
        self.assertEqual(handler._state["status"], 404)

    def test_get_root_serves_index(self):
        handler = _make_handler("/", api=_FakeApi())
        handler.do_GET()
        self.assertEqual(handler._state["status"], 200)
        self.assertGreater(len(handler.wfile.getvalue()), 0)

    def test_static_missing_file_404(self):
        handler = _make_handler("/static/nao-existe.css", api=_FakeApi())
        handler._static("nao-existe.css")
        self.assertEqual(handler._state["status"], 404)

    def test_post_without_confirm_400(self):
        handler = _make_handler("/api/actions/scan", api=_FakeApi(), body=b"{}")
        handler.do_POST()
        self.assertEqual(handler._state["status"], 400)
        self.assertIn("confirmação", json.loads(handler.wfile.getvalue())["error"])

    def test_post_scan_with_confirm_200(self):
        handler = _make_handler("/api/actions/scan?confirm=1", api=_FakeApi(), body=b"{}")
        handler.do_POST()
        self.assertEqual(handler._state["status"], 200)
        self.assertEqual(json.loads(handler.wfile.getvalue())["ok"], True)

    def test_post_install_requires_target(self):
        handler = _make_handler("/api/actions/install?confirm=1", api=_FakeApi(), body=b"{}")
        handler.do_POST()
        self.assertEqual(handler._state["status"], 400)

    def test_post_unknown_route_404(self):
        handler = _make_handler("/api/nao-existe?confirm=1", api=_FakeApi(), body=b"{}")
        handler.do_POST()
        self.assertEqual(handler._state["status"], 404)

    def test_json_helper(self):
        handler = _make_handler("/api/drivers", api=_FakeApi())
        handler._json({"ok": True})
        self.assertEqual(handler._state["status"], 200)
        self.assertEqual(json.loads(handler.wfile.getvalue()), {"ok": True})


class _Sink:
    def __init__(self):
        self.status = None
        self.headers = []
        self.buffer = io.BytesIO()

    def send_response(self, status, message=None):
        self.status = status

    def send_header(self, key, value):
        self.headers.append((key, value))

    def end_headers(self):
        pass


class _BodySink:
    def __init__(self, body=b"", headers=None):
        self.body = body
        self.headers = dict(headers or {})
        self.rfile = io.BytesIO(body)
        self.path = self.headers.pop("path", None)
        self.command = self.headers.pop("command", None)

    def read(self, length):
        return self.rfile.read(length)


class _FakeDB:
    def list_drivers(self, cls="", term=""):
        return [
            {"class": "Display"},
            {"class": "Network"},
            {"class": "Display"},
        ]

    def list_devices(self, kind=""):
        return [{"kind": "gpu"}, {"kind": "gpu"}, {"kind": "audio"}]


class _FakeApi:
    def boot(self):
        return {"version": "0.9.0"}

    def drivers(self, cls="", term=""):
        return {"drivers": [{"id": "x"}], "classes": ["Display"]}

    def action_scan(self):
        return {"ok": True}


def _make_handler(path, api, body=b"", content_length=None):
    handler = object.__new__(server_mod.DriverHubHandler)
    handler.path = path
    handler.headers = _HeadersDict({"Content-Length": content_length or str(len(body))})
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.api = api
    state = {"status": None}

    def send_response(code, message=None):
        state["status"] = code

    handler.send_response = send_response
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler.db_log = lambda *args, **kwargs: None
    handler._state = state
    return handler


class _HeadersDict(dict):
    def __init__(self, data):
        super().__init__(data)

    def get(self, key, default=None):
        return super().get(key, default)


if __name__ == "__main__":
    unittest.main()