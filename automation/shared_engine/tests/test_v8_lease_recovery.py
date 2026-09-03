import os
import sqlite3
import tempfile
import threading
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding
from orchestrator_provider_adapter_v7 import ProviderAdapterManifest, ProviderAdapterReceiptStore
from exact_v7_shared_engine import V7_MANIFEST

HEAD = "6" * 40
BRANCH = "agent/automation-shared-engine-integration-v8-candidate-20260903-v1"


class V8LeaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()
        self.binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
        self.provider_db = os.path.join(self.tmp.name, "provider.db")
        self.engine = ExactV7SharedEngine(
            self.binding,
            os.path.join(self.tmp.name, "bridge.db"),
            self.provider_db,
        )

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def _expire_lease(self, task_id):
        conn = sqlite3.connect(config.DB_PATH)
        try:
            conn.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    def _provider_execution_count(self, operation_key):
        manifest = ProviderAdapterManifest.load(V7_MANIFEST)
        store = ProviderAdapterReceiptStore(self.provider_db, manifest)
        try:
            return store.execution_count(operation_key)
        finally:
            store.close()

    def test_expired_active_task_can_be_reclaimed_with_generation_bump(self):
        task_id = self.engine.submit("core", "implement", "recover me")
        gen1 = self.engine.claim_and_start(task_id, "worker-1")
        self._expire_lease(task_id)

        gen2 = self.engine.reclaim_expired(task_id, "worker-2")
        task = db.get_task(task_id)
        self.assertEqual(task["state"], "IN_IMPLEMENT")
        self.assertEqual(task["claimed_by"], "worker-2")
        self.assertEqual(gen2, gen1 + 1)
        self.assertEqual(task["claim_generation"], gen2)

    def test_nonexpired_active_task_cannot_be_stolen(self):
        task_id = self.engine.submit("core", "implement", "do not steal")
        self.engine.claim_and_start(task_id, "worker-1")
        with self.assertRaises(db.LostLeaseError):
            self.engine.reclaim_expired(task_id, "worker-2")
        self.assertEqual(db.get_task(task_id)["claimed_by"], "worker-1")

    def test_terminal_or_pending_task_cannot_use_active_reclaim(self):
        pending = self.engine.submit("core", "implement", "pending")
        with self.assertRaisesRegex(db.InvalidTransitionError, "RECLAIM_STATE:PENDING"):
            self.engine.reclaim_expired(pending, "worker-2")

    def test_expired_worker_is_fenced_before_provider_execution_even_without_reclaim(self):
        task_id = self.engine.submit("core", "implement", "expired worker")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        self._expire_lease(task_id)
        op = "expired-before-provider"
        result = {
            "status": "READY",
            "candidate_head": HEAD,
            "diff_lines": 1,
            "cost_microusd": 0,
            "evidence_ref": "expired-before-provider-e",
        }

        with self.assertRaisesRegex(db.LostLeaseError, "task lease expired"):
            self.engine.execute_role(task_id, "IMPLEMENT", 0, op, "worker-1", gen, result)

        self.assertEqual(db.get_task(task_id)["state"], "IN_IMPLEMENT")
        self.assertEqual(self._provider_execution_count(op), 0)

    def test_concurrent_double_reclaim_has_exactly_one_winner(self):
        task_id = self.engine.submit("core", "implement", "double reclaim")
        gen1 = self.engine.claim_and_start(task_id, "worker-1")
        self._expire_lease(task_id)
        barrier = threading.Barrier(2)
        successes = []
        errors = []

        def contender(worker_id):
            try:
                barrier.wait()
                successes.append((worker_id, self.engine.reclaim_expired(task_id, worker_id)))
            except BaseException as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=contender, args=("worker-2",)),
            threading.Thread(target=contender, args=("worker-3",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], db.LostLeaseError)
        winner, gen2 = successes[0]
        task = db.get_task(task_id)
        self.assertEqual(gen2, gen1 + 1)
        self.assertEqual(task["claim_generation"], gen1 + 1)
        self.assertEqual(task["claimed_by"], winner)

    def test_stale_worker_receipt_is_fenced_then_new_worker_reuses_it_once(self):
        task_id = self.engine.submit("core", "implement", "receipt recovery")
        gen1 = self.engine.claim_and_start(task_id, "worker-1")
        self._expire_lease(task_id)
        gen2 = self.engine.reclaim_expired(task_id, "worker-2")

        result = {
            "status": "READY",
            "candidate_head": HEAD,
            "diff_lines": 1,
            "cost_microusd": 0,
            "evidence_ref": "lease-recovery-implement",
        }
        op = "lease-recovery-op"

        with self.assertRaises(db.LostLeaseError):
            self.engine.execute_role(task_id, "IMPLEMENT", 0, op, "worker-1", gen1, result)
        self.assertEqual(db.get_task(task_id)["state"], "IN_IMPLEMENT")

        state = self.engine.execute_role(task_id, "IMPLEMENT", 0, op, "worker-2", gen2, result)
        self.assertEqual(state, "IN_LAB")
        self.assertEqual(self._provider_execution_count(op), 1)

    def test_fix_required_crash_can_reclaim_and_resume_without_owner_gate(self):
        task_id = self.engine.submit("core", "implement", "fix crash")
        gen1 = self.engine.claim_and_start(task_id, "worker-1")
        head = self.binding.candidate_head

        self.engine.execute_role(task_id, "IMPLEMENT", 0, "fix-crash-impl-0", "worker-1", gen1, {
            "status": "READY", "candidate_head": head, "diff_lines": 1,
            "cost_microusd": 0, "evidence_ref": "fix-crash-impl-0-e",
        })
        self.engine.execute_role(task_id, "LAB", 0, "fix-crash-lab-fix", "worker-1", gen1, {
            "verdict": "FIX_REQUIRED", "reviewed_head": head, "evidence_ref": "fix-crash-lab-fix-e",
            "code": "L-CRASH", "detail": "repair after worker death",
        })
        self.assertEqual(db.get_task(task_id)["state"], "LAB_FIX_REQUIRED")

        self._expire_lease(task_id)
        with self.assertRaisesRegex(db.LostLeaseError, "task lease expired"):
            db.transition(task_id, "IN_IMPLEMENT", actor="dead-worker", event_type="AUTO_REMEDIATE", fencing=("worker-1", gen1))

        gen2 = self.engine.reclaim_expired(task_id, "worker-2")
        db.transition(task_id, "IN_IMPLEMENT", actor="auto_remediator", event_type="AUTO_REMEDIATE", fencing=("worker-2", gen2))
        self.engine.execute_role(task_id, "IMPLEMENT", 1, "fix-crash-impl-1", "worker-2", gen2, {
            "status": "READY", "candidate_head": head, "diff_lines": 1,
            "cost_microusd": 0, "evidence_ref": "fix-crash-impl-1-e",
        })
        self.engine.execute_role(task_id, "LAB", 1, "fix-crash-lab-pass", "worker-2", gen2, {
            "verdict": "PASS", "reviewed_head": head, "evidence_ref": "fix-crash-lab-pass-e",
        })
        self.engine.execute_role(task_id, "AUDIT", 0, "fix-crash-audit-pass", "worker-2", gen2, {
            "verdict": "PASS", "reviewed_head": head, "evidence_ref": "fix-crash-audit-pass-e",
        })
        self.assertEqual(db.get_task(task_id)["state"], "DONE")

        conn = sqlite3.connect(config.DB_PATH)
        try:
            owner_gate_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND (before_state='OWNER_GATE' OR after_state='OWNER_GATE')",
                (task_id,),
            ).fetchone()[0]
            reclaim_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND event_type='LEASE_RECLAIMED'",
                (task_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(owner_gate_events, 0)
        self.assertEqual(reclaim_events, 1)

    def test_lab_and_audit_fix_required_can_reenter_implementation_without_owner_gate(self):
        task_id = self.engine.submit("core", "implement", "auto remediate")
        gen = self.engine.claim_and_start(task_id, "worker")
        head = self.binding.candidate_head

        self.engine.execute_role(task_id, "IMPLEMENT", 0, "impl-0", "worker", gen, {
            "status": "READY", "candidate_head": head, "diff_lines": 1,
            "cost_microusd": 0, "evidence_ref": "impl-0-e",
        })
        self.engine.execute_role(task_id, "LAB", 0, "lab-fix", "worker", gen, {
            "verdict": "FIX_REQUIRED", "reviewed_head": head, "evidence_ref": "lab-fix-e",
            "code": "L1", "detail": "repair",
        })
        self.assertEqual(db.get_task(task_id)["state"], "LAB_FIX_REQUIRED")
        db.transition(task_id, "IN_IMPLEMENT", actor="auto_remediator", event_type="AUTO_REMEDIATE", fencing=("worker", gen))

        self.engine.execute_role(task_id, "IMPLEMENT", 1, "impl-1", "worker", gen, {
            "status": "READY", "candidate_head": head, "diff_lines": 1,
            "cost_microusd": 0, "evidence_ref": "impl-1-e",
        })
        self.engine.execute_role(task_id, "LAB", 1, "lab-pass", "worker", gen, {
            "verdict": "PASS", "reviewed_head": head, "evidence_ref": "lab-pass-e",
        })
        self.engine.execute_role(task_id, "AUDIT", 0, "audit-fix", "worker", gen, {
            "verdict": "FIX_REQUIRED", "reviewed_head": head, "evidence_ref": "audit-fix-e",
            "code": "A1", "detail": "repair again",
        })
        self.assertEqual(db.get_task(task_id)["state"], "AUDIT_FIX_REQUIRED")
        db.transition(task_id, "IN_IMPLEMENT", actor="auto_remediator", event_type="AUTO_REMEDIATE", fencing=("worker", gen))

        self.engine.execute_role(task_id, "IMPLEMENT", 2, "impl-2", "worker", gen, {
            "status": "READY", "candidate_head": head, "diff_lines": 1,
            "cost_microusd": 0, "evidence_ref": "impl-2-e",
        })
        self.engine.execute_role(task_id, "LAB", 2, "lab-pass-2", "worker", gen, {
            "verdict": "PASS", "reviewed_head": head, "evidence_ref": "lab-pass-2-e",
        })
        self.engine.execute_role(task_id, "AUDIT", 1, "audit-pass", "worker", gen, {
            "verdict": "PASS", "reviewed_head": head, "evidence_ref": "audit-pass-e",
        })
        self.assertEqual(db.get_task(task_id)["state"], "DONE")

        conn = sqlite3.connect(config.DB_PATH)
        try:
            owner_gate_events = conn.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND (before_state='OWNER_GATE' OR after_state='OWNER_GATE')",
                (task_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(owner_gate_events, 0)


if __name__ == "__main__":
    unittest.main()
