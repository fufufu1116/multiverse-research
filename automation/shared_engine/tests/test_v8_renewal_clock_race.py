import os
import sqlite3
import tempfile
import threading
import time
import unittest

import config
import db


class V8RenewalClockRaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, "task.db")
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _start_short_lease(self):
        task_id = db.create_task("core", "stale clock renewal race", task_type="implement")
        self.assertEqual(db.claim_next_task("worker-1", lease_seconds=0.20), task_id)
        gen = db.get_task(task_id)["claim_generation"]
        db.transition(task_id, "IN_IMPLEMENT", actor="test", event_type="START", fencing=("worker-1", gen))
        return task_id, gen

    def test_blocked_renewal_crossing_expiry_fails_then_reclaim_generation_bumps(self):
        task_id, gen1 = self._start_short_lease()
        before = db.get_task(task_id)
        blocker = sqlite3.connect(config.DB_PATH, timeout=10, check_same_thread=False)
        blocker.execute("PRAGMA busy_timeout=10000")
        blocker.execute("BEGIN IMMEDIATE")

        outcome = {}
        entered = threading.Event()

        def renew():
            entered.set()
            try:
                db.renew_lease(task_id, "worker-1", gen1, lease_seconds=0.20)
                outcome["value"] = "renewed"
            except BaseException as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=renew)
        thread.start()
        self.assertTrue(entered.wait(1))
        time.sleep(max(0.30, before["lease_until"] - time.time() + 0.10))
        blocker.commit()
        blocker.close()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertNotEqual(outcome.get("value"), "renewed")
        self.assertIsInstance(outcome.get("error"), db.LostLeaseError)
        self.assertIn("task lease expired", str(outcome["error"]))

        after_failed_renew = db.get_task(task_id)
        self.assertEqual(after_failed_renew["state"], before["state"])
        self.assertEqual(after_failed_renew["claimed_by"], before["claimed_by"])
        self.assertEqual(after_failed_renew["claim_generation"], before["claim_generation"])
        self.assertEqual(after_failed_renew["lease_until"], before["lease_until"])

        # Use a comfortably long post-reclaim lease: this assertion is about successful
        # generation-bumped takeover, not scheduler speed after the transaction commits.
        gen2 = db.reclaim_expired_task(task_id, "worker-2", lease_seconds=1.0)
        self.assertEqual(gen2, gen1 + 1)
        reclaimed = db.get_task(task_id)
        self.assertEqual(reclaimed["claimed_by"], "worker-2")
        self.assertEqual(reclaimed["claim_generation"], gen2)
        self.assertGreater(reclaimed["lease_until"], time.time())

    def test_reclaim_samples_time_after_writer_lock(self):
        task_id, gen1 = self._start_short_lease()
        blocker = sqlite3.connect(config.DB_PATH, timeout=10, check_same_thread=False)
        blocker.execute("PRAGMA busy_timeout=10000")
        blocker.execute("BEGIN IMMEDIATE")
        outcome = {}
        entered = threading.Event()

        def reclaim():
            entered.set()
            try:
                outcome["generation"] = db.reclaim_expired_task(task_id, "worker-2", lease_seconds=0.20)
            except BaseException as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=reclaim)
        thread.start()
        self.assertTrue(entered.wait(1))
        time.sleep(0.30)
        blocker.commit()
        blocker.close()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertNotIn("error", outcome)
        self.assertEqual(outcome.get("generation"), gen1 + 1)


if __name__ == "__main__":
    unittest.main()
