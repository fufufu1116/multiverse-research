import math
import os
import sqlite3
import tempfile
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding

HEAD = "7" * 40
BRANCH = "agent/automation-shared-engine-integration-v8-candidate-20260903-v1"


class V8LeaseRenewalTests(unittest.TestCase):
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

    def _expire(self, task_id):
        conn = sqlite3.connect(config.DB_PATH)
        try:
            conn.execute("UPDATE tasks SET lease_until=0 WHERE id=?", (task_id,))
            conn.commit()
        finally:
            conn.close()

    def _snapshot(self, task_id):
        task = db.get_task(task_id)
        return (task["claimed_by"], task["claim_generation"], task["lease_until"], task["state"])

    def test_live_owner_can_renew_without_generation_change(self):
        task_id = self.engine.submit("core", "implement", "long work")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        before = db.get_task(task_id)
        renewed_until = self.engine.renew(task_id, "worker-1", gen, lease_seconds=config.LEASE_MAX_SECONDS)
        after = db.get_task(task_id)
        self.assertGreaterEqual(renewed_until, before["lease_until"])
        self.assertEqual(after["claimed_by"], "worker-1")
        self.assertEqual(after["claim_generation"], gen)
        self.assertEqual(after["state"], "IN_IMPLEMENT")

    def test_stale_worker_or_generation_cannot_renew(self):
        task_id = self.engine.submit("core", "implement", "no stale heartbeat")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        original = db.get_task(task_id)["lease_until"]
        with self.assertRaisesRegex(db.LostLeaseError, "stale fencing token"):
            self.engine.renew(task_id, "worker-2", gen, lease_seconds=120)
        with self.assertRaisesRegex(db.LostLeaseError, "stale fencing token"):
            self.engine.renew(task_id, "worker-1", gen + 1, lease_seconds=120)
        self.assertEqual(db.get_task(task_id)["lease_until"], original)

    def test_expired_lease_cannot_be_resurrected_by_renewal(self):
        task_id = self.engine.submit("core", "implement", "expired heartbeat")
        gen1 = self.engine.claim_and_start(task_id, "worker-1")
        self._expire(task_id)
        with self.assertRaisesRegex(db.LostLeaseError, "task lease expired"):
            self.engine.renew(task_id, "worker-1", gen1, lease_seconds=120)
        self.assertEqual(db.get_task(task_id)["claim_generation"], gen1)
        gen2 = self.engine.reclaim_expired(task_id, "worker-2")
        self.assertEqual(gen2, gen1 + 1)

    def test_pending_task_cannot_be_renewed(self):
        task_id = self.engine.submit("core", "implement", "not claimed")
        with self.assertRaisesRegex(db.InvalidTransitionError, "RENEW_STATE:PENDING"):
            db.renew_lease(task_id, "worker", 1, lease_seconds=120)

    def test_invalid_renewal_duration_fails_closed_without_mutation(self):
        task_id = self.engine.submit("core", "implement", "bad heartbeat")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        before = self._snapshot(task_id)
        bad_values = (
            0, -1, True, "120", None if config.LEASE_SECONDS is None else object(),
            config.LEASE_MAX_SECONDS + 0.001, config.LEASE_MAX_SECONDS * 1000,
            float("inf"), float("-inf"), float("nan"),
        )
        for bad in bad_values:
            with self.subTest(bad=repr(bad)):
                with self.assertRaisesRegex(ValueError, "LEASE_SECONDS_BOUNDED_FINITE_REQUIRED"):
                    self.engine.renew(task_id, "worker-1", gen, lease_seconds=bad)
                self.assertEqual(self._snapshot(task_id), before)

    def test_reclaim_duration_uses_same_bounded_finite_invariant(self):
        task_id = self.engine.submit("core", "implement", "bad reclaim duration")
        gen = self.engine.claim_and_start(task_id, "worker-1")
        self._expire(task_id)
        before = self._snapshot(task_id)
        for bad in (0, -1, True, "120", config.LEASE_MAX_SECONDS + 1, float("inf"), float("nan")):
            with self.subTest(bad=repr(bad)):
                with self.assertRaisesRegex(ValueError, "LEASE_SECONDS_BOUNDED_FINITE_REQUIRED"):
                    self.engine.reclaim_expired(task_id, "worker-2", lease_seconds=bad)
                self.assertEqual(self._snapshot(task_id), before)
        gen2 = self.engine.reclaim_expired(task_id, "worker-2", lease_seconds=config.LEASE_MAX_SECONDS)
        self.assertEqual(gen2, gen + 1)
        self.assertTrue(math.isfinite(db.get_task(task_id)["lease_until"]))


if __name__ == "__main__":
    unittest.main()
