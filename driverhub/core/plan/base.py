# -*- coding: utf-8 -*-
"""Modelos base de planejamento: política, ação e plano de execução.

``Policy`` descreve o comportamento desejado (o que atualizar, como).
``PlanAction`` é uma etapa concreta do plano.
``Plan`` é a coleção ordenada de ações, com suporte a filtragem, ordenação,
serialização e detecção de necessidade de privilégios de administrador.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

KIND_ORDER: tuple = ("validate", "download", "apply", "wait", "reboot")
RISK_ORDER: tuple = ("low", "medium", "high")


def _norm(v: str, default: str = "") -> str:
    return str(v or default).strip()


@dataclass
class Policy:
    """Política de atualização de drivers.

    - ``categories`` vazio significa "todas as categorias".
    - ``blacklist`` exclui categorias (ou termos presentes no alvo).
    - ``strict`` exige fontes confirmadas/oficiais.
    - ``dry_run`` apenas planeja (não aplica) — reduz o risco percebido.
    """
    name: str = "default"
    strict: bool = False
    categories: List[str] = field(default_factory=list)
    dry_run: bool = False
    reboot: bool = True
    priority: str = "medium"
    schedule: Optional[Dict[str, Any]] = None
    blacklist: List[str] = field(default_factory=list)

    def allows(self, category: str = "", target: str = "") -> bool:
        """Verifica se a política aceita uma categoria/target."""
        try:
            cat = _norm(category).lower()
            tgt = _norm(target).lower()
            black = [str(b).lower() for b in (self.blacklist or [])]
            if black and (cat in black or any(b and b in tgt for b in black)):
                return False
            cats = [str(c).lower() for c in (self.categories or [])]
            if cats:
                return cat in cats or any(c and c in cat for c in cats)
            return True
        except Exception:
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "strict": bool(self.strict),
            "categories": list(self.categories or []),
            "dry_run": bool(self.dry_run),
            "reboot": bool(self.reboot),
            "priority": str(self.priority or "medium"),
            "schedule": dict(self.schedule or {}) if self.schedule else None,
            "blacklist": list(self.blacklist or []),
        }


@dataclass
class PlanAction:
    """Uma ação concreta do plano.

    - ``kind``: validate | download | apply | wait | reboot.
    - ``risk``: low | medium | high.
    """
    kind: str = "apply"
    target: str = ""
    detail: str = ""
    requires_admin: bool = False
    risk: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": _norm(self.kind, "apply"),
            "target": _norm(self.target),
            "detail": _norm(self.detail),
            "requires_admin": bool(self.requires_admin),
            "risk": _norm(self.risk, "medium"),
        }


class Plan:
    """Coleção ordenada de ações a serem executadas."""

    def __init__(self, name: str = "plan",
                 policy: Optional[Policy] = None,
                 actions: Optional[List[PlanAction]] = None):
        self.name = name or "plan"
        self.policy = policy
        self.actions: List[PlanAction] = list(actions or [])

    def add(self, action: PlanAction, index: Optional[int] = None) -> None:
        """Adiciona uma ação (aceita ``PlanAction`` ou dict compatível)."""
        item = action
        if isinstance(action, dict):
            item = PlanAction(
                kind=str(action.get("kind", "apply")),
                target=str(action.get("target", "")),
                detail=str(action.get("detail", "")),
                requires_admin=bool(action.get("requires_admin", False)),
                risk=str(action.get("risk", "medium")),
            )
        if index is None:
            self.actions.append(item)
        else:
            self.actions.insert(max(0, index), item)

    def add_action(self, kind: str, target: str = "", detail: str = "",
                   requires_admin: bool = False, risk: str = "medium") -> PlanAction:
        a = PlanAction(kind=kind, target=target, detail=detail,
                       requires_admin=requires_admin, risk=risk)
        self.actions.append(a)
        return a

    def sort(self, key: Optional[Callable[[PlanAction], Any]] = None) -> "Plan":
        """Ordena por (tipo, risco); ``key`` personalizada é opcional."""
        if key is None:
            def default_key(a: PlanAction):
                kind_idx = KIND_ORDER.index(a.kind) if a.kind in KIND_ORDER else len(KIND_ORDER)
                risk_idx = RISK_ORDER.index(a.risk) if a.risk in RISK_ORDER else len(RISK_ORDER)
                return (kind_idx, risk_idx)
            self.actions.sort(key=default_key)
        else:
            self.actions.sort(key=key)
        return self

    def needs_admin(self) -> bool:
        """True se alguma ação exigir privilégios de administrador."""
        return any(getattr(a, "requires_admin", False) for a in self.actions)

    def count(self) -> int:
        return len(self.actions)

    def clear(self) -> None:
        self.actions = []

    def by_kind(self, kind: str) -> List[PlanAction]:
        return [a for a in self.actions if getattr(a, "kind", "") == kind]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "policy": self.policy.to_dict() if isinstance(self.policy, Policy) else None,
            "needs_admin": self.needs_admin(),
            "count": len(self.actions),
            "actions": [a.to_dict() if not isinstance(a, dict) else a for a in self.actions],
        }