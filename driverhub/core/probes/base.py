# -*- coding: utf-8 -*-
"""Núcleo das sondas: registro global, despacho e execução sem exceções.

Uma sonda é um ``Probe`` (nome, descrição, prioridade, função). A função
deve retornar um ``Result``, um ``dict`` com ``ok``/``detail`` ou qualquer
valor serializável. ``dispatch`` e ``run_command`` jamais lançam.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

PROBES: Dict[str, "Probe"] = {}


@dataclass
class Probe:
    """Registro descritivo de uma sonda."""
    name: str
    desc: str
    func: Callable[..., "Result"]
    priority: int = 100


@dataclass
class Result:
    """Resultado padronizado de uma sonda."""
    ok: bool
    detail: str = ""
    data: Any = None
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "detail": self.detail, "data": self.data,
                "name": self.name}

    @classmethod
    def from_command(cls, args: List[str], timeout: int = 60,
                     name: str = "") -> "Result":
        res = run_command(args, timeout)
        return cls(ok=res["ok"], detail=res["detail"], data=res["data"],
                   name=name)


def register(probe: Probe) -> Probe:
    """Registra (ou substitui) uma sonda no núcleo."""
    PROBES[probe.name] = probe
    return probe


def probe(name: str, desc: str, priority: int = 100):
    """Decorator que registra uma função como sonda."""
    def wrap(fn: Callable[..., "Result"]) -> Callable[..., "Result"]:
        register(Probe(name=name, desc=desc, func=fn, priority=priority))
        return fn
    return wrap


def dispatch(name: str, **kw: Any) -> Result:
    """Executa uma sonda pelo nome. Nunca lança."""
    item = PROBES.get(name)
    if item is None:
        return Result(ok=False, detail=f"Sonda desconhecida: {name}", name=name)
    try:
        out = item.func(**kw)
        if isinstance(out, Result):
            return out
        if isinstance(out, dict):
            return Result(ok=bool(out.get("ok")),
                          detail=str(out.get("detail") or ""),
                          data=out.get("data"), name=name)
        return Result(ok=True, detail="OK", data=out, name=name)
    except Exception as exc:  # noqa: BLE001
        return Result(ok=False, detail=f"Falha na sonda: {exc}", name=name)


def run_all(names: Optional[List[str]] = None) -> List[Result]:
    """Executa todas as sondas registradas (ou apenas as listadas)."""
    if names is None:
        items = sorted(PROBES.values(), key=lambda p: (p.priority, p.name))
    else:
        items = [PROBES[n] for n in names if n in PROBES]
    return [dispatch(p.name) for p in items]


class BaseProbe:
    """Classe base opcional para sondas orientadas a objeto."""

    name: str = "base"
    desc: str = "Sonda genérica"

    def run(self, **kw: Any) -> Result:
        """Ponto de entrada da sonda; subclasses devem implementar."""
        raise NotImplementedError

    @staticmethod
    def run_command(args: List[str], timeout: int = 60) -> Result:
        return run_command(args if isinstance(args, list) else [str(args[0])],
                           timeout)


def run_command(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    """Executa um comando capturando stdout/stderr. Nunca lança."""
    kwargs: Dict[str, Any] = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.run(args, timeout=timeout, **kwargs)
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "detail": _decode(proc.stderr or b""),
            "data": _decode(proc.stdout or b""),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "detail": "tempo esgotado", "data": ""}
    except FileNotFoundError:
        bin_name = args[0] if args else ""
        return {"ok": False, "code": -2,
                "detail": f"comando não encontrado: {bin_name}", "data": ""}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": -3, "detail": str(exc), "data": ""}


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp850", "utf-16"):
        try:
            return raw.decode(enc).strip()
        except Exception:  # noqa: BLE001
            continue
    return raw.decode("utf-8", errors="replace").strip()