# -*- coding: utf-8 -*-
from __future__ import annotations

"""Testes do planejamento: Policy/PlanAction/Plan, risco, políticas padrão e
agendamento (next_run/due com datetimes fixos). Sem admin e sem rede.
"""

import unittest

from driverhub.core.plan import base as plan_base
from driverhub.core.plan import maintenance
from driverhub.core.plan import policies
from driverhub.core.plan import risk
from driverhub.core.plan import schedule
from driverhub.core.plan.base import Plan, PlanAction, Policy


class PolicyTest(unittest.TestCase):
    def test_default_policy(self):
        policy = policies.default_policy()
        self.assertEqual(policy.name, "default")
        self.assertTrue(policy.reboot)
        self.assertEqual(policy.priority, "medium")
        self.assertFalse(policy.strict)
        self.assertEqual(list(policy.categories), [])

    def test_allows_everything_with_no_restrictions(self):
        policy = Policy()
        self.assertTrue(policy.allows("gpu"))
        self.assertTrue(policy.allows("", "qualquer-coisa"))

    def test_allows_respects_categories(self):
        policy = Policy(categories=["gpu", "network"])
        self.assertTrue(policy.allows("gpu"))
        self.assertTrue(policy.allows("network"))
        self.assertFalse(policy.allows("audio"))

    def test_allows_respects_blacklist(self):
        policy = Policy(blacklist=["beta", "preview"])
        self.assertFalse(policy.allows("", "driver-beta"))
        self.assertFalse(policy.allows("", "build-preview-3"))
        self.assertTrue(policy.allows("", "driver-stable"))

    def test_to_dict(self):
        policy = Policy(name="x", strict=True, categories=["gpu"], dry_run=True)
        data = policy.to_dict()
        self.assertEqual(data["name"], "x")
        self.assertTrue(data["strict"])
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["categories"], ["gpu"])

    def test_policy_from_config_dict(self):
        policy = policies.policy_from_config({})
        self.assertEqual(policy.name, "config")
        self.assertTrue(policy.strict)
        self.assertTrue(policy.dry_run)
        self.assertTrue(policy.reboot)

    def test_quiet_and_conservative(self):
        self.assertTrue(policies.quiet_policy().dry_run)
        self.assertFalse(policies.quiet_policy().reboot)
        self.assertTrue(policies.conservative_policy().strict)
        self.assertIn("critical", policies.conservative_policy().categories)


class RiskTest(unittest.TestCase):
    def test_risk_level_critical_official_low(self):
        self.assertEqual(risk.risk_level({"category": "critical", "official": True}), "low")

    def test_risk_level_official_signed_low(self):
        self.assertEqual(risk.risk_level({"official": True, "signed": True}), "low")

    def test_risk_level_official_medium(self):
        self.assertEqual(risk.risk_level({"official": True}), "medium")

    def test_risk_level_dry_run_medium(self):
        self.assertEqual(risk.risk_level({"dry_run": True}), "medium")

    def test_risk_level_bare_high(self):
        self.assertEqual(risk.risk_level({}), "high")
        self.assertEqual(risk.risk_level({"category": "gpu"}), "high")

    def test_risk_level_plan_action_high(self):
        self.assertEqual(risk.risk_level(PlanAction()), "high")

    def test_risk_level_never_raises(self):
        self.assertEqual(risk.risk_level(None), "high")

    def test_categorize(self):
        self.assertEqual(risk.categorize("Placa de Vídeo NVIDIA GeForce"), "graphics")
        self.assertEqual(risk.categorize("Adaptador de Rede Wi-Fi"), "network")
        self.assertEqual(risk.categorize("Driver de impressora"), "printer")

    def test_explain(self):
        self.assertTrue(risk.explain("low").startswith("Risco baixo"))
        self.assertTrue(risk.explain("high").startswith("Risco alto"))
        self.assertTrue(risk.explain("medium").startswith("Risco médio"))


