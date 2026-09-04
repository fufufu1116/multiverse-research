import os
import sqlite3
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding

HEAD = "8" * 40
BRANCH = "agent/automation-shared-engine-integration-v8-candidate-20260903-v1"


class V8WorkerIdentityTests(unittest.TestCase):
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
        return (task["state"], task["claimed_by"], task["claim_generation"], task["lease_until"])

    def _expire(self, task_id):
        conn = sqlite3.connect(config.DB_PATH)
        try:
            conn.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    def test_missing_or_unbounded_worker_id_cannot_claim_task(self):
        task_id = self.engine.submit("core", "implement", "identity fence")
        before = self._snapshot(task_id)
        bad_ids = (None, "", "   ", 7, True, "x" * (config.WORKER_ID_MAX_LENGTH + 1))
        for bad in bad_ids:
            with self.subTest(worker_id=repr(bad)):
                with self.assertRaisesRegex(ValueError, "WORKER_ID_BOUNDED_NONEMPTY_REQUIRED"):
                    db.claim_next_task(bad)
                self.assertEqual(self._snapshot(task_id), before)

    def test_engine_cannot_start_active_task_without_worker_identity(self):
        task_id = self.engine.submit("core", "implement", "no anonymous active owner")
        before = self._snapshot(task_id)
        with self.assertRaisesRegex(ValueError, "WORKER_ID_BOUNDED_NONEMPTY_REQUIRED"):
            self.engine.claim_and_start(task_id, None)
        self.assertEqual(self._snapshot(task_id), before)

    def test_invalid_worker_cannot_renew_or_transition(self):
        task_id = self.engine.submit("core", "implement", "identity remains fenced")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        before = self._snapshot(task_id)
        for bad in (None, "", "   ", "x" * (config.WORKER_ID_MAX_LENGTH + 1)):
            with self.subTest(worker_id=repr(bad)):
                with self.assertRaisesRegex(ValueError, "WORKER_ID_BOUNDED_NONEMPTY_REQUIRED"):
                    db.renew_lease(task_id, bad, gen)
                with self.assertRaisesRegex(ValueError, "WORKER_ID_BOUNDED_NONEMPTY_REQUIRED"):
                    db.transition(task_id, "IN_LAB", actor="attack", event_type="ATTACK", fencing=(bad, gen))
                self.assertEqual(self._snapshot(task_id), before)

    def test_invalid_reclaimer_cannot_take_expired_task(self):
        task_id = self.engine.submit("core", "implement", "no anonymous reclaim")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        self._expire(task_id)
        before = self._snapshot(task_id)
        for bad in (None, "", "   ", "x" * (config.WORKER_ID_MAX_LENGTH + 1)):
            with self.subTest(worker_id=repr(bad)):
                with self.assertRaisesRegex(ValueError, "WORKER_ID_BOUNDED_NONEMPTY_REQUIRED"):
                    self.engine.reclaim_expired(task_id, bad)
                self.assertEqual(self._snapshot(task_id), before)
        gen2 = self.engine.reclaim_expired(task_id, "worker-2")
        self.assertEqual(gen2, gen + 1)


if __name__ == "__main__":
    unittest.main()
