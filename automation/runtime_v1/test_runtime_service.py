import os
import tempfile
import unittest

import config
import db
from runtime_service import RuntimeService
from runtime_supervisor import KillSwitchEngaged, RuntimeGateError, RuntimeSupervisor, SupervisorStore, WorkerIdentityVerifier
from shared_engine_driver import SharedEngineRuntimeDriver


class OpenTestStore(SupervisorStore):
    def kill_switch_engaged(self):
        return False


class RuntimeServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_engine_db = config.DB_PATH
        config.DB_PATH = os.path.join(self.tmp.name, "engine.db")
        db.init_schema()
        self.runtime_db = os.path.join(self.tmp.name, "runtime.db")
        self.now = 1_800_000_000
        self.verifier = WorkerIdentityVerifier(b"r" * 32, clock=lambda: self.now)
        self.token = self.verifier.mint_for_test("scheduler-1", issued_at=self.now, nonce="service")

    def tearDown(self):
        config.DB_PATH = self.old_engine_db
        self.tmp.cleanup()

    def test_production_kill_switch_blocks_before_task_mutation(self):
        tid = db.create_task("core", "x", task_type="implement")
        supervisor = RuntimeSupervisor(SupervisorStore(self.runtime_db), self.verifier)
        service = RuntimeService(supervisor, SharedEngineRuntimeDriver(), idle_seconds=0)
        with self.assertRaises(KillSwitchEngaged):
            service.cycle(self.token)
        task = db.get_task(tid)
        self.assertEqual(task["state"], "PENDING")
        self.assertIsNone(task["claimed_by"])

    def test_open_test_harness_claims_exact_task_then_idles(self):
        tid = db.create_task("core", "x", task_type="implement", priority=5)
        supervisor = RuntimeSupervisor(OpenTestStore(self.runtime_db), self.verifier)
        service = RuntimeService(supervisor, SharedEngineRuntimeDriver(), idle_seconds=0)
        out = service.run_bounded_for_test(self.token, cycles=2)
        self.assertEqual(out[0]["status"], "CLAIMED_FOR_IMPLEMENT")
        self.assertEqual(out[0]["task_id"], tid)
        self.assertEqual(out[1]["status"], "IDLE")
        task = db.get_task(tid)
        self.assertEqual(task["state"], "IN_IMPLEMENT")
        self.assertEqual(task["claimed_by"], "scheduler-1")
        cp = supervisor.store.get_checkpoint("scheduler:last_cycle")
        self.assertEqual(cp["status"], "IDLE")

    def test_exact_driver_type_required(self):
        class EvilDriver(SharedEngineRuntimeDriver):
            pass
        supervisor = RuntimeSupervisor(OpenTestStore(self.runtime_db), self.verifier)
        with self.assertRaises(RuntimeGateError):
            RuntimeService(supervisor, EvilDriver())

    def test_idle_and_test_cycles_are_bounded(self):
        supervisor = RuntimeSupervisor(OpenTestStore(self.runtime_db), self.verifier)
        with self.assertRaises(RuntimeGateError):
            RuntimeService(supervisor, SharedEngineRuntimeDriver(), idle_seconds=61)
        service = RuntimeService(supervisor, SharedEngineRuntimeDriver(), idle_seconds=0)
        for bad in (0, 101, True, -1):
            with self.assertRaises(RuntimeGateError):
                service.run_bounded_for_test(self.token, cycles=bad)


if __name__ == "__main__":
    unittest.main()
