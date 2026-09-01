#!/usr/bin/env python3
from __future__ import annotations

import unittest
from multiverse_task_router_v1 import MAX_REMEDIATION_RETRIES, RouterError, event_from_review, new_task, owner_free_remediation_allowed, routing_envelope, transition

SAFE = {
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

class RouterTests(unittest.TestCase):
    def task(self, authority=None):
        return new_task(
            "task-1", "fufufu1116/multiverse-research", "agent/example", "1"*40,
            "LOW", dict(SAFE if authority is None else authority), **KW
        )
    def to_lab(self,t):
        return transition(transition(transition(t,"CORE_READY"),"CORE_READY"),"MECHANICAL_PASS")
    def to_audit(self,t):
        return transition(self.to_lab(t),"LAB_PASS")

    def test_happy_path(self):
        t=self.to_audit(self.task())
        self.assertEqual(routing_envelope(t)["role"],"AUDITOR")
        t=transition(t,"AUDITOR_PASS")
        self.assertEqual(t["state"],"DONE")

    def test_exact_lab_result_parser(self):
        t=self.to_lab(self.task())
        body="`LAB_EXAMPLE_REVIEWED_HEAD: %s`\n`LAB_EXAMPLE_VERDICT: PASS`\n"%t["target_head"]
        self.assertEqual(event_from_review(t,"LAB",body),"LAB_PASS")

    def test_duplicate_verdict_denied(self):
        t=self.to_lab(self.task())
        body=("LAB_EXAMPLE_REVIEWED_HEAD: %s\nLAB_EXAMPLE_VERDICT: PASS\nLAB_EXAMPLE_VERDICT: PASS\n"%t["target_head"])
        with self.assertRaises(RouterError): event_from_review(t,"LAB",body)

    def test_head_mismatch_denied(self):
        t=self.to_lab(self.task())
        body="LAB_EXAMPLE_REVIEWED_HEAD: %s\nLAB_EXAMPLE_VERDICT: PASS\n"%("2"*40)
        with self.assertRaises(RouterError): event_from_review(t,"LAB",body)

    def test_lab_fix_routes_core_with_retry(self):
        t=transition(self.to_lab(self.task()),"LAB_FIX_REQUIRED","comment:1")
        self.assertEqual((t["state"],t["next_role"],t["retry_count"]),("LAB_FIX_REQUIRED","CORE",1))

    def test_auditor_fix_routes_core_with_retry(self):
        t=transition(self.to_audit(self.task()),"AUDITOR_FIX_REQUIRED")
        self.assertEqual((t["state"],t["retry_count"]),("AUDIT_FIX_REQUIRED",1))

    def test_risky_fix_routes_owner(self):
        unsafe=dict(SAFE);unsafe["no_authority_expansion"]=False
        t=transition(self.to_lab(self.task(unsafe)),"LAB_FIX_REQUIRED")
        self.assertEqual((t["state"],t["next_role"],t["retry_count"]),("OWNER_GATE","OWNER",0))

    def test_retry_ceiling_fail_closed(self):
        t=self.to_lab(self.task());t["retry_count"]=MAX_REMEDIATION_RETRIES
        t=transition(t,"LAB_FIX_REQUIRED")
        self.assertEqual(t["state"],"FAILED_CLOSED");self.assertTrue(t["fail_closed"])

    def test_invalid_transition_denied(self):
        with self.assertRaises(RouterError): transition(self.task(),"LAB_PASS")

    def test_owner_free_requires_all_gates(self):
        self.assertTrue(owner_free_remediation_allowed(SAFE))
        x=dict(SAFE);del x["deterministic_testable"]
        self.assertFalse(owner_free_remediation_allowed(x))

if __name__=="__main__": unittest.main()
