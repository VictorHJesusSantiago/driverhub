# -*- coding: utf-8 -*-
"""Interface de terminal (CLI) do DriverHub.

Usa ``rich`` quando disponível e degrada para impressão simples caso contrário.
Funciona em Windows (PowerShell/cmd), Linux, macOS e Termux.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, Iterable, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    _RICH = True
except Exception:  # pragma: no cover
    _RICH = False


if _RICH:
    _console = Console(highlight=False, safe_box=True, legacy_windows=True)
else:
    _console = None


def _encodable(ch: str) -> bool:
    """True se o caractere pode ser escrito no encoding do stdout."""
    try:
        ch.encode(sys.stdout.encoding or "utf-8", errors="strict")
        return True
    except Exception:
        return False


_OK = "✔" if _encodable("✔") else "OK "
_WARN = "▲" if _encodable("▲") else "!"
_FAIL = "✖" if _encodable("✖") else "X"
_ARROW = "➤" if _encodable("➤") else ">"


def out(*args: Any, **kw: Any) -> None:
    if _RICH:
        _console.print(*args, **kw)
    else:
        print(*args)


def err(*args: Any, **kw: Any) -> None:
    text = " ".join(str(a) for a in args)
    if _RICH:
        _console.print(f"[red]{text}[/red]", **kw)
    else:
        print(text, file=sys.stderr)


def ok(msg: str) -> None:
    if _RICH:
        _console.print(f"[green]{_OK}[/green] {msg}")
    else:
        print(f"[{_OK}] {msg}")


def warn(msg: str) -> None:
    if _RICH:
        _console.print(f"[yellow]{_WARN}[/yellow] {msg}")
    else:
        print(f"[{_WARN}] {msg}")


def fail(msg: str) -> None:
    if _RICH:
        _console.print(f"[red]{_FAIL}[/red] {msg}")
    else:
        print(f"[{_FAIL}] {msg}")


def table(title: str, columns: List[str], rows: Iterable[Iterable[Any]],
          highlight: Optional[str] = None) -> None:
    rows = list(rows)
    if not rows:
        warn(f"Nada encontrado em '{title}'.")
        return
    if _RICH:
        t = Table(title=title, title_style="bold cyan", show_lines=False)
        for c in columns:
            t.add_column(c, style="cyan", header_style="bold")
        for r in rows:
            cells = [str(x) if x is not None else "" for x in r]
            text_cells = []
            for i, cell in enumerate(cells):
                if highlight is not None and highlight in cell:
                    text_cells.append(Text(cell, style="bold yellow"))
                else:
                    text_cells.append(cell)
            t.add_row(*text_cells)
        _console.print(t)
    else:
        print(f"\n=== {title} ===")
        print(" | ".join(columns))
        print("-" * 60)
        for r in rows:
            print(" | ".join(str(x) if x is not None else "" for x in r))


def kv(title: str, data: Dict[str, Any], cols: int = 2) -> None:
    if _RICH:
        lines = "\n".join(f"[cyan]{k}[/cyan]: [white]{v}[/white]" for k, v in data.items())
        _console.print(Panel(lines, title=title, border_style="blue"))
    else:
        print(f"\n=== {title} ===")
        for k, v in data.items():
            print(f"  {k}: {v}")


def progress(title: str, total: int = 1) -> Any:
    if _RICH and total > 0:
        bar = Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                       BarColumn(), TextColumn("{task.completed}/{task.total}"))
        bar_task = bar.add_task(title, total=total)
        return bar, bar_task
    return None


def progress_advance(handle: Any) -> None:
    if handle and _RICH:
        bar, task = handle
        bar.advance(task)


def progress_done(handle: Any) -> None:
    if handle and _RICH:
        bar, task = handle
        bar.update(task, completed=bar.tasks[task].total)
        bar.stop()


def spinner(title: str) -> Any:
    if _RICH:
        return Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"))
    return None


def spinner_stop(handle: Any) -> None:
    if handle and _RICH:
        handle.stop()


def table_auto(title: str, rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
    """Tabela a partir de listas de dicts (usa chaves comuns)."""
    if not rows:
        warn(f"Nada encontrado em '{title}'.")
        return
    keys = columns or list(rows[0].keys())
    table(title, keys, [[r.get(k, "") for k in keys] for r in rows])