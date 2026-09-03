import inspect
import json
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
        self.socket = os.path.join(self.tmp.name, 'multiverse-v10-worker.sock')
        self.engine = ExactV7SharedEngine(self.binding, self.bridge, self.provider)
        self.proc = subprocess.Popen([
            sys.executable, BROKER,
            '--socket', self.socket, '--task-db', self.task_db,
            '--bridge-db', self.bridge, '--provider-db', self.provider,
            '--candidate-branch', BRANCH, '--candidate-head', HEAD,
            '--lease', '0.30', '--heartbeat', '0.05', '--poll', '0.01',
            '--max-requests', '100'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 5
        while time.time() < deadline and not os.path.exists(self.socket):
            if self.proc.poll() is not None:
                raise AssertionError(self.proc.stderr.read())
            time.sleep(0.01)
        self.client = ProcessIsolatedWorkerClient(ClientConfig(self.socket, 2.0))

    def tearDown(self):
        try:
            if self.proc.poll() is None:
                try: self.client.stop()
                except Exception: pass
                self.proc.terminate()
                self.proc.wait(timeout=3)
        finally:
            self.engine.close()
            config.DB_PATH = self.old_db
            self.tmp.cleanup()

    def raw(self, payload: bytes):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2); s.connect(self.socket); s.sendall(payload)
            return s.recv(4096)

    def test_distinct_process_and_client_has_no_engine_globals(self):
        ping = self.client.ping()
        self.assertNotEqual(ping['broker_pid'], os.getpid())
        source = inspect.getsource(client_module)
        for banned in ('ExactV7SharedEngine', 'LocalPersistentWorker', 'create_task(', '.submit(', 'pickle', 'marshal', 'eval(', 'exec('):
            self.assertNotIn(banned, source)
        values = list(ProcessIsolatedWorkerClient._request.__globals__.values())
        self.assertFalse(any(isinstance(v, type) and v.__name__ == 'ExactV7SharedEngine' for v in values))
        self.assertFalse(any(name in vars(self.client) for name in ('engine','binding','bridge_db','provider_db','task_db')))

    def test_client_monkeypatch_cannot_expand_broker_protocol(self):
        old = client_module.ALLOWED_OPS
        try:
            ProcessIsolatedWorkerClient._request.__globals__['ALLOWED_OPS'] = frozenset({'PING','STEP','STOP','SUBMIT','create_task'})
            with self.assertRaises(IPCError): self.client._request('SUBMIT')
            with self.assertRaises(IPCError): self.client._request('create_task')
        finally:
            ProcessIsolatedWorkerClient._request.__globals__['ALLOWED_OPS'] = old

    def test_strict_schema_unknown_extra_duplicate_and_malformed_fail_closed(self):
        before = db.list_tasks()
        bad = [
            b'{not-json}\n',
            b'{"v":1,"op":"SUBMIT","request_id":"x"}\n',
            b'{"v":1,"op":"PING","request_id":"x","extra":1}\n',
            b'{"v":1,"op":"PING","op":"STEP","request_id":"x"}\n',
            b'[]\n',
        ]
        for frame in bad:
            body = self.raw(frame)
            self.assertIn(b'"ok":false', body)
        self.assertEqual(before, db.list_tasks())

    def test_oversized_frame_fails_closed(self):
        before = db.list_tasks()
        body = self.raw(b'{' + b'x' * 5000 + b'}\n')
        self.assertIn(b'"ok":false', body)
        self.assertEqual(before, db.list_tasks())

    def test_preexisting_core_and_keirin_tasks_use_same_client_broker_path(self):
        core = self.engine.submit('core','implement','preexisting core')
        keirin = self.engine.submit('keirin','research','PIT-safe preexisting keirin')
        a = self.client.step(); b = self.client.step()
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
