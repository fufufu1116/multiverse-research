import os
import sqlite3
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding

HEAD = "9" * 40
BRANCH = "agent/automation-shared-engine-integration-v8-candidate-20260903-v1"


class V8GenerationIdentityTests(unittest.TestCase):
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

    def _snapshot(self, task_id):
        task = db.get_task(task_id)
        conn = sqlite3.connect(config.DB_PATH)
        try:
            events = conn.execute("SELECT COUNT(*) FROM events WHERE task_id=?", (task_id,)).fetchone()[0]
        finally:
            conn.close()
        return (
            task["state"], task["claimed_by"], task["claim_generation"],
            task["lease_until"], task["result"], events,
        )

    def test_bool_float_string_and_nonpositive_generations_cannot_fence(self):
        task_id = self.engine.submit("core", "implement", "strict generation identity")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        self.assertEqual(gen, 1)
        before = self._snapshot(task_id)

        for bad in (True, 1.0, "1", 0, -1, None):
            with self.subTest(generation=repr(bad)):
                with self.assertRaisesRegex(db.LostLeaseError, "invalid fencing generation"):
                    db.assert_unexpired_fence(task_id, "worker-1", bad)
                with self.assertRaisesRegex(db.LostLeaseError, "invalid fencing generation"):
                    db.renew_lease(task_id, "worker-1", bad)
                with self.assertRaisesRegex(db.LostLeaseError, "invalid fencing generation"):
                    db.transition(
                        task_id, "IN_LAB", actor="attack", event_type="ATTACK",
                        result_update={"should_not_write": True}, fencing=("worker-1", bad),
                    )
                self.assertEqual(self._snapshot(task_id), before)

    def test_exact_integer_generation_remains_valid(self):
        task_id = self.engine.submit("core", "implement", "valid integer generation")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        self.assertIs(type(gen), int)
        self.assertTrue(db.assert_unexpired_fence(task_id, "worker-1", gen))
        renewed = db.renew_lease(task_id, "worker-1", gen)
        self.assertIsInstance(renewed, float)
        self.assertEqual(
            db.transition(task_id, "IN_LAB", actor="worker-1", event_type="IMPLEMENT_DONE", fencing=("worker-1", gen)),
            "IN_LAB",
        )


if __name__ == "__main__":
    unittest.main()
