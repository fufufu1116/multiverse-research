#!/usr/bin/env python3
import multiprocessing as mp
import os
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import Orchestrator, OrchestratorStore, StaticBindingVerifier, demo_spec
from orchestrator_role_relay_policy_v4 import (
    CandidateBindingPolicy,
    PolicyRelayRoleWorker,
    policy_fixture_process_one,
)

REPO = "fufufu1116/multiverse-research"


def _agent_loop(relay_db, receipt_db, policy, script, expected_jobs):
    completed = 0
    deadline = time.time() + 20
    while completed < expected_jobs and time.time() < deadline:
        out = policy_fixture_process_one(relay_db, receipt_db, policy, "fixture-agent", script,
                                         lease_seconds=2)
        if out == "COMPLETE":
            completed += 1
        else:
            time.sleep(0.01)
    if completed != expected_jobs:
        raise SystemExit(91)


class PolicyRelayV4IntegrationTests(unittest.TestCase):
    def test_exact_head_full_orchestrator_e2e_with_runtime_selected_candidate_branch(self):
        head = os.environ.get("MULTIVERSE_EXPECTED_HEAD")
        main = os.environ.get("MULTIVERSE_CANONICAL_MAIN")
        branch = os.environ.get("MULTIVERSE_V4_CANDIDATE_BRANCH")
        if not head or not main or not branch:
            self.skipTest("exact-head/main/branch environment supplied by mechanical gate")
        self.assertEqual(len(head), 40)
        self.assertEqual(len(main), 40)
        self.assertTrue(branch.startswith("agent/"))
        policy = CandidateBindingPolicy.exact(REPO, ("automation", branch))

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay-v4.sqlite"
            receipt_db = root / "receipt.sqlite"
            orch_db = root / "orch.sqlite"
            script = {
                "IMPLEMENT": {
                    "1": {"status": "READY", "candidate_head": head, "diff_lines": 10,
                          "cost_microusd": 0, "evidence_ref": "policy-relay-impl-1"},
                    "2": {"status": "READY", "candidate_head": head, "diff_lines": 11,
                          "cost_microusd": 0, "evidence_ref": "policy-relay-impl-2"},
                },
                "LAB": {
                    "1": {"verdict": "FIX_REQUIRED", "reviewed_head": head,
                          "code": "POLICY_RELAY_DEMO_FIX", "detail": "deterministic policy relay remediation",
                          "evidence_ref": "policy-relay-lab-fix"},
                    "2": {"verdict": "PASS", "reviewed_head": head,
                          "evidence_ref": "policy-relay-lab-pass"},
                },
                "AUDIT": {
                    "2": {"verdict": "PASS", "reviewed_head": head,
                          "evidence_ref": "policy-relay-audit-pass"},
                },
            }
            ctx = mp.get_context("fork")
            agent = ctx.Process(target=_agent_loop,
                                args=(str(relay_db), str(receipt_db), policy, script, 5))
            agent.start()
            spec = demo_spec("policy-relay-exact-head-e2e", canonical_main=main, candidate_head=head)
            spec["domain"] = "automation"
            spec["candidate_branch"] = branch
            store = OrchestratorStore(orch_db)
            try:
                store.create_task(spec)
                worker = PolicyRelayRoleWorker(relay_db, policy, poll_seconds=0.01, result_wait_seconds=4.0)
                final = Orchestrator(store, worker, StaticBindingVerifier(main, head)).run_until_terminal(spec["task_id"])
                task = store.get(spec["task_id"])
                self.assertEqual(final, "DONE")
                self.assertEqual(task["result"]["candidate_head"], head)
                self.assertEqual(task["result"]["owner_copy_paste_count"], 0)
                self.assertEqual(task["result"]["owner_continue_prompt_count"], 0)
                self.assertEqual(task["result"]["owner_keep_alive_count"], 0)
                self.assertEqual(task["semantic_retry_count"], 1)
                relay_check = PolicyRelayRoleWorker(relay_db, policy)
                self.assertEqual(relay_check.policy.fingerprint, policy.fingerprint)
            finally:
                store.close()
            agent.join(10)
            self.assertEqual(agent.exitcode, 0)


if __name__ == "__main__":
    unittest.main()
