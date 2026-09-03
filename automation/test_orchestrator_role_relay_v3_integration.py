#!/usr/bin/env python3
import multiprocessing as mp
import os
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import Orchestrator, OrchestratorStore, StaticBindingVerifier, demo_spec
from orchestrator_role_relay_v3 import CANDIDATE_BRANCH, RelayRoleWorker, fixture_process_one


def _agent_loop(relay_db, receipt_db, script, expected_jobs):
    completed = 0
    deadline = time.time() + 20
    while completed < expected_jobs and time.time() < deadline:
        out = fixture_process_one(relay_db, receipt_db, "fixture-agent", script, lease_seconds=2)
        if out == "COMPLETE":
            completed += 1
        else:
            time.sleep(0.01)
    if completed != expected_jobs:
        raise SystemExit(91)


class RelayV3IntegrationTests(unittest.TestCase):
    def test_exact_head_full_orchestrator_e2e(self):
        head = os.environ.get("MULTIVERSE_EXPECTED_HEAD")
        main = os.environ.get("MULTIVERSE_CANONICAL_MAIN")
        if not head or not main:
            self.skipTest("exact-head environment supplied by mechanical gate")
        self.assertEqual(len(head), 40)
        self.assertEqual(len(main), 40)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay.sqlite"
            receipt_db = root / "receipt.sqlite"
            orch_db = root / "orch.sqlite"
            script = {
                "IMPLEMENT": {
                    "1": {"status": "READY", "candidate_head": head, "diff_lines": 10, "cost_microusd": 0, "evidence_ref": "relay-impl-1"},
                    "2": {"status": "READY", "candidate_head": head, "diff_lines": 11, "cost_microusd": 0, "evidence_ref": "relay-impl-2"},
                },
                "LAB": {
                    "1": {"verdict": "FIX_REQUIRED", "reviewed_head": head, "code": "RELAY_DEMO_FIX", "detail": "deterministic relay remediation", "evidence_ref": "relay-lab-fix"},
                    "2": {"verdict": "PASS", "reviewed_head": head, "evidence_ref": "relay-lab-pass"},
                },
                "AUDIT": {
                    "2": {"verdict": "PASS", "reviewed_head": head, "evidence_ref": "relay-audit-pass"},
                },
            }
            ctx = mp.get_context("fork")
            agent = ctx.Process(target=_agent_loop, args=(str(relay_db), str(receipt_db), script, 5))
            agent.start()
            spec = demo_spec("relay-exact-head-e2e", canonical_main=main, candidate_head=head)
            spec["candidate_branch"] = CANDIDATE_BRANCH
            store = OrchestratorStore(orch_db)
            try:
                store.create_task(spec)
                worker = RelayRoleWorker(relay_db, poll_seconds=0.01, result_wait_seconds=4.0)
                final = Orchestrator(store, worker, StaticBindingVerifier(main, head)).run_until_terminal(spec["task_id"])
                task = store.get(spec["task_id"])
                self.assertEqual(final, "DONE")
                self.assertEqual(task["result"]["candidate_head"], head)
                self.assertEqual(task["result"]["owner_copy_paste_count"], 0)
                self.assertEqual(task["result"]["owner_continue_prompt_count"], 0)
                self.assertEqual(task["result"]["owner_keep_alive_count"], 0)
                self.assertEqual(task["semantic_retry_count"], 1)
            finally:
                store.close()
            agent.join(10)
            self.assertEqual(agent.exitcode, 0)

if __name__ == "__main__":
    unittest.main()
