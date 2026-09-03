import os
import tempfile
import unittest

import config
import db


class V8ActiveReleaseSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _active_task(self):
        task_id = db.create_task("core", "release liveness probe", task_type="implement")
        claimed = db.claim_next_task("worker-1")
        self.assertEqual(claimed, task_id)
        gen = db.get_task(task_id)["claim_generation"]
        db.transition(task_id, "IN_IMPLEMENT", actor="support", event_type="START", fencing=("worker-1", gen))
        return task_id, gen

    def test_release_flag_cannot_orphan_nonterminal_active_state(self):
        task_id, gen = self._active_task()
        before = db.get_task(task_id)
        with self.assertRaises(db.InvalidTransitionError):
            db.transition(
                task_id,
                "IN_LAB",
                actor="support",
                event_type="ILLEGAL_ACTIVE_RELEASE",
                release=True,
                fencing=("worker-1", gen),
            )
        after = db.get_task(task_id)
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["claimed_by"], before["claimed_by"])
        self.assertEqual(after["claim_generation"], before["claim_generation"])
        self.assertEqual(after["lease_until"], before["lease_until"])

    def test_done_release_remains_allowed(self):
        task_id, gen = self._active_task()
        db.transition(task_id, "IN_LAB", actor="support", event_type="IMPLEMENT_PASS", fencing=("worker-1", gen))
        db.transition(task_id, "IN_AUDIT", actor="support", event_type="LAB_PASS", fencing=("worker-1", gen))
        db.transition(task_id, "DONE", actor="support", event_type="AUDIT_PASS", release=True, fencing=("worker-1", gen))
        task = db.get_task(task_id)
        self.assertEqual(task["state"], "DONE")
        self.assertIsNone(task["claimed_by"])
        self.assertIsNone(task["lease_until"])


if __name__ == "__main__":
    unittest.main()
