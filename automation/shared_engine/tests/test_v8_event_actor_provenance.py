import json
import os
import sqlite3
import tempfile
import unittest

import config
import db


class V8EventActorProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_transition_event_actor_is_fenced_worker_not_declared_label(self):
        task_id = db.create_task("core", "actor provenance", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-1"), task_id)
        generation = db.get_task(task_id)["claim_generation"]

        db.transition(
            task_id,
            "IN_IMPLEMENT",
            actor="Independent Auditor",
            event_type="AUDITOR_APPROVED",
            detail={"fencing_worker": "spoofed", "declared_actor": "spoofed"},
            fencing=("worker-1", generation),
        )

        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            event = conn.execute(
                "SELECT actor,event_type,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        finally:
            conn.close()

        detail = json.loads(event["detail_json"])
        self.assertEqual(event["actor"], "worker-1")
        self.assertEqual(event["event_type"], "AUDITOR_APPROVED")
        self.assertEqual(detail["declared_actor"], "Independent Auditor")
        self.assertEqual(detail["fencing_worker"], "worker-1")

    def test_normal_engine_emitter_label_is_preserved_without_replacing_provenance(self):
        task_id = db.create_task("core", "normal emitter", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-2"), task_id)
        generation = db.get_task(task_id)["claim_generation"]

        db.transition(
            task_id,
            "IN_IMPLEMENT",
            actor="exact_v7_shared_engine",
            event_type="START",
            fencing=("worker-2", generation),
        )

        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            event = conn.execute(
                "SELECT actor,detail_json FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        finally:
            conn.close()
        detail = json.loads(event["detail_json"])
        self.assertEqual(event["actor"], "worker-2")
        self.assertEqual(detail["declared_actor"], "exact_v7_shared_engine")
        self.assertEqual(detail["fencing_worker"], "worker-2")


if __name__ == "__main__":
    unittest.main()
