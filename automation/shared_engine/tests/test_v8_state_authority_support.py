import os
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD, v7_result_to_bridge_receipt
from current_state import resume_instruction, shared_current
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding

HEAD = "6" * 40
BRANCH = "agent/automation-shared-engine-v8-adversarial-support-test"


class V8StateAuthoritySupportTests(unittest.TestCase):
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

    def _bindings(self):
        return {
            "canonical_main": CANONICAL_MAIN,
            "automation_candidate": HEAD,
            "keirin_research": "sealed-research-binding",
        }

    def test_recording_durable_bridge_receipt_cannot_mutate_task_state(self):
        task_id = self.engine.submit("core", "implement", "receipt evidence only")
        generation = self.engine.claim_and_start(task_id, "worker")
        before = db.get_task(task_id)["state"]
        job = self.engine._job(task_id, "IMPLEMENT", 0, "receipt-only")
        result = {
            "status": "READY",
            "candidate_head": HEAD,
            "diff_lines": 0,
            "cost_microusd": 0,
            "evidence_ref": "receipt-only-evidence",
        }
        receipt = v7_result_to_bridge_receipt(job, result, local_binding=self.binding)
        self.engine.bridge_receipts.record(receipt)
        after = db.get_task(task_id)
        self.assertEqual(after["state"], before)
        self.assertEqual(after["claimed_by"], "worker")
        self.assertEqual(after["claim_generation"], generation)

    def test_shared_current_is_read_only_projection_not_mutation_authority(self):
        task_id = self.engine.submit("core", "implement", "current projection")
        before = db.get_task(task_id).copy()
        snapshot = shared_current(self._bindings())
        self.assertEqual(snapshot["authority"]["task_state"], "sqlite")
        self.assertFalse(snapshot["authority"]["chat"])
        self.assertFalse(snapshot["authority"]["github_binding_is_mutation_authority"])
        snapshot["domains"]["core"]["next_state"] = "DONE"
        snapshot["owner_routing_required"] = True
        after = db.get_task(task_id)
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["claim_generation"], before["claim_generation"])
        self.assertEqual(after["claimed_by"], before["claimed_by"])

    def test_resume_instruction_requires_fresh_read_before_external_claims(self):
        task_id = self.engine.submit("keirin", "research", "resume proof")
        snapshot = shared_current(self._bindings())
        instruction = resume_instruction(snapshot, "keirin")
        self.assertEqual(instruction["task_id"], task_id)
        self.assertTrue(instruction["fresh_read_required_before_external_claims"])

    def test_shared_current_rejects_missing_or_extra_binding_keys(self):
        bindings = self._bindings()
        missing = dict(bindings)
        missing.pop("canonical_main")
        with self.assertRaisesRegex(ValueError, "CURRENT_BINDING_KEYS"):
            shared_current(missing)
        extra = dict(bindings)
        extra["chat_memory"] = "not-authority"
        with self.assertRaisesRegex(ValueError, "CURRENT_BINDING_KEYS"):
            shared_current(extra)

    def test_resume_instruction_rejects_unknown_domain_and_schema_drift(self):
        snapshot = shared_current(self._bindings())
        with self.assertRaisesRegex(ValueError, "CURRENT_DOMAIN"):
            resume_instruction(snapshot, "unknown")
        drifted = dict(snapshot)
        drifted["schema"] = "multiverse.shared-current.future"
        with self.assertRaisesRegex(ValueError, "CURRENT_SCHEMA"):
            resume_instruction(drifted, "core")


if __name__ == "__main__":
    unittest.main()
