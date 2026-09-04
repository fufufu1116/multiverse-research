#!/usr/bin/env python3
import pathlib
import tempfile
import threading
import time
import unittest

from orchestrator_mvp_v2 import OrchestratorError, operation_key
from orchestrator_role_relay_v3 import DurableFixtureReceiptStore, RelayStore
from orchestrator_role_relay_policy_v4 import (
    CandidateBindingPolicy,
    PolicyRelayRoleWorker,
    PolicyRelayStore,
    policy_fixture_process_one,
)

REPO = "fufufu1116/multiverse-research"
BRANCH_A = "agent/automation-policy-v4-fixture-a"
BRANCH_B = "agent/automation-policy-v4-fixture-b"


def policy(*bindings):
    return CandidateBindingPolicy.exact(REPO, *bindings)


def task(*, task_id="task-v4", domain="automation", branch=BRANCH_A,
         head="a" * 40, main="b" * 40):
    return {
        "task_id": task_id,
        "state": "IN_IMPLEMENT",
        "semantic_retry_count": 0,
        "transient_retry_count": 0,
        "spec": {
            "objective": "prove policy-bound generic candidate relay",
            "domain": domain,
            "canonical_repo": REPO,
            "candidate_head": head,
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


class PolicyRelayV4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.relay_db = self.root / "relay-v4.sqlite"
        self.receipt_db = self.root / "receipts.sqlite"
        self.policy = policy(("automation", BRANCH_A), ("automation", BRANCH_B))

    def tearDown(self):
        self.tmp.cleanup()

    def enqueue(self, t=None, *, role="IMPLEMENT", sem=1, trans=1):
        t = task() if t is None else t
        op = operation_key(t["task_id"], role, sem - 1)
        store = PolicyRelayStore(self.relay_db, self.policy)
        try:
            store.enqueue(role=role, task=t, operation_key_value=op,
                          semantic_attempt=sem, transient_attempt=trans)
        finally:
            store.close()
        return op

    def test_two_explicit_bindings_share_one_relay(self):
        op_a = self.enqueue(task_id := task(task_id="a", branch=BRANCH_A))
        op_b = self.enqueue(task(task_id="b", branch=BRANCH_B))
        self.assertNotEqual(op_a, op_b)
        store = PolicyRelayStore(self.relay_db, self.policy)
        try:
            self.assertEqual(store.job(op_a)["candidate_branch"], BRANCH_A)
            self.assertEqual(store.job(op_b)["candidate_branch"], BRANCH_B)
        finally:
            store.close()

    def test_cross_pair_and_unlisted_binding_are_denied(self):
        strict = policy(("automation", BRANCH_A), ("keirin", BRANCH_B))
        store = PolicyRelayStore(self.relay_db, strict)
        try:
            crossed = task(branch=BRANCH_B, domain="automation")
            op = operation_key(crossed["task_id"], "IMPLEMENT", 0)
            with self.assertRaisesRegex(OrchestratorError, "RELAY_BINDING_POLICY_DENIED"):
                store.enqueue(role="IMPLEMENT", task=crossed, operation_key_value=op,
                              semantic_attempt=1, transient_attempt=1)
            unknown = task(branch="agent/automation-policy-v4-unknown")
            op2 = operation_key(unknown["task_id"], "LAB", 0)
            with self.assertRaisesRegex(OrchestratorError, "RELAY_BINDING_POLICY_DENIED"):
                store.enqueue(role="LAB", task=unknown, operation_key_value=op2,
                              semantic_attempt=1, transient_attempt=1)
        finally:
            store.close()

    def test_policy_rejects_non_candidate_or_malformed_branches(self):
        for bad in ("main", "master", "state/multiverse-core-current", "research/keirin", "agent/a..b", "agent/a b"):
            with self.subTest(branch=bad):
                with self.assertRaisesRegex(OrchestratorError, "RELAY_POLICY_BRANCH_INVALID"):
                    policy(("automation", bad))

    def test_policy_is_db_pinned_and_v3_adapter_rejects_v4_db(self):
        store = PolicyRelayStore(self.relay_db, self.policy)
        fp = self.policy.fingerprint
        try:
            row = store.conn.execute("SELECT v FROM meta WHERE k='binding_policy_fingerprint'").fetchone()
            self.assertEqual(row[0], fp)
        finally:
            store.close()
        changed = policy(("automation", BRANCH_A))
        with self.assertRaisesRegex(OrchestratorError, "RELAY_POLICY_FINGERPRINT_MISMATCH"):
            PolicyRelayStore(self.relay_db, changed)
        with self.assertRaisesRegex(OrchestratorError, "RELAY_DB_SCHEMA_VERSION_MISMATCH"):
            RelayStore(self.relay_db)

    def test_replay_branch_head_and_main_conflicts_fail_closed(self):
        base = task(task_id="same")
        op = self.enqueue(base)
        variants = [
            task(task_id="same", branch=BRANCH_B),
            task(task_id="same", head="c" * 40),
            task(task_id="same", main="d" * 40),
        ]
        codes = ["RELAY_REPLAY_BRANCH_MISMATCH", "RELAY_REPLAY_HEAD_MISMATCH", "RELAY_REPLAY_MAIN_MISMATCH"]
        for changed, code in zip(variants, codes):
            store = PolicyRelayStore(self.relay_db, self.policy)
            try:
                with self.assertRaisesRegex(OrchestratorError, code):
                    store.enqueue(role="IMPLEMENT", task=changed, operation_key_value=op,
                                  semantic_attempt=1, transient_attempt=2)
            finally:
                store.close()

    def test_repo_spend_and_safety_authority_are_denied(self):
        cases = []
        wrong_repo = task(task_id="repo")
        wrong_repo["spec"]["canonical_repo"] = "other/repo"
        cases.append((wrong_repo, "RELAY_REPO_POLICY_DENIED"))
        spend = task(task_id="spend")
        spend["spec"]["budgets"]["cost_budget_microusd"] = 1
        cases.append((spend, "RELAY_SPEND_DENIED"))
        unsafe = task(task_id="unsafe")
        unsafe["spec"]["safety"]["authority_expansion"] = True
        cases.append((unsafe, "RELAY_SAFETY_FAIL_CLOSED:authority_expansion"))
        for item, code in cases:
            store = PolicyRelayStore(self.relay_db, self.policy)
            try:
                op = operation_key(item["task_id"], "IMPLEMENT", 0)
                with self.assertRaisesRegex(OrchestratorError, code):
                    store.enqueue(role="IMPLEMENT", task=item, operation_key_value=op,
                                  semantic_attempt=1, transient_attempt=1)
            finally:
                store.close()

    def test_review_head_binding_is_inherited(self):
        op = self.enqueue(task(task_id="lab"), role="LAB")
        store = PolicyRelayStore(self.relay_db, self.policy)
        try:
            job = store.claim_next(worker_id="lab")
            with self.assertRaisesRegex(OrchestratorError, "RELAY_LAB_HEAD_MISMATCH"):
                store.complete(op, job["claim_token"], {
                    "verdict": "PASS", "reviewed_head": "c" * 40, "evidence_ref": "lab"
                })
        finally:
            store.close()

    def test_crash_after_durable_receipt_replays_once_under_policy(self):
        t = task(task_id="crash")
        op = self.enqueue(t)
        script = {"IMPLEMENT": {"1": {
            "candidate_head": "a" * 40,
            "evidence_ref": "impl",
            "diff_lines": 1,
            "cost_microusd": 0,
        }}}
        first = policy_fixture_process_one(str(self.relay_db), str(self.receipt_db), self.policy,
                                           "w1", script, lease_seconds=1, crash_after_receipt=True)
        self.assertEqual(first, "CRASH_AFTER_RECEIPT")
        time.sleep(1.05)
        second = policy_fixture_process_one(str(self.relay_db), str(self.receipt_db), self.policy,
                                            "w2", script, lease_seconds=1)
        self.assertEqual(second, "COMPLETE")
        receipts = DurableFixtureReceiptStore(self.receipt_db)
        self.assertEqual(receipts.execution_count(op), 1)

    def test_policy_worker_survives_transport_delay(self):
        t = task(task_id="worker", branch=BRANCH_B)
        op = operation_key(t["task_id"], "IMPLEMENT", 0)
        worker = PolicyRelayRoleWorker(self.relay_db, self.policy, poll_seconds=0.01, result_wait_seconds=2.0)
        script = {"IMPLEMENT": {"1": {
            "candidate_head": "a" * 40,
            "evidence_ref": "impl",
            "diff_lines": 2,
            "cost_microusd": 0,
        }}}

        def agent():
            deadline = time.time() + 1
            while time.time() < deadline:
                try:
                    result = policy_fixture_process_one(str(self.relay_db), str(self.receipt_db), self.policy,
                                                        "agent", script)
                    if result == "COMPLETE":
                        return
                except Exception:
                    pass
                time.sleep(0.01)
            raise RuntimeError("agent timeout")

        th = threading.Thread(target=agent)
        th.start()
        out = worker.run(role="IMPLEMENT", task=t, operation_key=op,
                         semantic_attempt=1, transient_attempt=1)
        th.join()
        self.assertEqual(out["evidence_ref"], "impl")


if __name__ == "__main__":
    unittest.main()
