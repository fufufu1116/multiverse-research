import os
import sqlite3
import tempfile
import unittest

import config
import db


class V8ActorEvidenceSpoofProbe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fenced_worker_can_write_arbitrary_actor_into_event_evidence(self):
        task_id = db.create_task("core", "actor evidence spoof probe", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-1"), task_id)
        generation = db.get_task(task_id)["claim_generation"]

        db.transition(
            task_id,
            "IN_IMPLEMENT",
            actor="Independent Auditor",
            event_type="AUDITOR_APPROVED",
            fencing=("worker-1", generation),
        )

        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            event = conn.execute(
                "SELECT actor,event_type,before_state,after_state FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(event["actor"], "Independent Auditor")
        self.assertEqual(event["event_type"], "AUDITOR_APPROVED")
        self.assertEqual(event["before_state"], "PENDING")
        self.assertEqual(event["after_state"], "IN_IMPLEMENT")
        self.assertEqual(db.get_task(task_id)["claimed_by"], "worker-1")


if __name__ == "__main__":
    unittest.main()
