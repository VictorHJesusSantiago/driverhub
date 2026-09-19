# -*- coding: utf-8 -*-
"""Plano de upgrade de drivers (e de atualização do sistema).

``upgrade_plan`` separa as ações em ``apply`` (aplicar), ``wait`` (aguardar) e
``reboot`` (reiniciar). ``plan_steps`` humaniza o plano e ``estimate`` estima
tempo/impacto. Nenhuma função aqui lança exceções.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _policy_of(policy: Any) -> Any:
    from .base import Policy
    if isinstance(policy, Policy) and policy is not None:
        return policy
    from .policies import default_policy
    try:
        return default_policy()
    except Exception:
        return None


def _actions_of(plan: Any, policy_from_plan: bool = False) -> tuple:
    """Extrai (actions, policy) de um Plan, dict, lista ou objeto genérico."""
    from .base import Plan
    if isinstance(plan, Plan):
        return (list(plan.actions), plan.policy if policy_from_plan else None)
    if isinstance(plan, dict):
        return (list(plan.get("actions", [])), plan.get("policy") if policy_from_plan else None)
    if isinstance(plan, (list, tuple)):
        return (list(plan), None)
    try:
        items = list(plan)
        return (items, None)
    except Exception:
        return ([], None)


def upgrade_plan(drivers: Any = None, policy: Any = None) -> Any:
    """Constrói o plano completo: separando apply, wait e reboot.

    Cada driver (dict) é avaliado contra a política; só entram no plano os que
    a política permite. Nunca lança exceção.
    """
    from .base import Plan, PlanAction
    from .risk import categorize, risk_level
    try:
        pol = _policy_of(policy)
        plan = Plan(name=f"{pol.name}-upgrade" if pol else "upgrade", policy=pol)
        items = list(drivers or [])
        applied = 0
        for d in items:
            if not isinstance(d, dict):
                d = {"name": str(d)}
            name = str(d.get("name") or d.get("target") or d.get("display") or "Driver")
            detail = str(d.get("detail") or "")
            category = str(d.get("category") or "")
            if not category:
                category = categorize(detail or name)
            if pol is not None:
                try:
                    if not pol.allows(category=category, target=name):
                        continue
                except Exception:
                    pass
            risk = risk_level(dict(d, dry_run=getattr(pol, "dry_run", False)))
            plan.add(PlanAction(
                kind="apply",
                target=name,
                detail=(detail or f"Atualizar driver da categoria {category or 'outros'}"),
                requires_admin=True,
                risk=risk,
            ))
            applied += 1
        if applied:
            plan.add(PlanAction(
                kind="wait",
                target="sistema",
                detail="Aguardar o SO concluir a aplicação dos drivers antes de reiniciar",
                requires_admin=False,
                risk="low",
            ))
            reboot_ok = bool(getattr(pol, "reboot", True))
            if reboot_ok:
                plan.add(PlanAction(
                    kind="reboot",
                    target="sistema",
                    detail="Reinicialização necessária para concluir as atualizações",
                    requires_admin=True,
                    risk="high",
                ))
        plan.sort()
        return plan
    except Exception:
        return Plan(name="upgrade-error", policy=pol)


def plan_steps(plan: Any) -> List[str]:
    """Lista de passos humanizados (pt-BR) a partir de um plano."""
    risk_label = {"low": "baixo", "medium": "médio", "high": "alto"}
    kind_label = {"validate": "Validar", "download": "Baixar", "apply": "Aplicar",
                  "wait": "Aguardar", "reboot": "Reiniciar"}
    try:
        actions, _ = _actions_of(plan)
        steps: List[str] = []
        for i, a in enumerate(actions, start=1):
            if isinstance(a, dict):
                kind = str(a.get("kind", "apply"))
                target = str(a.get("target", ""))
                detail = str(a.get("detail", ""))
                risk = str(a.get("risk", "medium"))
            else:
                kind = str(getattr(a, "kind", "apply"))
                target = str(getattr(a, "target", ""))
                detail = str(getattr(a, "detail", ""))
                risk = str(getattr(a, "risk", "medium"))
            verb = kind_label.get(kind, "Executar")
            rk = risk_label.get(risk, risk)
            if target and detail and target != detail:
                steps.append(f"{i}. {verb} {target} — {detail} (risco {rk})")
            elif target:
                steps.append(f"{i}. {verb} {target} (risco {rk})")
            else:
                steps.append(f"{i}. {verb} — {detail or 'passo de execução'} (risco {rk})")
        return steps
    except Exception:
        return []


def estimate(plan: Any) -> Dict[str, Any]:
    """Estimativa de tempo e impacto do plano (dict, nunca lança)."""
    try:
        actions, policy = _actions_of(plan, policy_from_plan=True)

        def _kind(a: Any) -> str:
            return str(a.get("kind", "") if isinstance(a, dict) else getattr(a, "kind", ""))

        applies = [a for a in actions if _kind(a) == "apply"]
        downloads = [a for a in actions if _kind(a) == "download"]
        reboot = any(_kind(a) == "reboot" for a in actions)
        dry = bool(getattr(policy, "dry_run", False)) if policy is not None else False
        minutes = int(max(1, len(applies)) * (1.0 if dry else 6.0)) if applies else 0
        detail = f"~{minutes} min para {len(applies)} aplicação(ões)"
        if reboot:
            detail += " e reinicialização ao final"
        if dry:
            detail += " (modo simulação — nada será alterado)"
        return {
            "steps": len(actions),
            "applies": len(applies),
            "downloads": len(downloads),
            "reboot": bool(reboot),
            "dry_run": bool(dry),
            "install_time_min": minutes,
            "detail": detail,
        }
    except Exception:
        return {"steps": 0, "applies": 0, "downloads": 0, "reboot": False,
                "dry_run": False, "install_time_min": 0, "detail": "Sem dados para estimar."}