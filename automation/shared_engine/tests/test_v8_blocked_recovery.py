import os
import sqlite3
import tempfile
import time
import unittest

import config
import db


class V8BlockedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        config.DB_PATH = os.path.join(self.tmp.name, 'tasks.db')
        db.init_schema()

    def tearDown(self):
        config.DB_PATH = self.old_db
        self.tmp.cleanup()

    def _blocked_task(self, lease_seconds=30):
        tid = db.create_task('core', 'blocked-recovery')
        gen = db.claim_task(tid, 'worker-1', lease_seconds=lease_seconds)
        db.transition(
            tid,
            'IN_IMPLEMENT',
            actor='test',
            event_type='START',
            fencing=('worker-1', gen),
        )
        db.transition(
            tid,
            'BLOCKED_TECHNICAL',
            actor='test',
            event_type='BLOCK',
            fencing=('worker-1', gen),
        )
        return tid, gen

    def _expire(self, tid):
        c = sqlite3.connect(config.DB_PATH)
        try:
            c.execute('UPDATE tasks SET lease_until=? WHERE id=?', (time.time() - 1, tid))
            c.commit()
        finally:
            c.close()

    def test_expired_blocked_task_can_be_reclaimed_and_requeued(self):
        tid, old_gen = self._blocked_task()
        self._expire(tid)

        new_gen = db.reclaim_expired_task(tid, 'worker-2', lease_seconds=30)
        self.assertEqual(new_gen, old_gen + 1)
        t = db.get_task(tid)
        self.assertEqual(t['state'], 'BLOCKED_TECHNICAL')
        self.assertEqual(t['claimed_by'], 'worker-2')
        self.assertEqual(t['claim_generation'], new_gen)

        db.transition(
            tid,
            'PENDING',
            actor='worker-2',
            event_type='UNBLOCK_REQUEUE',
            release=True,
            fencing=('worker-2', new_gen),
        )
        t = db.get_task(tid)
        self.assertEqual(t['state'], 'PENDING')
        self.assertIsNone(t['claimed_by'])
        self.assertIsNone(t['lease_until'])

    def test_live_blocked_owner_can_renew_without_generation_change(self):
        tid, gen = self._blocked_task(lease_seconds=10)
        before = db.get_task(tid)
        renewed_until = db.renew_lease(tid, 'worker-1', gen, lease_seconds=30)
        after = db.get_task(tid)
        self.assertEqual(after['state'], 'BLOCKED_TECHNICAL')
        self.assertEqual(after['claimed_by'], 'worker-1')
        self.assertEqual(after['claim_generation'], gen)
        self.assertGreater(renewed_until, before['lease_until'])

    def test_expired_blocked_old_worker_is_fenced_after_reclaim(self):
        tid, old_gen = self._blocked_task()
        self._expire(tid)
        new_gen = db.reclaim_expired_task(tid, 'worker-2', lease_seconds=30)
        with self.assertRaises(db.LostLeaseError):
            db.transition(
                tid,
                'PENDING',
                actor='worker-1',
                event_type='STALE_UNBLOCK',
                release=True,
                fencing=('worker-1', old_gen),
            )
        self.assertEqual(db.get_task(tid)['claim_generation'], new_gen)
        self.assertEqual(db.get_task(tid)['claimed_by'], 'worker-2')


if __name__ == '__main__':
    unittest.main()
