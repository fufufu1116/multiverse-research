#!/usr/bin/env python3
import pathlib
import tempfile
import threading
import time
import unittest

from orchestrator_mvp_v2 import OrchestratorError, operation_key
from orchestrator_role_relay_v3 import (
    CANDIDATE_BRANCH,
    DurableFixtureReceiptStore,
    RelayRoleWorker,
    RelayStore,
    fixture_process_one,
)


def task(head="a"*40, main="b"*40, task_id="task-v3"):
    return {
        "task_id": task_id,
        "state": "IN_IMPLEMENT",
        "semantic_retry_count": 0,
        "transient_retry_count": 0,
        "spec": {
            "objective": "prove durable role relay",
            "candidate_head": head,
            "candidate_branch": CANDIDATE_BRANCH,
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


class RelayV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.relay_db = self.root / "relay.sqlite"
        self.receipt_db = self.root / "receipts.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def enqueue(self, role="IMPLEMENT", sem=1, trans=1, t=None):
        t = task() if t is None else t
        op = operation_key(t["task_id"], role, sem - 1)
        s = RelayStore(self.relay_db)
        try:
            s.enqueue(role=role, task=t, operation_key_value=op, semantic_attempt=sem, transient_attempt=trans)
        finally:
            s.close()
        return op

    def test_enqueue_replay_is_idempotent(self):
        op = self.enqueue()
        self.enqueue(trans=2)
        s = RelayStore(self.relay_db)
        try:
            row = s.conn.execute("SELECT count(*) FROM jobs WHERE operation_key=?", (op,)).fetchone()
            self.assertEqual(row[0], 1)
            self.assertEqual(s.job(op)["status"], "QUEUED")
        finally:
            s.close()

    def test_lease_expiry_requeues_without_new_operation(self):
        op = self.enqueue()
        s = RelayStore(self.relay_db)
        try:
            j1 = s.claim_next(worker_id="w1", lease_seconds=1)
            self.assertEqual(j1["operation_key"], op)
            recovered = s.recover_expired(at=time.time() + 2)
            self.assertEqual(recovered, [op])
            j2 = s.claim_next(worker_id="w2", lease_seconds=1)
            self.assertEqual(j2["operation_key"], op)
            self.assertNotEqual(j1["claim_token"], j2["claim_token"])
        finally:
            s.close()

    def test_recover_expired_serializes_heartbeat_after_validation(self):
        op = self.enqueue()
        s = RelayStore(self.relay_db)
        try:
            j1 = s.claim_next(worker_id="w1", lease_seconds=1)
        finally:
            s.close()

        selected = threading.Event()
        release = threading.Event()
        recovered = []
        recovery_errors = []
        heartbeat_errors = []

        def recoverer():
            store = RelayStore(self.relay_db)
            try:
                def trace(sql):
                    if sql.startswith("SELECT operation_key,claim_token FROM jobs"):
                        selected.set()
                        release.wait(2)
                store.conn.set_trace_callback(trace)
                recovered.extend(store.recover_expired(at=time.time() + 5))
            except Exception as exc:
                recovery_errors.append(exc)
            finally:
                store.close()

        def heartbeater():
            store = RelayStore(self.relay_db)
            try:
                store.heartbeat(op, j1["claim_token"], lease_seconds=30)
            except Exception as exc:
                heartbeat_errors.append(exc)
            finally:
                store.close()

        rt = threading.Thread(target=recoverer)
        rt.start()
        self.assertTrue(selected.wait(2))
        ht = threading.Thread(target=heartbeater)
        ht.start()
        time.sleep(0.1)
        self.assertTrue(ht.is_alive(), "heartbeat must block behind recovery writer transaction")
        release.set()
        rt.join(2)
        ht.join(2)
        self.assertFalse(rt.is_alive())
        self.assertFalse(ht.is_alive())
        self.assertEqual(recovery_errors, [])
        self.assertEqual(recovered, [op])
        self.assertEqual(len(heartbeat_errors), 1)
        self.assertIsInstance(heartbeat_errors[0], OrchestratorError)
        check = RelayStore(self.relay_db)
        try:
            self.assertEqual(check.job(op)["status"], "QUEUED")
        finally:
            check.close()

    def test_complete_validation_and_update_are_one_writer_transaction(self):
        op = self.enqueue()
        s = RelayStore(self.relay_db)
        try:
            j1 = s.claim_next(worker_id="w1", lease_seconds=1)
        finally:
            s.close()
        good = {"candidate_head": "a"*40, "evidence_ref": "impl-evidence", "diff_lines": 1, "cost_microusd": 0}

        selected = threading.Event()
        release = threading.Event()
        complete_errors = []
        recovery_errors = []
        recovered = []

        def completer():
            store = RelayStore(self.relay_db)
            try:
                def trace(sql):
                    if sql.startswith("SELECT * FROM jobs WHERE operation_key="):
                        selected.set()
                        release.wait(2)
                store.conn.set_trace_callback(trace)
                store.complete(op, j1["claim_token"], good)
            except Exception as exc:
                complete_errors.append(exc)
            finally:
                store.close()

        def recoverer():
            store = RelayStore(self.relay_db)
            try:
                recovered.extend(store.recover_expired(at=time.time() + 120))
            except Exception as exc:
                recovery_errors.append(exc)
            finally:
                store.close()

        ct = threading.Thread(target=completer)
        ct.start()
        self.assertTrue(selected.wait(2))
        rt = threading.Thread(target=recoverer)
        rt.start()
        time.sleep(0.1)
        self.assertTrue(rt.is_alive(), "recovery must block after completion has validated ownership")
        release.set()
        ct.join(2)
        rt.join(2)
        self.assertFalse(ct.is_alive())
        self.assertFalse(rt.is_alive())
        self.assertEqual(complete_errors, [])
        self.assertEqual(recovery_errors, [])
        self.assertEqual(recovered, [])
        check = RelayStore(self.relay_db)
        try:
            self.assertEqual(check.job(op)["status"], "COMPLETE")
            self.assertEqual(check.result(op), good)
        finally:
            check.close()

    def test_conflicting_duplicate_result_is_denied(self):
        op = self.enqueue()
        s = RelayStore(self.relay_db)
        try:
            j = s.claim_next(worker_id="w1")
            good = {"candidate_head": "a"*40, "evidence_ref": "impl-evidence", "diff_lines": 1, "cost_microusd": 0}
            s.complete(op, j["claim_token"], good)
            s.complete(op, j["claim_token"], dict(good))
            with self.assertRaises(OrchestratorError):
                s.complete(op, j["claim_token"], {**good, "diff_lines": 2})
        finally:
            s.close()

    def test_review_head_mismatch_is_denied(self):
        op = self.enqueue(role="LAB")
        s = RelayStore(self.relay_db)
        try:
            j = s.claim_next(worker_id="lab")
            with self.assertRaises(OrchestratorError):
                s.complete(op, j["claim_token"], {"verdict": "PASS", "reviewed_head": "c"*40, "evidence_ref": "lab"})
        finally:
            s.close()

    def test_spend_or_external_authority_is_denied(self):
        t = task()
        t["spec"]["safety"]["money_spend"] = True
        op = operation_key(t["task_id"], "IMPLEMENT", 0)
        s = RelayStore(self.relay_db)
        try:
            with self.assertRaises(OrchestratorError):
                s.enqueue(role="IMPLEMENT", task=t, operation_key_value=op, semantic_attempt=1, transient_attempt=1)
        finally:
            s.close()

    def test_candidate_branch_mismatch_is_denied(self):
        t = task()
        t["spec"]["candidate_branch"] = "wrong/branch"
        op = operation_key(t["task_id"], "IMPLEMENT", 0)
        s = RelayStore(self.relay_db)
        try:
            with self.assertRaises(OrchestratorError):
                s.enqueue(role="IMPLEMENT", task=t, operation_key_value=op, semantic_attempt=1, transient_attempt=1)
        finally:
            s.close()

    def test_heartbeat_extends_claim_lease_and_stale_claim_cannot_complete(self):
        op = self.enqueue()
        s = RelayStore(self.relay_db)
        try:
            j1 = s.claim_next(worker_id="w1", lease_seconds=1)
            s.heartbeat(op, j1["claim_token"], lease_seconds=2)
            self.assertEqual(s.recover_expired(at=time.time() + 1.2), [])
            self.assertEqual(s.recover_expired(at=time.time() + 3.0), [op])
            j2 = s.claim_next(worker_id="w2", lease_seconds=1)
            good = {"candidate_head": "a"*40, "evidence_ref": "impl-evidence", "diff_lines": 1, "cost_microusd": 0}
            with self.assertRaises(OrchestratorError):
                s.complete(op, j1["claim_token"], good)
            s.complete(op, j2["claim_token"], good)
        finally:
            s.close()

    def test_crash_after_fixture_receipt_replays_provider_once(self):
        op = self.enqueue()
        script = {"IMPLEMENT": {"1": {"candidate_head": "a"*40, "evidence_ref": "impl", "diff_lines": 1, "cost_microusd": 0}}}
        first = fixture_process_one(str(self.relay_db), str(self.receipt_db), "w1", script, lease_seconds=1, crash_after_receipt=True)
        self.assertEqual(first, "CRASH_AFTER_RECEIPT")
        time.sleep(1.05)
        second = fixture_process_one(str(self.relay_db), str(self.receipt_db), "w2", script, lease_seconds=1)
        self.assertEqual(second, "COMPLETE")
        receipts = DurableFixtureReceiptStore(self.receipt_db)
        self.assertEqual(receipts.execution_count(op), 1)
        s = RelayStore(self.relay_db)
        try:
            self.assertIsNotNone(s.result(op))
        finally:
            s.close()

    def test_relay_role_worker_survives_transport_delay(self):
        t = task()
        op = operation_key(t["task_id"], "IMPLEMENT", 0)
        worker = RelayRoleWorker(self.relay_db, poll_seconds=0.01, result_wait_seconds=2.0)
        script = {"IMPLEMENT": {"1": {"candidate_head": "a"*40, "evidence_ref": "impl", "diff_lines": 2, "cost_microusd": 0}}}

        def agent():
            deadline = time.time() + 1
            while time.time() < deadline:
                try:
                    result = fixture_process_one(str(self.relay_db), str(self.receipt_db), "agent", script)
                    if result == "COMPLETE":
                        return
                except Exception:
                    pass
                time.sleep(0.01)
            raise RuntimeError("agent timeout")

        th = threading.Thread(target=agent)
        th.start()
        out = worker.run(role="IMPLEMENT", task=t, operation_key=op, semantic_attempt=1, transient_attempt=1)
        th.join()
        self.assertEqual(out["evidence_ref"], "impl")

if __name__ == "__main__":
    unittest.main()
