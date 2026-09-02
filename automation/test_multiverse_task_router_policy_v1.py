#!/usr/bin/env python3
from __future__ import annotations

import unittest

from multiverse_task_router_policy_v1 import transition
from multiverse_task_router_v1 import RouterError, new_task

BASE_AUTHORITY = {
    "candidate_scope_only": True,
    "no_production_or_stable_effect": True,
    "no_external_send": True,
    "no_spending": True,
    "no_secrets_or_writer_key": True,
    "no_protected_data_access": True,
    "no_irreversible_operation": True,
    "no_authority_expansion": True,
    "deterministic_testable": True,
}

KW = dict(
    objective="Review candidate",
    artifact_ref="comment:request",
    role_owner="CORE",
    allowed_read=["canonical repo"],
    forbidden_read=["secrets"],
    allowed_actions=["review"],
    forbidden_actions=["production mutation"],
    pass_criteria=["exact head"],
    fail_criteria=["head mismatch"],
    routing_contract={
        "lab_verdict_field": "LAB_EXAMPLE_VERDICT",
        "lab_head_field": "LAB_EXAMPLE_REVIEWED_HEAD",
        "auditor_verdict_field": "AUDITOR_EXAMPLE_VERDICT",
        "auditor_head_field": "AUDITOR_EXAMPLE_REVIEWED_HEAD",
    },
)


class PromotionPolicyTests(unittest.TestCase):
    def task(self, owner_gate: bool | None):
        authority = dict(BASE_AUTHORITY)
        if owner_gate is not None:
            authority["owner_gate_on_auditor_pass"] = owner_gate
        t = new_task(
            "task-policy-1",
            "fufufu1116/multiverse-research",
            "agent/example",
            "1" * 40,
            "LOW",
            authority,
            **KW,
        )
        t = transition(t, "CORE_READY")
        t = transition(t, "CORE_READY")
        t = transition(t, "MECHANICAL_PASS")
        t = transition(t, "LAB_PASS")
        return t

    def test_auditor_pass_owner_gate_when_prespecified(self):
        t = transition(self.task(True), "AUDITOR_PASS", "comment:audit")
        self.assertEqual((t["state"], t["next_role"]), ("OWNER_GATE", "OWNER"))

    def test_auditor_pass_done_when_prespecified(self):
        t = transition(self.task(False), "AUDITOR_PASS", "comment:audit")
        self.assertEqual((t["state"], t["next_role"]), ("DONE", "NONE"))

    def test_missing_promotion_policy_fails_closed(self):
        with self.assertRaises(RouterError):
            transition(self.task(None), "AUDITOR_PASS")


if __name__ == "__main__":
    unittest.main()
