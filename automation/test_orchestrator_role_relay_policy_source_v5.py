#!/usr/bin/env python3
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import OrchestratorError, operation_key
from orchestrator_role_relay_policy_v4 import PolicyRelayStore
from orchestrator_role_relay_policy_source_v5 import (
    REVIEWED_POLICY_MANIFEST_SHA256,
    ReviewedPolicySource,
    SourceBoundPolicyRelayStore,
    source_fixture_process_one,
)

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"
MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
HEAD = "a" * 40


def task(task_id="v5", *, branch=BRANCH, domain="automation-v5", main=MAIN):
    return {
        "task_id": task_id,
        "state": "IN_IMPLEMENT",
        "semantic_retry_count": 0,
        "transient_retry_count": 0,
        "spec": {
            "objective": "prove exact reviewed policy source binding",
            "domain": domain,
            "canonical_repo": "fufufu1116/multiverse-research",
            "candidate_head": HEAD,
            "candidate_branch": branch,
            "canonical_main": main,
            "safety": {
                "candidate_only": True,
                "stable_production_effect": False,
                "secret_credential": False,
                "external_effect": False,
                "money_spend": False,
                "protected_data": False,
                "irreversible_operation": False,
                "authority_expansion": False,
                "unknown_risk": False,
            },
            "budgets": {"cost_budget_microusd": 0},
        },
    }


class PolicySourceV5Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.relay_db = self.root / "relay-v5.sqlite"
        self.receipt_db = self.root / "receipt.sqlite"
        self.source = ReviewedPolicySource.load(MANIFEST)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compiled_manifest_identity_loads_exact_source(self):
        self.assertEqual(self.source.raw_sha256, REVIEWED_POLICY_MANIFEST_SHA256)
        self.assertEqual(self.source.source_branch, BRANCH)
        self.assertEqual(self.source.canonical_main, MAIN)
        self.assertTrue(self.source.policy.allows("automation-v5", BRANCH))

    def test_tampered_manifest_and_symlink_are_denied(self):
        tampered = self.root / MANIFEST.name
        tampered.write_text(MANIFEST.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(OrchestratorError, "POLICY_SOURCE_SHA256_MISMATCH"):
            ReviewedPolicySource.load(tampered)
        link = self.root / "link" / MANIFEST.name
        link.parent.mkdir()
        link.symlink_to(MANIFEST)
        with self.assertRaisesRegex(OrchestratorError, "POLICY_SOURCE_FILE_CLASS"):
            ReviewedPolicySource.load(link)

    def test_runtime_task_cannot_select_policy_or_wrong_main(self):
        store = SourceBoundPolicyRelayStore(self.relay_db, self.source)
        try:
            wrong = task("wrong-branch", branch="agent/not-reviewed")
            op = operation_key(wrong["task_id"], "IMPLEMENT", 0)
            with self.assertRaisesRegex(OrchestratorError, "RELAY_BINDING_POLICY_DENIED"):
                store.enqueue(role="IMPLEMENT", task=wrong, operation_key_value=op,
                              semantic_attempt=1, transient_attempt=1)
            wrong_main = task("wrong-main", main="b" * 40)
            op2 = operation_key(wrong_main["task_id"], "IMPLEMENT", 0)
            with self.assertRaisesRegex(OrchestratorError, "POLICY_SOURCE_TASK_MAIN_MISMATCH"):
                store.enqueue(role="IMPLEMENT", task=wrong_main, operation_key_value=op2,
                              semantic_attempt=1, transient_attempt=1)
        finally:
            store.close()

    def test_source_and_policy_are_db_pinned_and_v4_adapter_rejects_v5_db(self):
        store = SourceBoundPolicyRelayStore(self.relay_db, self.source)
        try:
            got = dict(store.conn.execute(
                "SELECT k,v FROM meta WHERE k IN ('policy_source_sha256','binding_policy_fingerprint')"
            ).fetchall())
            self.assertEqual(got["policy_source_sha256"], self.source.raw_sha256)
            self.assertEqual(got["binding_policy_fingerprint"], self.source.policy.fingerprint)
        finally:
            store.close()
        with self.assertRaisesRegex(OrchestratorError, "POLICY_RELAY_DB_SCHEMA_VERSION_MISMATCH"):
            PolicyRelayStore(self.relay_db, self.source.policy)

    def test_partial_source_meta_fails_closed(self):
        store = SourceBoundPolicyRelayStore(self.relay_db, self.source)
        store.conn.execute("DELETE FROM meta WHERE k='policy_source_id'")
        store.conn.commit()
        store.close()
        with self.assertRaisesRegex(OrchestratorError, "POLICY_SOURCE_META_PARTIAL"):
            SourceBoundPolicyRelayStore(self.relay_db, self.source)

    def test_crash_after_receipt_reclaims_same_operation_once(self):
        t = task("crash")
        op = operation_key(t["task_id"], "IMPLEMENT", 0)
        store = SourceBoundPolicyRelayStore(self.relay_db, self.source)
        store.enqueue(role="IMPLEMENT", task=t, operation_key_value=op,
                      semantic_attempt=1, transient_attempt=1)
        store.close()
        script = {"IMPLEMENT": {"1": {
            "candidate_head": HEAD,
            "evidence_ref": "source-v5-impl",
            "diff_lines": 1,
            "cost_microusd": 0,
        }}}
        first = source_fixture_process_one(str(self.relay_db), str(self.receipt_db), str(MANIFEST),
                                           "w1", script, lease_seconds=1, crash_after_receipt=True)
        self.assertEqual(first, "CRASH_AFTER_RECEIPT")
        time.sleep(1.05)
        second = source_fixture_process_one(str(self.relay_db), str(self.receipt_db), str(MANIFEST),
                                            "w2", script, lease_seconds=1)
        self.assertEqual(second, "COMPLETE")
        from orchestrator_role_relay_v3 import DurableFixtureReceiptStore
        receipts = DurableFixtureReceiptStore(self.receipt_db)
        self.assertEqual(receipts.execution_count(op), 1)


if __name__ == "__main__":
    unittest.main()
