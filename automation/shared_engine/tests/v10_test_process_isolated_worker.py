import concurrent.futures
import inspect
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import IntegrationBinding
import process_isolated_worker_v10 as client_module
from process_isolated_worker_broker_v10 import (
    DurableReplayStore,
    ProtocolError,
    REPLAY_CAPACITY,
)
from process_isolated_worker_v10 import ClientConfig, IPCError, ProcessIsolatedWorkerClient

HEAD = 'a' * 40
BRANCH = 'agent/automation-shared-engine-process-isolated-worker-v10-test'
BROKER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'process_isolated_worker_broker_v10.py')


class ProcessIsolatedWorkerV10Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = config.DB_PATH
        self.task_db = os.path.join(self.tmp.name, 'task.db')
        config.DB_PATH = self.task_db
        db.init_schema()
        self.binding = IntegrationBinding(CANONICAL_MAIN, BRANCH, HEAD, V7_HEAD)
        self.bridge = os.path.join(self.tmp.name, 'bridge.db')
        self.provider = os.path.join(self.tmp.name, 'provider.db')
        self.replay = os.path.join(self.tmp.name, 'ipc-replay.db')
        self.socket = os.path.join(self.tmp.name, 'multiverse-v10-worker.sock')
        self.engine = ExactV7SharedEngine(self.binding, self.bridge, self.provider)
        self.proc = None
        self.start_broker()
        self.client = ProcessIsolatedWorkerClient(ClientConfig(self.socket, 2.0))

    def start_broker(self):
        try:
            os.unlink(self.socket)
        except FileNotFoundError:
            pass
        self.proc = subprocess.Popen([
            sys.executable, BROKER, '--socket', self.socket, '--task-db', self.task_db,
            '--bridge-db', self.bridge, '--provider-db', self.provider, '--replay-db', self.replay,
            '--candidate-branch', BRANCH, '--candidate-head', HEAD,
            '--lease', '0.30', '--heartbeat', '0.05', '--poll', '0.01', '--max-requests', '100'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 5
        while time.time() < deadline and not os.path.exists(self.socket):
            if self.proc.poll() is not None:
                raise AssertionError(self.proc.stderr.read())
            time.sleep(0.01)
        if not os.path.exists(self.socket):
            raise AssertionError('broker socket did not appear')

    def terminate_broker(self):
        proc = self.proc
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=3)
        if proc.stderr:
            proc.stderr.close()
        self.proc = None
        try:
            os.unlink(self.socket)
        except FileNotFoundError:
            pass

    def restart_broker(self):
        self.terminate_broker()
        self.start_broker()
        self.client = ProcessIsolatedWorkerClient(ClientConfig(self.socket, 2.0))

    def tearDown(self):
        try:
            if self.proc is not None and self.proc.poll() is None:
                try:
                    self.client.stop()
                except Exception:
                    pass
            self.terminate_broker()
        finally:
            self.engine.close()
            config.DB_PATH = self.old_db
            self.tmp.cleanup()

    def raw(self, payload: bytes):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(self.socket)
            s.sendall(payload)
            return s.recv(4096)

    def test_distinct_process_and_client_has_no_engine_globals(self):
        ping = self.client.ping()
        self.assertNotEqual(ping['broker_pid'], os.getpid())
        source = inspect.getsource(client_module)
        for banned in ('ExactV7SharedEngine', 'LocalPersistentWorker', 'create_task(', '.submit(', 'pickle', 'marshal', 'eval(', 'exec('):
            self.assertNotIn(banned, source)
        values = list(ProcessIsolatedWorkerClient._request.__globals__.values())
        self.assertFalse(any(isinstance(v, type) and v.__name__ == 'ExactV7SharedEngine' for v in values))
        self.assertFalse(any(name in vars(self.client) for name in ('engine','binding','bridge_db','provider_db','task_db','replay_db')))

    def test_client_monkeypatch_cannot_expand_broker_protocol(self):
        old = client_module.ALLOWED_OPS
        try:
            ProcessIsolatedWorkerClient._request.__globals__['ALLOWED_OPS'] = frozenset({'PING','STEP','STOP','SUBMIT','create_task'})
            with self.assertRaises(IPCError):
                self.client._request('SUBMIT')
            with self.assertRaises(IPCError):
                self.client._request('create_task')
        finally:
            ProcessIsolatedWorkerClient._request.__globals__['ALLOWED_OPS'] = old

    def test_strict_schema_unknown_extra_duplicate_and_malformed_fail_closed_without_capacity_use(self):
        before_tasks = db.list_tasks()
        store = DurableReplayStore(self.replay)
        before_count = store.count()
        for frame in (
            b'{not-json}\n',
            b'{"v":1,"op":"SUBMIT","request_id":"x"}\n',
            b'{"v":1,"op":"PING","request_id":"x","extra":1}\n',
            b'{"v":1,"op":"PING","op":"STEP","request_id":"x"}\n',
            b'[]\n',
        ):
            self.assertIn(b'"ok":false', self.raw(frame))
        self.assertEqual(before_tasks, db.list_tasks())
        self.assertEqual(before_count, store.count())

    def test_oversized_frame_fails_closed_without_capacity_use(self):
        store = DurableReplayStore(self.replay)
        before = store.count()
        before_tasks = db.list_tasks()
        self.assertIn(b'"ok":false', self.raw(b'{' + b'x' * 5000 + b'}\n'))
        self.assertEqual(before, store.count())
        self.assertEqual(before_tasks, db.list_tasks())

    def test_replayed_request_id_is_rejected_before_second_authoritative_step(self):
        first_task = self.engine.submit('core', 'implement', 'replay first')
        second_task = self.engine.submit('core', 'implement', 'replay second')
        frame = b'{"v":1,"op":"STEP","request_id":"replay-step-1"}\n'
        first = self.raw(frame)
        self.assertIn(b'"ok":true', first)
        second = self.raw(frame)
        self.assertIn(b'"ok":false', second)
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', second)
        states = {db.get_task(first_task)['state'], db.get_task(second_task)['state']}
        self.assertEqual(states, {'DONE', 'PENDING'})

    def test_replay_persists_across_broker_restart_after_step(self):
        first_task = self.engine.submit('core', 'implement', 'restart replay first')
        second_task = self.engine.submit('core', 'implement', 'restart replay second')
        frame = b'{"v":1,"op":"STEP","request_id":"restart-step-1"}\n'
        self.assertIn(b'"ok":true', self.raw(frame))
        states_before = {db.get_task(first_task)['state'], db.get_task(second_task)['state']}
        self.assertEqual(states_before, {'DONE', 'PENDING'})
        self.restart_broker()
        replay = self.raw(frame)
        self.assertIn(b'"ok":false', replay)
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', replay)
        states_after = {db.get_task(first_task)['state'], db.get_task(second_task)['state']}
        self.assertEqual(states_after, {'DONE', 'PENDING'})

    def test_durable_reservation_before_dispatch_survives_restart(self):
        task = self.engine.submit('core', 'implement', 'reserved but not dispatched')
        self.terminate_broker()
        store = DurableReplayStore(self.replay)
        store.reserve({'v': 1, 'op': 'STEP', 'request_id': 'reserved-before-dispatch'})
        self.start_broker()
        self.client = ProcessIsolatedWorkerClient(ClientConfig(self.socket, 2.0))
        replay = self.raw(b'{"v":1,"op":"STEP","request_id":"reserved-before-dispatch"}\n')
        self.assertIn(b'"ok":false', replay)
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', replay)
        self.assertEqual(db.get_task(task)['state'], 'PENDING')
        fresh = self.raw(b'{"v":1,"op":"STEP","request_id":"fresh-after-lost-pulse"}\n')
        self.assertIn(b'"ok":true', fresh)
        self.assertEqual(db.get_task(task)['state'], 'DONE')

    def test_conflicting_reuse_of_request_id_is_rejected_across_restart(self):
        first = self.raw(b'{"v":1,"op":"PING","request_id":"same-id"}\n')
        self.assertIn(b'"ok":true', first)
        self.restart_broker()
        second = self.raw(b'{"v":1,"op":"STEP","request_id":"same-id"}\n')
        self.assertIn(b'"ok":false', second)
        self.assertIn(b'V10_REQUEST_ID_CONFLICT', second)

    def test_ping_and_stop_ids_are_durable_replay_denied(self):
        self.assertIn(b'"ok":true', self.raw(b'{"v":1,"op":"PING","request_id":"ping-id"}\n'))
        self.restart_broker()
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', self.raw(b'{"v":1,"op":"PING","request_id":"ping-id"}\n'))
        self.assertIn(b'"ok":true', self.raw(b'{"v":1,"op":"STOP","request_id":"stop-id"}\n'))
        self.restart_broker()
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', self.raw(b'{"v":1,"op":"STOP","request_id":"stop-id"}\n'))

    def test_concurrent_same_id_durable_reservation_has_single_winner(self):
        self.terminate_broker()
        a = DurableReplayStore(self.replay)
        b = DurableReplayStore(self.replay)
        request = {'v': 1, 'op': 'STEP', 'request_id': 'concurrent-one-winner'}

        def reserve(store):
            try:
                store.reserve(request)
                return 'ok'
            except ProtocolError as exc:
                return str(exc)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, (a, b)))
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('V10_REQUEST_REPLAY_DENIED'), 1)

    def test_replay_capacity_is_persistent_non_evicting_and_fail_closed(self):
        self.terminate_broker()
        store = DurableReplayStore(self.replay)
        for i in range(REPLAY_CAPACITY):
            store.reserve({'v': 1, 'op': 'PING', 'request_id': f'cap-{i}'})
        self.assertEqual(store.count(), REPLAY_CAPACITY)
        with self.assertRaisesRegex(ProtocolError, 'V10_REPLAY_STORE_FULL'):
            store.reserve({'v': 1, 'op': 'PING', 'request_id': 'capacity-new'})
        self.start_broker()
        self.client = ProcessIsolatedWorkerClient(ClientConfig(self.socket, 2.0))
        response = self.raw(b'{"v":1,"op":"PING","request_id":"capacity-new"}\n')
        self.assertIn(b'"ok":false', response)
        self.assertIn(b'V10_REPLAY_STORE_FULL', response)
        self.restart_broker()
        response2 = self.raw(b'{"v":1,"op":"PING","request_id":"capacity-new-2"}\n')
        self.assertIn(b'V10_REPLAY_STORE_FULL', response2)
        replay = self.raw(b'{"v":1,"op":"PING","request_id":"cap-0"}\n')
        self.assertIn(b'V10_REQUEST_REPLAY_DENIED', replay)

    def test_preexisting_core_and_keirin_tasks_use_same_client_broker_path(self):
        core = self.engine.submit('core','implement','preexisting core')
        keirin = self.engine.submit('keirin','research','PIT-safe preexisting keirin')
        a = self.client.step()
        b = self.client.step()
        self.assertEqual({a['task_id'], b['task_id']}, {core, keirin})
        self.assertEqual(db.get_task(core)['state'], 'DONE')
        self.assertEqual(db.get_task(keirin)['state'], 'DONE')

    def test_no_task_creation_opcode_and_bounds(self):
        self.assertEqual(client_module.ALLOWED_OPS, frozenset({'PING','STEP','STOP'}))
        with self.assertRaisesRegex(ValueError, 'V10_RUN_CYCLE_BOUND'):
            self.client.run(max_cycles=1001)
        with self.assertRaisesRegex(ValueError, 'V10_UNIX_SOCKET_PATH_BOUND'):
            ClientConfig('/' + 'x'*101).validate()


if __name__ == '__main__':
    unittest.main()
