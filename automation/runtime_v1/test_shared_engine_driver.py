import os
import sqlite3
import tempfile
import unittest

import config
import db
from shared_engine_driver import SharedEngineRuntimeDriver


class SharedEngineRuntimeDriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        config.DB_PATH = os.path.join(self.tmp.name, "engine.db")
        db.init_schema()
        self.driver = SharedEngineRuntimeDriver()

    def tearDown(self):
        config.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_claim_start_uses_exact_fenced_task(self):
        low = db.create_task("core", "low", task_type="research", priority=1)
        high = db.create_task("core", "high", task_type="implement", priority=10)
        started = self.driver.claim_and_start_next("runtime-worker")
        self.assertEqual(started["task_id"], high)
        self.assertEqual(started["state"], "IN_IMPLEMENT")
        self.assertEqual(db.get_task(low)["state"], "PENDING")
        self.assertIsNone(db.get_task(low)["claimed_by"])
        self.assertEqual(db.get_task(high)["claimed_by"], "runtime-worker")
        self.assertEqual(db.get_task(high)["claim_generation"], started["claim_generation"])

    def test_invalid_persisted_domain_is_skipped_without_claim(self):
        now = 1_800_000_000.0
        c = sqlite3.connect(config.DB_PATH)
        with c:
            c.execute("INSERT INTO tasks(id,domain,task_type,goal,priority,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                      ("bad", "keirin", "implement", "bad", 99, "PENDING", now, now))
        c.close()
        good = db.create_task("core", "good", task_type="implement", priority=1)
        started = self.driver.claim_and_start_next("runtime-worker")
        self.assertEqual(started["task_id"], good)
        bad = db.get_task("bad")
        self.assertEqual(bad["state"], "PENDING")
        self.assertIsNone(bad["claimed_by"])

    def test_stale_generation_cannot_renew_after_reclaim(self):
        tid = db.create_task("core", "lease", task_type="implement")
        started = self.driver.claim_and_start_next("worker-a")
        self.assertEqual(started["task_id"], tid)
        gen1 = started["claim_generation"]
        c = sqlite3.connect(config.DB_PATH)
        with c:
            c.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (tid,))
        c.close()
        gen2 = self.driver.reclaim_expired(tid, "worker-b")
        self.assertGreater(gen2, gen1)
        with self.assertRaises(db.LostLeaseError):
            self.driver.renew(tid, "worker-a", gen1)
        self.assertGreater(self.driver.renew(tid, "worker-b", gen2), 0)

    def test_empty_queue_is_none(self):
        self.assertIsNone(self.driver.claim_and_start_next("runtime-worker"))


if __name__ == "__main__":
    unittest.main()
