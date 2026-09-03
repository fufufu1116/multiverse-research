import inspect
import os
import tempfile
import time
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding
from local_persistent_worker_v9 import LocalPersistentWorker, WorkerConfig

HEAD = '9' * 40
BRANCH = 'agent/automation-shared-engine-persistent-worker-v9-test'


class LocalPersistentWorkerV9Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        config.DB_PATH = os.path.join(self.tmp.name, 'task.db')
        db.init_schema()
        self.binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
        self.bridge = os.path.join(self.tmp.name, 'bridge.db')
        self.provider = os.path.join(self.tmp.name, 'provider.db')
        self.engine = ExactV7SharedEngine(self.binding, self.bridge, self.provider)

    def tearDown(self):
        self.engine.close()
        config.DB_PATH = self.old_db
        self.tmp.cleanup()

    def worker(self, **kwargs):
        return LocalPersistentWorker(
            self.binding,
            self.bridge,
            self.provider,
            WorkerConfig(lease_seconds=0.30, heartbeat_seconds=0.05, poll_seconds=0.01),
            **kwargs,
        )

    def test_worker_identity_is_internal_and_bounded(self):
        sig = inspect.signature(LocalPersistentWorker)
        self.assertNotIn('worker_id', sig.parameters)
        self.assertNotIn('engine', sig.parameters)
        a, b = self.worker(), self.worker()
        self.assertNotEqual(a.worker_id, b.worker_id)
        self.assertTrue(a.worker_id.startswith('lpw9-'))
        self.assertLessEqual(len(a.worker_id), config.WORKER_ID_MAX_LENGTH)

    def test_worker_has_no_task_creation_or_retained_engine_surface(self):
        source = inspect.getsource(LocalPersistentWorker)
        self.assertNotIn('create_task(', source)
        self.assertNotIn('.submit(', source)
        w = self.worker()
        self.assertFalse(hasattr(w, 'engine'))
        self.assertFalse(any(isinstance(value, ExactV7SharedEngine) for value in vars(w).values()))
        with self.assertRaisesRegex(TypeError, 'V9_EXACT_BINDING_TYPE_REQUIRED'):
            LocalPersistentWorker(object(), self.bridge, self.provider)

    def test_consumes_only_preexisting_task_and_runs_to_done(self):
        task = self.engine.submit('core', 'implement', 'preexisting only')
        w = self.worker()
        result = w.step()
        self.assertEqual(result, (task, 'DONE'))
        self.assertEqual(db.get_task(task)['state'], 'DONE')

    def test_keirin_same_worker_path(self):
        task = self.engine.submit('keirin', 'research', 'PIT-safe preexisting research')
        self.assertEqual(self.worker().step(), (task, 'DONE'))
        self.assertEqual(db.get_task(task)['state'], 'DONE')

    def test_restart_after_lab_fix_required_uses_durable_generation(self):
        task = self.engine.submit('core', 'implement', 'fix then restart')
        gen = db.claim_task(task, 'seed', lease_seconds=0.10)
        db.transition(task, 'IN_IMPLEMENT', actor='seed', event_type='START', fencing=('seed', gen))
        self.engine.execute_role(task, 'IMPLEMENT', 0, f'lpw9:{task}:implement:0', 'seed', gen,
            {'status':'READY','candidate_head':HEAD,'diff_lines':0,'cost_microusd':0,'evidence_ref':'seed-i'})
        self.engine.execute_role(task, 'LAB', 0, f'lpw9:{task}:lab:0', 'seed', gen,
            {'verdict':'FIX_REQUIRED','reviewed_head':HEAD,'evidence_ref':'seed-l','code':'EDGE','detail':'bounded'})
        self.assertEqual(db.get_task(task)['state'], 'LAB_FIX_REQUIRED')
        time.sleep(0.13)
        w = self.worker()
        self.assertEqual(w._semantic_generation(task), 1)
        self.assertEqual(w.step(), (task, 'DONE'))

    def test_poll_lease_heartbeat_and_cycle_bounds_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'V9_LEASE_BOUND'):
            WorkerConfig(lease_seconds=121, heartbeat_seconds=1, poll_seconds=.1).validate()
        with self.assertRaisesRegex(ValueError, 'V9_HEARTBEAT_BOUND'):
            WorkerConfig(lease_seconds=1, heartbeat_seconds=.6, poll_seconds=.1).validate()
        with self.assertRaisesRegex(ValueError, 'V9_POLL_BOUND'):
            WorkerConfig(lease_seconds=1, heartbeat_seconds=.1, poll_seconds=6).validate()
        with self.assertRaisesRegex(ValueError, 'V9_RUN_CYCLE_BOUND'):
            self.worker().run(max_cycles=1001)

    def test_idle_stop_is_clean_and_active_stop_does_not_force_release(self):
        idle = self.worker(); idle.stop(); self.assertEqual(idle.run(max_cycles=2), 0)
        task = self.engine.submit('core', 'implement', 'stop safety')
        active = self.worker()
        claimed = active._claim_or_reclaim(); self.assertIsNotNone(claimed)
        active.stop()
        self.assertEqual(active._drive_claimed(*claimed), 'IN_IMPLEMENT')
        snap = db.get_task(task)
        self.assertEqual(snap['state'], 'IN_IMPLEMENT')
        self.assertEqual(snap['claimed_by'], active.worker_id)
        self.assertIsNotNone(snap['lease_until'])


if __name__ == '__main__':
    unittest.main()
