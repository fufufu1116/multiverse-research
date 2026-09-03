import os
import sqlite3
import tempfile
import unittest

import config
import db


class V8TransitionMatrixSupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        config.DB_PATH = os.path.join(self.tmp.name, 'tasks.db')
        db.init_schema()

    def tearDown(self):
        config.DB_PATH = self.old_db
        self.tmp.cleanup()

    def _event_count(self, task_id):
        c = sqlite3.connect(config.DB_PATH)
        try:
            return c.execute('SELECT COUNT(*) FROM events WHERE task_id=?', (task_id,)).fetchone()[0]
        finally:
            c.close()

    def _authority_snapshot(self, task_id):
        t = db.get_task(task_id)
        return {
            'state': t['state'],
            'claimed_by': t['claimed_by'],
            'claim_generation': t['claim_generation'],
            'lease_until': t['lease_until'],
            'result': t['result'],
            'events': self._event_count(task_id),
        }

    def _active_task(self):
        tid = db.create_task('core', 'matrix-support')
        self.assertEqual(db.claim_next_task('worker-1', lease_seconds=30), tid)
        gen = db.get_task(tid)['claim_generation']
        db.transition(
            tid,
            'IN_IMPLEMENT',
            actor='support',
            event_type='START',
            fencing=('worker-1', gen),
        )
        return tid, gen

    def test_illegal_active_transition_is_exactly_immutable(self):
        tid, gen = self._active_task()
        before = self._authority_snapshot(tid)
        with self.assertRaises(db.InvalidTransitionError):
            db.transition(
                tid,
                'DONE',
                actor='support',
                event_type='ILLEGAL_SKIP',
                result_update={'should_not_exist': True},
                release=True,
                fencing=('worker-1', gen),
            )
        self.assertEqual(self._authority_snapshot(tid), before)

    def test_terminal_done_cannot_reopen_and_is_exactly_immutable(self):
        tid, gen = self._active_task()
        db.transition(tid, 'IN_LAB', actor='support', event_type='IMPLEMENT_OK', fencing=('worker-1', gen))
        db.transition(tid, 'IN_AUDIT', actor='support', event_type='LAB_OK', fencing=('worker-1', gen))
        db.transition(tid, 'DONE', actor='support', event_type='AUDIT_OK', release=True, fencing=('worker-1', gen))
        before = self._authority_snapshot(tid)
        for target in config.ALLOWED_TRANSITIONS:
            if target == 'DONE':
                continue
            with self.assertRaises(db.InvalidTransitionError, msg=f'DONE->{target}'):
                db.transition(tid, target, actor='support', event_type='REOPEN_ATTEMPT')
            self.assertEqual(self._authority_snapshot(tid), before)

    def test_all_declared_terminal_states_have_no_outbound_transition(self):
        for terminal in ('FAILED_CLOSED', 'OWNER_GATE', 'DONE', 'ROLLED_BACK'):
            self.assertEqual(config.ALLOWED_TRANSITIONS.get(terminal), set(), terminal)


if __name__ == '__main__':
    unittest.main()
