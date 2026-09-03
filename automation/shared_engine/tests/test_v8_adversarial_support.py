import os
import tempfile
import threading
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD, v7_result_to_bridge_receipt
from exact_v7_shared_engine import ExactV7SharedEngine, V7_MANIFEST
from integration_bridge import IntegrationBinding, apply_receipt
from orchestrator_provider_adapter_v7 import (
    DeterministicLocalAdapter,
    OrchestratorError,
    ProviderAdapterManifest,
    ProviderAdapterReceiptStore,
    provider_request_from_job,
)

HEAD = "6" * 40
BRANCH = "agent/automation-shared-engine-v8-adversarial-support-test"


class V8AdversarialSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()
        self.binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
        self.engine = ExactV7SharedEngine(
            self.binding,
            os.path.join(self.tmp.name, "bridge.db"),
            os.path.join(self.tmp.name, "provider.db"),
        )

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def _provider_job(self, operation_key="same-op"):
        return {
            "operation_key": operation_key,
            "task_id": "t",
            "role": "IMPLEMENT",
            "semantic_generation": 0,
            "candidate_head": HEAD,
            "candidate_branch": BRANCH,
            "canonical_main": CANONICAL_MAIN,
            "objective": "x",
            "authority": {
                "candidate_only": True,
                "live_provider": False,
                "production": False,
                "runtime": False,
                "spend": False,
            },
        }

    def test_concurrent_same_operation_yields_one_durable_execution(self):
        manifest = ProviderAdapterManifest.load(V7_MANIFEST)
        path = os.path.join(self.tmp.name, "concurrent.db")
        request = provider_request_from_job(self._provider_job(), manifest)
        result = {
            "status": "READY",
            "candidate_head": HEAD,
            "diff_lines": 0,
            "cost_microusd": 0,
            "evidence_ref": "concurrent-e",
        }
        barrier = threading.Barrier(2)
        outputs = []
        errors = []

        def worker():
            store = ProviderAdapterReceiptStore(path, manifest)
            try:
                barrier.wait()
                outputs.append(
                    store.execute_local_once(
                        "same-op",
                        request,
                        DeterministicLocalAdapter({"IMPLEMENT": {"1": result}}),
                    )
                )
            except BaseException as exc:
                errors.append(exc)
            finally:
                store.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(outputs, [result, result])
        store = ProviderAdapterReceiptStore(path, manifest)
        try:
            self.assertEqual(store.execution_count("same-op"), 1)
        finally:
            store.close()

    def test_valid_receipt_cannot_advance_different_task(self):
        t1 = self.engine.submit("core", "implement", "one")
        gen1 = self.engine.claim_and_start(t1, "w")
        t2 = self.engine.submit("core", "implement", "two")
        before = db.get_task(t2)["state"]
        job = self.engine._job(t1, "IMPLEMENT", 0, "bound-op")
        result = {
            "status": "READY",
            "candidate_head": HEAD,
            "diff_lines": 0,
            "cost_microusd": 0,
            "evidence_ref": "bound-e",
        }
        bridge = v7_result_to_bridge_receipt(job, result, local_binding=self.binding)
        self.engine.bridge_receipts.record(bridge)
        with self.assertRaises(Exception):
            apply_receipt(t2, bridge, self.binding, "w", gen1)
        self.assertEqual(db.get_task(t2)["state"], before)

    def test_provider_main_drift_fails_before_receipt(self):
        manifest = ProviderAdapterManifest.load(V7_MANIFEST)
        job = self._provider_job("main-drift")
        job["canonical_main"] = "7" * 40
        with self.assertRaisesRegex(OrchestratorError, "PROVIDER_JOB_MAIN_MISMATCH"):
            provider_request_from_job(job, manifest)

    def test_provider_authority_widening_fails_before_receipt(self):
        manifest = ProviderAdapterManifest.load(V7_MANIFEST)
        job = self._provider_job("authority-drift")
        job["authority"] = dict(job["authority"])
        job["authority"]["runtime"] = True
        with self.assertRaisesRegex(OrchestratorError, "PROVIDER_JOB_AUTHORITY"):
            provider_request_from_job(job, manifest)

    def test_malformed_lab_result_does_not_advance(self):
        t = self.engine.submit("core", "implement", "x")
        gen = self.engine.claim_and_start(t, "w")
        self.engine.execute_role(
            t,
            "IMPLEMENT",
            0,
            "impl",
            "w",
            gen,
            {
                "status": "READY",
                "candidate_head": HEAD,
                "diff_lines": 0,
                "cost_microusd": 0,
                "evidence_ref": "impl-e",
            },
        )
        with self.assertRaises(OrchestratorError):
            self.engine.execute_role(
                t,
                "LAB",
                0,
                "bad-lab",
                "w",
                gen,
                {"verdict": "PASS", "reviewed_head": HEAD, "evidence_ref": ""},
            )
        self.assertEqual(db.get_task(t)["state"], "IN_LAB")

    def test_malformed_audit_result_does_not_advance(self):
        t = self.engine.submit("core", "implement", "x")
        gen = self.engine.claim_and_start(t, "w")
        self.engine.execute_role(
            t,
            "IMPLEMENT",
            0,
            "impl-a",
            "w",
            gen,
            {
                "status": "READY",
                "candidate_head": HEAD,
                "diff_lines": 0,
                "cost_microusd": 0,
                "evidence_ref": "impl-a-e",
            },
        )
        self.engine.execute_role(
            t,
            "LAB",
            0,
            "lab-pass",
            "w",
            gen,
            {"verdict": "PASS", "reviewed_head": HEAD, "evidence_ref": "lab-e"},
        )
        with self.assertRaises(OrchestratorError):
            self.engine.execute_role(
                t,
                "AUDIT",
                0,
                "bad-audit",
                "w",
                gen,
                {"verdict": "FIX_REQUIRED", "reviewed_head": HEAD, "evidence_ref": "a", "code": "", "detail": "x"},
            )
        self.assertEqual(db.get_task(t)["state"], "IN_AUDIT")


if __name__ == "__main__":
    unittest.main()
