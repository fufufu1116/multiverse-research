import os
import tempfile
import unittest

import config
import db


class V8ReleaseLivenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _active_task(self):
        task_id = db.create_task("core", "release liveness", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-1"), task_id)
        gen = db.get_task(task_id)["claim_generation"]
        db.transition(task_id, "IN_IMPLEMENT", actor="test", event_type="START", fencing=("worker-1", gen))
        return task_id, gen

    def test_release_cannot_orphan_active_or_blocked_target(self):
        task_id, gen = self._active_task()
        for target in ("IN_LAB", "BLOCKED_TECHNICAL"):
            with self.subTest(target=target):
                before = db.get_task(task_id)
                with self.assertRaisesRegex(db.InvalidTransitionError, f"RELEASE_TARGET:{target}"):
                    db.transition(task_id, target, actor="test", event_type="BAD_RELEASE", release=True, fencing=("worker-1", gen))
                after = db.get_task(task_id)
                self.assertEqual(after["state"], before["state"])
                self.assertEqual(after["claimed_by"], before["claimed_by"])
                self.assertEqual(after["claim_generation"], before["claim_generation"])
                self.assertEqual(after["lease_until"], before["lease_until"])

    def test_done_release_is_allowed(self):
        task_id, gen = self._active_task()
        db.transition(task_id, "IN_LAB", actor="test", event_type="IMPLEMENT_PASS", fencing=("worker-1", gen))
        db.transition(task_id, "IN_AUDIT", actor="test", event_type="LAB_PASS", fencing=("worker-1", gen))
        db.transition(task_id, "DONE", actor="test", event_type="AUDIT_PASS", release=True, fencing=("worker-1", gen))
        task = db.get_task(task_id)
        self.assertEqual(task["state"], "DONE")
        self.assertIsNone(task["claimed_by"])
        self.assertIsNone(task["lease_until"])

    def test_requeue_to_pending_may_release_for_new_claim(self):
        task_id, gen = self._active_task()
        db.transition(task_id, "BLOCKED_TECHNICAL", actor="test", event_type="BLOCK", fencing=("worker-1", gen))
        db.transition(task_id, "PENDING", actor="test", event_type="REQUEUE", release=True, fencing=("worker-1", gen))
        task = db.get_task(task_id)
        self.assertEqual(task["state"], "PENDING")
        self.assertIsNone(task["claimed_by"])
        self.assertIsNone(task["lease_until"])
        self.assertEqual(db.claim_next_task("worker-2"), task_id)
        self.assertEqual(db.get_task(task_id)["claim_generation"], gen + 1)


if __name__ == "__main__":
    unittest.main()