class PlanTest(unittest.TestCase):
    def test_add_and_count(self):
        plan = Plan(name="p1", policy=Policy())
        plan.add_action("apply", target="oem.inf", risk="medium")
        plan.add({"kind": "download", "target": "https://www.nvidia.com/x"})
        self.assertEqual(plan.count(), 2)
        self.assertIsInstance(plan.actions[0], PlanAction)

    def test_sort_orders_by_kind(self):
        plan = Plan()
        plan.add_action("reboot")
        plan.add_action("apply", target="oem.inf")
        plan.sort()
        self.assertEqual([a.kind for a in plan.actions], ["apply", "reboot"])

    def test_needs_admin(self):
        plan = Plan()
        self.assertFalse(plan.needs_admin())
        plan.add_action("apply", target="oem.inf", requires_admin=True)
        self.assertTrue(plan.needs_admin())

    def test_by_kind(self):
        plan = Plan()
        plan.add_action("apply", target="a.inf")
        plan.add_action("download")
        self.assertEqual(len(plan.by_kind("apply")), 1)
        self.assertEqual(len(plan.by_kind("reboot")), 0)

    def test_to_dict(self):
        plan = Plan(name="p", policy=Policy(name="default", reboot=True))
        plan.add_action("apply", target="oem.inf", requires_admin=True)
        data = plan.to_dict()
        self.assertEqual(data["name"], "p")
        self.assertTrue(data["needs_admin"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["actions"][0]["kind"], "apply")
        self.assertEqual(data["policy"]["reboot"], True)

    def test_plan_action_to_dict(self):
        action = PlanAction(kind="apply", target="oem.inf", detail="detalhe")
        data = action.to_dict()
        self.assertEqual(data["kind"], "apply")
        self.assertEqual(data["target"], "oem.inf")
        self.assertEqual(data["risk"], "medium")


class ScheduleTest(unittest.TestCase):
    """next_run/due com datetimes fixos (100% determinístico)."""

    def test_next_run_at_time_later_today(self):
        item = schedule.Schedule(name="scan", interval_h=24, at="08:30", last_run=None)
        self.assertEqual(schedule.next_run(item, "2026-01-01T07:00"), "2026-01-01T08:30")

    def test_next_run_after_at_time_rolls_to_tomorrow(self):
        item = schedule.Schedule(name="scan", interval_h=24, at="08:30", last_run=None)
        self.assertEqual(schedule.next_run(item, "2026-01-01T09:00"), "2026-01-02T09:00")

    def test_next_run_from_last_run(self):
        item = schedule.Schedule(name="check", interval_h=24, at="08:30", last_run="2026-01-01T08:30")
        self.assertEqual(schedule.next_run(item, "2026-01-01T09:00"), "2026-01-02T08:30")

    def test_due_at_time(self):
        item = schedule.Schedule(name="scan", interval_h=24, at="08:30", last_run=None)
        self.assertFalse(schedule.due(item, "2026-01-01T07:00"))
        self.assertTrue(schedule.due(item, "2026-01-01T09:00"))

    def test_due_from_last_run(self):
        item = schedule.Schedule(name="check", interval_h=24, at="08:30", last_run="2026-01-01T08:30")
        self.assertFalse(schedule.due(item, "2026-01-02T08:29"))
        self.assertTrue(schedule.due(item, "2026-01-02T08:30"))

    def test_due_disabled_never(self):
        item = schedule.Schedule(name="parada", interval_h=1, at="00:00", enabled=False)
        self.assertFalse(schedule.due(item, "2099-01-01T00:00"))

    def test_scheduler_view(self):
        rows = schedule.scheduler_view([schedule.Schedule(name="scan", interval_h=24, at="08:30")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "scan")
        self.assertIn("next_run", rows[0])
        self.assertIn("status", rows[0])

    def test_save_and_load_schedules(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "schedules.json")
            result = schedule.save_schedules(
                [schedule.Schedule(name="scan", interval_h=24)], path)
            self.assertTrue(result["ok"])
            loaded = schedule.load_schedules(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].name, "scan")


class MaintenanceTest(unittest.TestCase):
    def test_every_seconds(self):
        self.assertEqual(maintenance.every(24)["seconds"], 86400)
        self.assertEqual(maintenance.every(0.5)["seconds"], 1800)

    def test_maintenance_schedule_fixed_base(self):
        rows = maintenance.maintenance_schedule(base="2026-01-01T00:00")
        self.assertTrue(any(r["task"] == "scan" for r in rows))
        self.assertTrue(any(r["task"] == "backup" for r in rows))
        for row in rows:
            self.assertIn("next", row)
            self.assertFalse(row["due"])


if __name__ == "__main__":
    unittest.main()