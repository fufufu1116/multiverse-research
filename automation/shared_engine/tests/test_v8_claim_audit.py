import json
import os
import sqlite3
import tempfile
import unittest

import config
import db


class V8ClaimAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _last(self, task_id):
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            return dict(conn.execute(
                "SELECT actor,event_type,before_state,after_state,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone())
        finally:
            conn.close()

    def test_exact_claim_records_authoritative_worker_generation_and_mode(self):
        task_id = db.create_task("core", "exact claim audit", task_type="implement")
        generation = db.claim_task(task_id, "worker-exact")
        event = self._last(task_id)
        detail = json.loads(event["detail_json"])
        self.assertEqual(event["actor"], "worker-exact")
        self.assertEqual(event["event_type"], "LEASE_CLAIMED")
        self.assertEqual(event["before_state"], "PENDING")
        self.assertEqual(event["after_state"], "PENDING")
        self.assertEqual(detail["generation"], generation)
        self.assertEqual(detail["claim_mode"], "exact")
        self.assertGreater(detail["lease_until"], 0)

    def test_queue_claim_records_authoritative_worker_generation_and_mode(self):
        task_id = db.create_task("core", "queue claim audit", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-queue"), task_id)
        task = db.get_task(task_id)
        event = self._last(task_id)
        detail = json.loads(event["detail_json"])
        self.assertEqual(event["actor"], "worker-queue")
        self.assertEqual(event["event_type"], "LEASE_CLAIMED")
        self.assertEqual(detail["generation"], task["claim_generation"])
        self.assertEqual(detail["claim_mode"], "queue")


if __name__ == "__main__":
    unittest.main()
