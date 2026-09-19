# -*- coding: utf-8 -*-
"""Helpers de rede: IPs locais, conectividade e requisições seguras."""
from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


def local_ips() -> List[str]:
    ips: List[str] = []
    try:
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


def has_internet(timeout: float = 5.0) -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def http_get(url: str, timeout: int = 30, headers: Optional[Dict[str, str]] = None,
             max_bytes: int = 0) -> Dict[str, Any]:
    """GET com timeout, User-Agent e limite opcional de tamanho."""
    hdrs = {"User-Agent": "DriverHub/0.9 (+https://github.com/anomalyco/driverhub)"}
    if headers:
        hdrs.update(headers)
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read() if max_bytes <= 0 else resp.read(max_bytes + 1)
            if max_bytes > 0 and len(data) > max_bytes:
                return {"ok": False, "error": "exceeded max size",
                        "status": resp.status}
            return {"ok": True, "status": resp.status, "data": data,
                    "headers": dict(resp.headers)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "status": 0}


def http_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    import json
    res = http_get(url, timeout=timeout)
    if not res.get("ok"):
        return res
    try:
        return {"ok": True, "json": json.loads(res["data"].decode("utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": f"JSON inválido: {exc}"}