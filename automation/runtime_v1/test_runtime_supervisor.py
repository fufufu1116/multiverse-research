import os
import tempfile
import unittest

from runtime_supervisor import (
    AUTHORITY, KillSwitchEngaged, ReviewRoleBoundaryError, RuntimeGateError,
    RuntimeSupervisor, SupervisorStore, WorkerIdentityError, WorkerIdentityVerifier,
)


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

    def arm_test_mode(self):
        self.store.set_test_kill_switch(False, authority="TEST_ONLY_LOCAL_CANDIDATE")

    def test_authority_is_default_deny(self):
        self.assertTrue(AUTHORITY)
        self.assertTrue(all(v is False for v in AUTHORITY.values()))

    def test_kill_switch_defaults_engaged_and_blocks_step(self):
        s = RuntimeSupervisor(self.store, self.verifier)
        self.assertTrue(self.store.kill_switch_engaged())
        with self.assertRaises(KillSwitchEngaged):
            s.step(self.token(), "IMPLEMENT", "k", lambda: {"ok": True})
        self.assertIsNone(self.store.get_checkpoint("k"))

    def test_kill_switch_cannot_be_disabled_without_test_authority(self):
        with self.assertRaises(RuntimeGateError):
            self.store.set_test_kill_switch(False, authority="wrong")
        self.assertTrue(self.store.kill_switch_engaged())

    def test_identity_tamper_and_expiry_fail_closed(self):
        token = self.token()
        with self.assertRaises(WorkerIdentityError):
            self.verifier.verify(token[:-1] + ("0" if token[-1] != "0" else "1"))
        old = self.verifier.mint_for_test("worker-1", issued_at=self.now - 301, nonce="old")
        with self.assertRaises(WorkerIdentityError):
            self.verifier.verify(old)

    def test_success_checkpoint_survives_restart(self):
        self.arm_test_mode()
        s1 = RuntimeSupervisor(self.store, self.verifier)
        out = s1.step(self.token(), "IMPLEMENT", "task-1", lambda: {"phase": "done", "n": 1})
        self.assertEqual(out["phase"], "done")
        cp = self.store.get_checkpoint("task-1")
        self.assertEqual(cp, {"n": 1, "phase": "done"})
        s2 = RuntimeSupervisor(SupervisorStore(self.db), self.verifier)
        self.assertGreater(s2.incarnation, s1.incarnation)
        self.assertEqual(s2.store.get_checkpoint("task-1"), cp)

    def test_crash_is_journaled_without_false_checkpoint(self):
        self.arm_test_mode()
        s = RuntimeSupervisor(self.store, self.verifier)
        def boom():
            raise ValueError("boom")
        with self.assertRaises(ValueError):
            s.step(self.token(), "RECOVERY", "crash-key", boom)
        self.assertIsNone(self.store.get_checkpoint("crash-key"))
        events = [e["event_type"] for e in self.store.events()]
        self.assertIn("STEP_FAILED", events)
        self.assertNotIn("STEP_COMPLETED", events)

    def test_review_roles_cannot_be_self_manufactured(self):
        self.arm_test_mode()
        s = RuntimeSupervisor(self.store, self.verifier)
        for role in ("LAB", "AUDIT", "INDEPENDENT_LAB", "INDEPENDENT_AUDITOR"):
            with self.assertRaises(ReviewRoleBoundaryError):
                s.step(self.token(), role, "x", lambda: {"verdict": "PASS"})

    def test_bounded_loop_rejects_unbounded_or_bool(self):
        self.arm_test_mode()
        s = RuntimeSupervisor(self.store, self.verifier)
        for bad in (0, 101, True, -1):
            with self.assertRaises(RuntimeGateError):
                s.run_bounded(self.token(), "CHECKPOINT", "loop", lambda: {"ok": True}, max_steps=bad)
        out = s.run_bounded(self.token(), "CHECKPOINT", "loop", lambda: {"ok": True}, max_steps=3)
        self.assertEqual(len(out), 3)

    def test_heartbeat_requires_valid_identity_and_open_kill_switch(self):
        s = RuntimeSupervisor(self.store, self.verifier)
        with self.assertRaises(KillSwitchEngaged):
            s.heartbeat(self.token())
        self.arm_test_mode()
        worker = s.heartbeat(self.token())
        self.assertEqual(worker.worker_id, "worker-1")


if __name__ == "__main__":
    unittest.main()
