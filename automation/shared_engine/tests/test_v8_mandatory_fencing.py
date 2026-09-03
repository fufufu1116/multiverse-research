import os
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding

HEAD = "7" * 40
BRANCH = "agent/automation-shared-engine-integration-v8-candidate-20260903-v1"


class V8MandatoryFencingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()
        self.engine = ExactV7SharedEngine(
            IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD),
            os.path.join(self.tmp.name, "bridge.db"),
            os.path.join(self.tmp.name, "provider.db"),
        )

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def test_low_level_transition_without_fence_is_rejected_and_state_unchanged(self):
        task_id = self.engine.submit("core", "implement", "no bypass")
        gen = self.engine.claim_and_start(task_id, "worker")
        before = db.get_task(task_id)

        with self.assertRaisesRegex(db.LostLeaseError, "fencing token required"):
            db.transition(task_id, "IN_LAB", actor="bypass", event_type="UNFENCED_BYPASS")

        after = db.get_task(task_id)
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["claimed_by"], "worker")
        self.assertEqual(after["claim_generation"], gen)

    def test_valid_live_fence_still_allows_expected_transition(self):
        task_id = self.engine.submit("core", "implement", "fenced path")
        gen = self.engine.claim_and_start(task_id, "worker")
        self.assertEqual(
            db.transition(task_id, "IN_LAB", actor="fenced", event_type="FENCED_PATH", fencing=("worker", gen)),
            "IN_LAB",
        )


if __name__ == "__main__":
    unittest.main()
