import os
import sqlite3
import tempfile
import unittest

import config
import db


class V8ClaimAuditSupportProbe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _events(self, task_id):
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(
                "SELECT actor,event_type,before_state,after_state,detail_json FROM events WHERE task_id=? ORDER BY id",
                (task_id,),
            ).fetchall()]
        finally:
            conn.close()

    def test_exact_claim_mutates_generation_and_owner_without_durable_claim_event(self):
        task_id = db.create_task("core", "claim audit probe", task_type="implement")
        generation = db.claim_task(task_id, "worker-claim")
        task = db.get_task(task_id)
        self.assertEqual(generation, 1)
        self.assertEqual(task["claimed_by"], "worker-claim")
        self.assertEqual(task["claim_generation"], 1)
        events = self._events(task_id)
        self.assertEqual([e["event_type"] for e in events], ["TASK_CREATED"])

    def test_queue_claim_mutates_generation_and_owner_without_durable_claim_event(self):
        task_id = db.create_task("core", "queue claim audit probe", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-queue"), task_id)
        task = db.get_task(task_id)
        self.assertEqual(task["claimed_by"], "worker-queue")
        self.assertEqual(task["claim_generation"], 1)
        events = self._events(task_id)
        self.assertEqual([e["event_type"] for e in events], ["TASK_CREATED"])


if __name__ == "__main__":
    unittest.main()
