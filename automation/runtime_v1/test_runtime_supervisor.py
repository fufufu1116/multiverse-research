import os
import tempfile
import unittest

from runtime_supervisor import (
    AUTHORITY, KillSwitchEngaged, ReviewRoleBoundaryError, RuntimeGateError,
    RuntimeSupervisor, SupervisorStore, WorkerIdentityError, WorkerIdentityVerifier,
)


class OpenTestStore(SupervisorStore):
    """Test-only harness outside production module; it cannot alter persisted kill_switch."""
    def kill_switch_engaged(self):
        return False


class RuntimeSupervisorV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "runtime.db")
        self.now = 1_800_000_000
        self.clock = lambda: self.now
        self.key = b"k" * 32
        self.verifier = WorkerIdentityVerifier(self.key, clock=self.clock)
        self.store = SupervisorStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def token(self, worker="worker-1"):
        return self.verifier.mint_for_test(worker, issued_at=self.now, nonce="n-1")

    def open_store(self):
        return OpenTestStore(self.db)

    def test_authority_is_default_deny(self):
        self.assertTrue(AUTHORITY)
        self.assertTrue(all(v is False for v in AUTHORITY.values()))

    def test_kill_switch_defaults_engaged_and_blocks_step(self):
        s = RuntimeSupervisor(self.store, self.verifier)
        self.assertTrue(self.store.kill_switch_engaged())
        with self.assertRaises(KillSwitchEngaged):
            s.step(self.token(), "IMPLEMENT", "k", {"ok": True})
        self.assertIsNone(self.store.get_checkpoint("k"))

    def test_production_store_exposes_no_kill_switch_disable_method(self):
        self.assertFalse(hasattr(self.store, "set_test_kill_switch"))
        self.assertFalse(hasattr(self.store, "disable_kill_switch"))
        self.assertTrue(self.store.kill_switch_engaged())

    def test_store_binding_rejects_persisted_kill_switch_tamper(self):
        import sqlite3
        c = sqlite3.connect(self.db)
        with c:
            c.execute("UPDATE meta SET v='0' WHERE k='kill_switch'")
        c.close()
        with self.assertRaises(RuntimeGateError):
            SupervisorStore(self.db)

    def test_identity_tamper_and_expiry_fail_closed(self):
        token = self.token()
        with self.assertRaises(WorkerIdentityError):
            self.verifier.verify(token[:-1] + ("0" if token[-1] != "0" else "1"))
        old = self.verifier.mint_for_test("worker-1", issued_at=self.now - 301, nonce="old")
        with self.assertRaises(WorkerIdentityError):
            self.verifier.verify(old)

    def test_success_checkpoint_survives_restart(self):
        store1 = self.open_store()
        s1 = RuntimeSupervisor(store1, self.verifier)
        out = s1.step(self.token(), "IMPLEMENT", "task-1", {"phase": "done", "n": 1})
        self.assertEqual(out["phase"], "done")
        cp = store1.get_checkpoint("task-1")
        self.assertEqual(cp, {"n": 1, "phase": "done"})
        store2 = self.open_store()
        s2 = RuntimeSupervisor(store2, self.verifier)
        self.assertGreater(s2.incarnation, s1.incarnation)
        self.assertEqual(s2.store.get_checkpoint("task-1"), cp)

    def test_unserializable_payload_is_journaled_without_false_checkpoint(self):
        store = self.open_store()
        s = RuntimeSupervisor(store, self.verifier)
        with self.assertRaises(TypeError):
            s.step(self.token(), "RECOVERY", "crash-key", {"bad": {1, 2}})
        self.assertIsNone(store.get_checkpoint("crash-key"))
        events = [e["event_type"] for e in store.events()]
        self.assertIn("STEP_FAILED", events)
        self.assertNotIn("STEP_COMPLETED", events)

    def test_review_roles_cannot_be_self_manufactured(self):
        store = self.open_store()
        s = RuntimeSupervisor(store, self.verifier)
        for role in ("LAB", "AUDIT", "INDEPENDENT_LAB", "INDEPENDENT_AUDITOR"):
            with self.assertRaises(ReviewRoleBoundaryError):
                s.step(self.token(), role, "x", {"verdict": "PASS"})

    def test_bounded_loop_rejects_unbounded_or_bool(self):
        store = self.open_store()
        s = RuntimeSupervisor(store, self.verifier)
        for bad in (0, 101, True, -1):
            with self.assertRaises(RuntimeGateError):
                s.run_bounded(self.token(), "CHECKPOINT", "loop", {"ok": True}, max_steps=bad)
        out = s.run_bounded(self.token(), "CHECKPOINT", "loop", {"ok": True}, max_steps=3)
        self.assertEqual(len(out), 3)

    def test_heartbeat_requires_valid_identity_and_open_test_harness(self):
        s = RuntimeSupervisor(self.store, self.verifier)
        with self.assertRaises(KillSwitchEngaged):
            s.heartbeat(self.token())
        open_s = RuntimeSupervisor(self.open_store(), self.verifier)
        worker = open_s.heartbeat(self.token())
        self.assertEqual(worker.worker_id, "worker-1")

    def test_step_accepts_inert_data_not_executable_callback(self):
        store = self.open_store()
        s = RuntimeSupervisor(store, self.verifier)
        with self.assertRaises(RuntimeGateError):
            s.step(self.token(), "IMPLEMENT", "callable", lambda: {"ok": True})
        self.assertIsNone(store.get_checkpoint("callable"))


if __name__ == "__main__":
    unittest.main()
