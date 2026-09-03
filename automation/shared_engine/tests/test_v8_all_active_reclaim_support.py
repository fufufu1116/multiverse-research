import os
import sqlite3
import tempfile
import time
import unittest

import config
import db


class V8AllActiveReclaimSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_declared_recoverable_state_reclaims_with_generation_bump(self):
        for state in sorted(db.RECOVERABLE_ACTIVE_STATES):
            task_id = db.create_task("core", f"reclaim {state}", task_type="implement")
            generation = db.claim_task(task_id, "worker-old")
            conn = sqlite3.connect(config.DB_PATH)
            try:
                conn.execute(
                    "UPDATE tasks SET state=?, lease_until=? WHERE id=?",
                    (state, time.time() - 1.0, task_id),
                )
                conn.commit()
            finally:
                conn.close()

            new_generation = db.reclaim_expired_task(task_id, "worker-new")
            task = db.get_task(task_id)
            self.assertEqual(task["state"], state)
            self.assertEqual(task["claimed_by"], "worker-new")
            self.assertEqual(new_generation, generation + 1)
            self.assertEqual(task["claim_generation"], generation + 1)
            self.assertGreater(task["lease_until"], time.time())

            with self.assertRaises(db.LostLeaseError):
                db.assert_unexpired_fence(task_id, "worker-old", generation)
            self.assertTrue(db.assert_unexpired_fence(task_id, "worker-new", new_generation))


if __name__ == "__main__":
    unittest.main()
