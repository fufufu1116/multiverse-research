#!/usr/bin/env python3
import multiprocessing as mp
import os
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import Orchestrator, OrchestratorStore, StaticBindingVerifier, demo_spec
from orchestrator_role_relay_policy_source_v5 import SourceBoundPolicyRelayRoleWorker, source_fixture_process_one

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"


def _agent_loop(relay_db, receipt_db, script, expected_jobs):
    completed = 0
    deadline = time.time() + 20
    while completed < expected_jobs and time.time() < deadline:
        out = source_fixture_process_one(relay_db, receipt_db, str(MANIFEST), "fixture-agent", script,
                                         lease_seconds=2)
        if out == "COMPLETE":
            completed += 1
        else:
            time.sleep(0.01)
    if completed != expected_jobs:
        raise SystemExit(91)


class PolicySourceV5IntegrationTests(unittest.TestCase):
    def test_exact_head_full_orchestrator_e2e_uses_compiled_reviewed_source(self):
        head = os.environ.get("MULTIVERSE_EXPECTED_HEAD")
        main = os.environ.get("MULTIVERSE_CANONICAL_MAIN")
        branch = os.environ.get("MULTIVERSE_V5_CANDIDATE_BRANCH")
        if not head or not main or not branch:
            self.skipTest("exact-head/main/branch environment supplied by mechanical gate")
        self.assertEqual(main, "040d37f0a4e426cf2e119706484c90cbb48f0e56")
        self.assertEqual(branch, BRANCH)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay-v5.sqlite"
            receipt_db = root / "receipt.sqlite"
            orch_db = root / "orch.sqlite"
            script = {
                "IMPLEMENT": {
                    "1": {"status": "READY", "candidate_head": head, "diff_lines": 10,
                          "cost_microusd": 0, "evidence_ref": "source-v5-impl-1"},
                    "2": {"status": "READY", "candidate_head": head, "diff_lines": 11,
                          "cost_microusd": 0, "evidence_ref": "source-v5-impl-2"},
                },
                "LAB": {
                    "1": {"verdict": "FIX_REQUIRED", "reviewed_head": head,
                          "code": "POLICY_SOURCE_DEMO_FIX", "detail": "deterministic source remediation",
                          "evidence_ref": "source-v5-lab-fix"},
                    "2": {"verdict": "PASS", "reviewed_head": head,
                          "evidence_ref": "source-v5-lab-pass"},
                },
                "AUDIT": {
                    "2": {"verdict": "PASS", "reviewed_head": head,
                          "evidence_ref": "source-v5-audit-pass"},
                },
            }
            ctx = mp.get_context("fork")
            agent = ctx.Process(target=_agent_loop,
                                args=(str(relay_db), str(receipt_db), script, 5))
            agent.start()
            spec = demo_spec("policy-source-v5-e2e", canonical_main=main, candidate_head=head)
            spec["domain"] = "automation-v5"
            spec["candidate_branch"] = branch
            store = OrchestratorStore(orch_db)
            try:
                store.create_task(spec)
                worker = SourceBoundPolicyRelayRoleWorker(
                    relay_db, MANIFEST, poll_seconds=0.01, result_wait_seconds=4.0
                )
                final = Orchestrator(store, worker, StaticBindingVerifier(main, head)).run_until_terminal(spec["task_id"])
                task = store.get(spec["task_id"])
                self.assertEqual(final, "DONE")
                self.assertEqual(task["result"]["candidate_head"], head)
                self.assertEqual(task["result"]["owner_copy_paste_count"], 0)
                self.assertEqual(task["result"]["owner_continue_prompt_count"], 0)
                self.assertEqual(task["result"]["owner_keep_alive_count"], 0)
            finally:
                store.close()
            agent.join(10)
            self.assertEqual(agent.exitcode, 0)


if __name__ == "__main__":
    unittest.main()
