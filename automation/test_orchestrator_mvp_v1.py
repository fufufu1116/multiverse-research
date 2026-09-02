import pathlib
import tempfile
import unittest

from orchestrator_mvp_v1 import (
    InjectedCrash,
    Orchestrator,
    OrchestratorStore,
    ScriptedRoleWorker,
    demo_spec,
    run_demo,
)


class OrchestratorMVPTests(unittest.TestCase):
    def db(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return pathlib.Path(td.name) / "state.sqlite"

    def test_end_to_end_auto_fix_done_zero_owner_transport(self):
        out = run_demo(self.db())
        self.assertEqual(out["final_state"], "DONE")
        result = out["task"]["result"]
        self.assertEqual(result["owner_copy_paste_count"], 0)
        self.assertEqual(result["owner_continue_prompt_count"], 0)
        self.assertEqual(result["owner_keep_alive_count"], 0)
        self.assertEqual(result["semantic_retries"], 1)
        types = [e["event_type"] for e in out["events"]]
        self.assertIn("LAB_FIX_REQUIRED", types)
        self.assertIn("AUDITOR_PASS_DONE", types)

    def test_crash_recovery_does_not_consume_semantic_retry(self):
        path = self.db()
        spec = demo_spec("crash-task")
        worker = ScriptedRoleWorker({
            "IMPLEMENT": [{"status": "READY", "diff_lines": 1, "cost_microusd": 0, "evidence_ref": "i"}],
            "LAB": [{"verdict": "PASS", "evidence_ref": "l"}],
            "AUDIT": [{"verdict": "PASS", "evidence_ref": "a"}],
        })
        store = OrchestratorStore(path)
        store.create_task(spec)
        orch = Orchestrator(store, worker)
        with self.assertRaises(InjectedCrash):
            orch.step(spec["task_id"], crash_after_start="IMPLEMENT")
        task = store.get(spec["task_id"])
        self.assertEqual(task["state"], "IN_IMPLEMENT")
        self.assertIsNotNone(task["active_claim"])
        recovered = store.recover_stale(
            at=task["heartbeat_at"] + spec["budgets"]["heartbeat_timeout_seconds"] + 1
        )
        self.assertEqual(recovered, [spec["task_id"]])
        self.assertEqual(store.get(spec["task_id"])["semantic_retry_count"], 0)
        self.assertEqual(orch.run_until_terminal(spec["task_id"]), "DONE")
        store.close()

    def test_repeated_failure_fingerprint_routes_owner_gate(self):
        path = self.db()
        spec = demo_spec("loop-task")
        worker = ScriptedRoleWorker({
            "IMPLEMENT": [
                {"status": "BAD", "diff_lines": 1, "cost_microusd": 0, "evidence_ref": "x"},
                {"status": "BAD", "diff_lines": 1, "cost_microusd": 0, "evidence_ref": "x"},
            ]
        })
        store = OrchestratorStore(path)
        store.create_task(spec)
        orch = Orchestrator(store, worker)
        self.assertEqual(orch.step(spec["task_id"]), "MECH_GATE_FAIL")
        self.assertEqual(orch.step(spec["task_id"]), "OWNER_GATE")
        self.assertEqual(
            store.get(spec["task_id"])["owner_gate_reason"],
            "REPEATED_FAILURE_FINGERPRINT",
        )
        store.close()

    def test_transient_failure_is_recovery_not_semantic_retry(self):
        path = self.db()
        spec = demo_spec("transient-task")
        worker = ScriptedRoleWorker({
            "IMPLEMENT": [
                {"raise": "TRANSIENT", "detail": "network blip"},
                {"status": "READY", "diff_lines": 1, "cost_microusd": 0, "evidence_ref": "i"},
            ],
            "LAB": [{"verdict": "PASS", "evidence_ref": "l"}],
            "AUDIT": [{"verdict": "PASS", "evidence_ref": "a"}],
        })
        store = OrchestratorStore(path)
        store.create_task(spec)
        orch = Orchestrator(store, worker)
        self.assertEqual(orch.step(spec["task_id"]), "IN_IMPLEMENT")
        task = store.get(spec["task_id"])
        self.assertEqual(task["semantic_retry_count"], 0)
        self.assertEqual(task["transient_retry_count"], 1)
        self.assertEqual(orch.run_until_terminal(spec["task_id"]), "DONE")
        store.close()

    def test_safety_unknown_fails_closed_to_owner_gate(self):
        path = self.db()
        spec = demo_spec("unsafe-task")
        spec["safety"]["unknown_risk"] = True
        worker = ScriptedRoleWorker({})
        store = OrchestratorStore(path)
        store.create_task(spec)
        self.assertEqual(
            Orchestrator(store, worker).step(spec["task_id"]),
            "OWNER_GATE",
        )
        self.assertIn("unknown_risk", store.get(spec["task_id"])["owner_gate_reason"])
        store.close()

    def test_candidate_rollback_is_terminal_and_nonproduction(self):
        path = self.db()
        spec = demo_spec("rollback-task")
        worker = ScriptedRoleWorker({})
        store = OrchestratorStore(path)
        store.create_task(spec)
        orch = Orchestrator(store, worker)
        self.assertEqual(orch.rollback(spec["task_id"], "test rollback"), "ROLLED_BACK")
        task = store.get(spec["task_id"])
        self.assertEqual(task["state"], "ROLLED_BACK")
        self.assertFalse(task["result"]["production_or_stable_mutation"])
        store.close()


if __name__ == "__main__":
    unittest.main()
