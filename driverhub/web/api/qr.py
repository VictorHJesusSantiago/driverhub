# -*- coding: utf-8 -*-
"""URL de acesso rápido e QR Code aproximado (sem dependência externa).

O :func:`as_ascii` NÃO implementa um QR Code real (padrão ISO/IEC 18004): gera
uma grade determinística estilo QR a partir do conteúdo, com padrões de encontro
(finder patterns), linha de tempo (timing), conteúdo derivado de um PRNG
semeado pelo SHA-256 do texto e uma **linha de checksum simples** embutida
(última linha da grade). Destina-se apenas à identificação visual rápida do
destino; é 100% determinístico — mesmas entradas produzem exatamente a mesma
grade.
"""
from __future__ import annotations

import hashlib

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000


def _web(store):
    port = DEFAULT_PORT
    try:
        port = int(store.get_meta("web_port", DEFAULT_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    return DEFAULT_HOST, port


def web_url(host, port) -> str:
    """Monta ``http://<host>:<port>/`` normalizando host/porta."""
    host = str(host or DEFAULT_HOST).strip() or DEFAULT_HOST
    try:
        port = int(port)
        if not 1 <= port <= 65535:
            port = DEFAULT_PORT
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    base = host
    if base.startswith(("http://", "https://")):
        base = base.split("://", 1)[1]
    base = base.rstrip("/")
    if ":" in base and not base.startswith("["):
        base = "[" + base + "]"
    return f"http://{base}:{port}/"


def qr_content(store):
    """Gera a URL de acesso rápido: ``http://<ip-local>:<porta>/``."""
    try:
        from ...tools import net
        ips = net.local_ips()
        _, port = _web(store)
        entries = [{"ip": ip, "url": web_url(ip, port)} for ip in ips]
        url = entries[0]["url"] if entries else web_url("127.0.0.1", port)
        return {"url": url, "ips": ips, "port": port, "entries": entries}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"erro ao gerar URL de acesso rápido: {exc}"}


def as_ascii(data, size: int | None = None) -> str:
    """Desenha uma grade estilo QR determinística usando blocos ▀ ▄ █.

    ``size`` força a quantidade de módulos (ímpar, 21..43); por padrão é
    derivada do hash do conteúdo. Retorna uma string multi-linha.
    """
    data = str(data or "")
    digest = hashlib.sha256(data.encode("utf-8")).digest()
    n = int(size) if size else 21 + (digest[0] % 12) * 2
    if n < 21:
        n = 21
    dark = _fill_grid(data, n, digest)
    lines = _render(dark, n, _checksum(data))
    return "\n".join(lines)


def _checksum(data: str) -> int:
    """Checksum simples: soma dos bytes do conteúdo módulo 256."""
    return sum(data.encode("utf-8")) % 256


def _fill_grid(data: str, n: int, digest: bytes) -> set:
    dark = set()
    for (r, c, w) in ((0, 0, 7), (0, n - 7, 7), (n - 7, 0, 7)):
        _finder(dark, r, c, w, n)
    light = _separators(n)
    for i in range(8, n - 8):  # linha/coluna de tempo
        if i % 2 == 0:
            dark.add((6, i))
            dark.add((i, 6))
    cells = []
    for r in range(n):
        for c in range(n):
            if (r, c) in dark or (r, c) in light or r == n - 1:
                continue  # linha final reservada para o checksum
            cells.append((r, c))
    rng = _lcg(digest)
    for r, c in cells:
        if next(rng) % 10 < 5:
            dark.add((r, c))
    ck = _checksum(data)
    for i in range(8):  # bites do checksum (LSB primeiro) na linha final
        if (ck >> i) & 1:
            dark.add((n - 1, 8 + i))
    if ck:
        dark.add((n - 1, 0))  # marcador "checksum presente"
    return dark


def _finder(dark: set, r: int, c: int, w: int, n: int) -> None:
    for i in range(w):
        for j in range(w):
            edge = i == 0 or i == w - 1 or j == 0 or j == w - 1
            inner = 2 <= i <= 4 and 2 <= j <= 4
            if r + i < n and c + j < n and (edge or inner):
                dark.add((r + i, c + j))


def _separators(n: int) -> set:
    light = set()

    def add(r, c):
        if 0 <= r < n and 0 <= c < n:
            light.add((r, c))

    for i in range(8):  # sup-esq: (0..6, 0..6)
        add(7, i)
        add(i, 7)
    for i in range(8):  # sup-dir: (0..6, n-7..n-1)
        add(7, n - 1 - i)
        add(i, n - 8)
    for i in range(8):  # inf-esq: (n-7..n-1, 0..6)
        add(n - 1 - i, 7)
        add(n - 8, i)
    add(7, n - 8)  # esquina livre entre sup-dir e sup-esq
    return light


def _lcg(digest: bytes):
    seed = int.from_bytes(digest[:8], "big")
    while True:
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        yield seed >> 56


def _render(dark: set, n: int, cksum: int) -> list:
    quiet = 4
    rows = range(-quiet, n + quiet)
    lines = []
    for step in range(0, len(rows), 2):
        line = []
        for c in range(-quiet, n + quiet):
            top = (rows[step], c) in dark
            bot = (rows[step + 1], c) in dark if step + 1 < len(rows) else False
            if top and bot:
                line.append("\u2588")
            elif top:
                line.append("\u2580")
            elif bot:
                line.append("\u2584")
            else:
                line.append(" ")
        lines.append("".join(line))
    header = f"driverhub-qr cksum={cksum:02x} size={n}"
    width = len(lines[0]) if lines else 1
    lines.insert(0, " " * max(0, (width - len(header)) // 2) + header)
    return lines