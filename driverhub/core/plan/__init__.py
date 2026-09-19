# -*- coding: utf-8 -*-
"""Planejamento, políticas e agendamento do DriverHub."""
from __future__ import annotations

from typing import Any, List, Optional

from .base import Plan, PlanAction, Policy
from . import maintenance, policies, risk, schedule, upgrade

__all__ = ["Policy", "Plan", "PlanAction", "create_plan", "build_plan",
           "maintenance", "policies", "risk", "schedule", "upgrade"]


def create_plan(policy: Optional[Policy] = None,
                actions: Optional[List[PlanAction]] = None,
                name: str = "plan") -> Plan:
    """Cria um ``Plan`` a partir de uma política e de uma lista de ações."""
    try:
        if policy is None:
            from .policies import default_policy
            policy = default_policy()
        return Plan(name=name or "plan", policy=policy, actions=list(actions or []))
    except Exception:
        return Plan(name="plan", policy=None)


def build_plan(drivers: Optional[list] = None,
               policy: Optional[Policy] = None) -> Plan:
    """Monta o plano de execução para uma lista de drivers (dicts).

    Delega ao módulo de upgrade; nunca lança exceção e nunca acessa fontes
    externas — apenas organiza os drivers recebidos de acordo com a política.
    """
    from .upgrade import upgrade_plan
    try:
        return upgrade_plan(list(drivers or []), policy)
    except Exception:
        return Plan(name="build-error", policy=policy)