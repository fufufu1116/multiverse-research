import multiprocessing as mp
import os
import tempfile
import threading
import time
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding
from local_persistent_worker_v9 import LocalPersistentWorker, WorkerConfig
from orchestrator_provider_adapter_v7 import DeterministicLocalAdapter, ProviderAdapterReceiptStore, provider_request_from_job

HEAD = '8' * 40
BRANCH = 'agent/automation-shared-engine-persistent-worker-v9-integration'


def _process_worker(task_db, bridge_db, provider_db, max_cycles, execute_delay=0.0):
    config.DB_PATH = task_db
    binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
    engine = ExactV7SharedEngine(binding, bridge_db, provider_db)
    try:
        worker = LocalPersistentWorker(
            engine,
            WorkerConfig(lease_seconds=0.25, heartbeat_seconds=0.04, poll_seconds=0.02),
            _execute_delay=execute_delay,
        )
        worker.run(max_cycles=max_cycles)
    finally:
        engine.close()


class LocalPersistentWorkerV9IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        self.task_db = os.path.join(self.tmp.name, 'task.db')
        self.bridge_db = os.path.join(self.tmp.name, 'bridge.db')
        self.provider_db = os.path.join(self.tmp.name, 'provider.db')
        config.DB_PATH = self.task_db
        db.init_schema()
        self.binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
        self.engine = ExactV7SharedEngine(self.binding, self.bridge_db, self.provider_db)

    def tearDown(self):
        self.engine.close()
        config.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_live_heartbeat_prevents_competing_reclaim(self):
        task = self.engine.submit('core', 'implement', 'slow local fixture')
        result = []
        failure = []

        def run_worker_in_own_thread_connection():
            thread_engine = ExactV7SharedEngine(self.binding, self.bridge_db, self.provider_db)
            try:
                worker = LocalPersistentWorker(
                    thread_engine,
                    WorkerConfig(lease_seconds=0.25, heartbeat_seconds=0.04, poll_seconds=0.01),
                    _execute_delay=0.45,
                )
                result.append(worker.step())
            except BaseException as exc:
                failure.append(exc)
            finally:
                thread_engine.close()

        thread = threading.Thread(target=run_worker_in_own_thread_connection)
        thread.start()
        deadline = time.time() + 2
        while time.time() < deadline and db.get_task(task)['state'] != 'IN_IMPLEMENT':
            time.sleep(0.01)
        self.assertEqual(db.get_task(task)['state'], 'IN_IMPLEMENT')
        time.sleep(0.30)
        competitor = ExactV7SharedEngine(self.binding, self.bridge_db, self.provider_db)
        try:
            with self.assertRaises(db.LostLeaseError):
                competitor.reclaim_expired(task, 'competitor', lease_seconds=0.25)
        finally:
            competitor.close()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failure, [])
        self.assertEqual(result, [(task, 'DONE')])

    def test_crash_after_durable_provider_receipt_reuses_same_operation(self):
        task = self.engine.submit('core', 'implement', 'receipt crash')
        generation = db.claim_task(task, 'dead-worker', lease_seconds=0.12)
        db.transition(task, 'IN_IMPLEMENT', actor='seed', event_type='START', fencing=('dead-worker', generation))
        operation = f'lpw9:{task}:implement:0'
        job = self.engine._job(task, 'IMPLEMENT', 0, operation)
        request = provider_request_from_job(job, self.engine.manifest)
        result = {
            'status': 'READY', 'candidate_head': HEAD, 'diff_lines': 0, 'cost_microusd': 0,
            'evidence_ref': f'local-v9:{task}:implement:0',
        }
        store = ProviderAdapterReceiptStore(self.provider_db, self.engine.manifest)
        try:
            store.execute_local_once(operation, request, DeterministicLocalAdapter({'IMPLEMENT': {'1': result}}))
            self.assertEqual(store.execution_count(operation), 1)
        finally:
            store.close()
        time.sleep(0.15)
        fresh_engine = ExactV7SharedEngine(self.binding, self.bridge_db, self.provider_db)
        try:
            worker = LocalPersistentWorker(fresh_engine, WorkerConfig(lease_seconds=.25, heartbeat_seconds=.04, poll_seconds=.01))
            self.assertEqual(worker.step(), (task, 'DONE'))
        finally:
            fresh_engine.close()
        store = ProviderAdapterReceiptStore(self.provider_db, self.engine.manifest)
        try:
            self.assertEqual(store.execution_count(operation), 1)
        finally:
            store.close()

    def test_two_processes_divide_preexisting_tasks_without_duplicate_authority(self):
        tasks = [self.engine.submit('core', 'implement', f'job-{i}', priority=i) for i in range(4)]
        p1 = mp.Process(target=_process_worker, args=(self.task_db, self.bridge_db, self.provider_db, 8))
        p2 = mp.Process(target=_process_worker, args=(self.task_db, self.bridge_db, self.provider_db, 8))
        p1.start(); p2.start(); p1.join(8); p2.join(8)
        self.assertEqual(p1.exitcode, 0); self.assertEqual(p2.exitcode, 0)
        self.assertTrue(all(db.get_task(task)['state'] == 'DONE' for task in tasks))
        conn = db._conn()
        try:
            for task in tasks:
                claims = conn.execute("SELECT COUNT(*) FROM events WHERE task_id=? AND event_type='LEASE_CLAIMED'", (task,)).fetchone()[0]
                self.assertEqual(claims, 1)
        finally:
            conn.close()

    def test_process_crash_then_generation_bump_reclaim_converges(self):
        task = self.engine.submit('core', 'implement', 'crash then reclaim')
        p1 = mp.Process(target=_process_worker, args=(self.task_db, self.bridge_db, self.provider_db, 1, 5.0))
        p1.start()
        deadline = time.time() + 3
        while time.time() < deadline:
            snap = db.get_task(task)
            if snap['state'] == 'IN_IMPLEMENT' and snap['claimed_by']:
                break
            time.sleep(0.02)
        first = db.get_task(task)
        self.assertEqual(first['state'], 'IN_IMPLEMENT')
        first_generation = first['claim_generation']
        p1.terminate(); p1.join(3)
        time.sleep(0.32)
        p2 = mp.Process(target=_process_worker, args=(self.task_db, self.bridge_db, self.provider_db, 4))
        p2.start(); p2.join(8)
        self.assertEqual(p2.exitcode, 0)
        final = db.get_task(task)
        self.assertEqual(final['state'], 'DONE')
        self.assertGreater(final['claim_generation'], first_generation)


if __name__ == '__main__':
    unittest.main()
