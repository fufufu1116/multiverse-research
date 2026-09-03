#!/usr/bin/env python3
import multiprocessing as mp
import os
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import Orchestrator, OrchestratorStore, StaticBindingVerifier, demo_spec
from orchestrator_provider_adapter_v7 import provider_adapter_process_one
from orchestrator_role_relay_policy_source_v5 import SourceBoundPolicyRelayRoleWorker

HERE = pathlib.Path(__file__).resolve().parent
POLICY_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
ADAPTER_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_V7.json"
MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
TASK_HEAD = "e803723309a045086287e613f924a90a880b5a3b"
TASK_BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"


def _adapter_loop(relay_db, receipt_db, script, expected_jobs):
    completed = 0
    deadline = time.time() + 20
    while completed < expected_jobs and time.time() < deadline:
        out = provider_adapter_process_one(
            relay_db, receipt_db, str(POLICY_MANIFEST), str(ADAPTER_MANIFEST),
            "provider-adapter-v7", script, lease_seconds=2,
        )
        if out == "COMPLETE":
            completed += 1
        else:
            time.sleep(0.01)
    if completed != expected_jobs:
        raise SystemExit(92)


class ProviderAdapterV7IntegrationTests(unittest.TestCase):
    def test_v2_orchestrator_to_v5_relay_to_v7_sealed_adapter_reaches_done(self):
        code_head = os.environ.get("MULTIVERSE_V7_CODE_HEAD")
        main = os.environ.get("MULTIVERSE_CANONICAL_MAIN")
        if not code_head or not main:
            self.skipTest("exact v7 code-head/main environment supplied by mechanical gate")
        self.assertEqual(len(code_head), 40)
        self.assertEqual(main, MAIN)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            relay_db = root / "relay.sqlite"
            receipt_db = root / "adapter-receipt.sqlite"
            orch_db = root / "orch.sqlite"
            script = {
                "IMPLEMENT": {
                    "1": {"status": "READY", "candidate_head": TASK_HEAD, "diff_lines": 10,
                          "cost_microusd": 0, "evidence_ref": "provider-v7-impl-1"},
                    "2": {"status": "READY", "candidate_head": TASK_HEAD, "diff_lines": 11,
                          "cost_microusd": 0, "evidence_ref": "provider-v7-impl-2"},
                },
                "LAB": {
                    "1": {"verdict": "FIX_REQUIRED", "reviewed_head": TASK_HEAD,
                          "code": "PROVIDER_ADAPTER_DEMO_FIX", "detail": "deterministic adapter remediation",
                          "evidence_ref": "provider-v7-lab-fix"},
                    "2": {"verdict": "PASS", "reviewed_head": TASK_HEAD,
                          "evidence_ref": "provider-v7-lab-pass"},
                },
                "AUDIT": {
                    "2": {"verdict": "PASS", "reviewed_head": TASK_HEAD,
                          "evidence_ref": "provider-v7-audit-pass"},
                },
            }
            ctx = mp.get_context("fork")
            agent = ctx.Process(target=_adapter_loop,
                                args=(str(relay_db), str(receipt_db), script, 5))
            agent.start()
            spec = demo_spec("provider-adapter-v7-e2e", canonical_main=main, candidate_head=TASK_HEAD)
            spec["domain"] = "automation-v5"
            spec["candidate_branch"] = TASK_BRANCH
            store = OrchestratorStore(orch_db)
            try:
                store.create_task(spec)
                worker = SourceBoundPolicyRelayRoleWorker(
                    relay_db, POLICY_MANIFEST, poll_seconds=0.01, result_wait_seconds=4.0
                )
                final = Orchestrator(store, worker, StaticBindingVerifier(main, TASK_HEAD)).run_until_terminal(spec["task_id"])
                task = store.get(spec["task_id"])
                self.assertEqual(final, "DONE")
                self.assertEqual(task["result"]["candidate_head"], TASK_HEAD)
                self.assertEqual(task["result"]["owner_copy_paste_count"], 0)
                self.assertEqual(task["result"]["owner_continue_prompt_count"], 0)
                self.assertEqual(task["result"]["owner_keep_alive_count"], 0)
            finally:
                store.close()
            agent.join(10)
            self.assertEqual(agent.exitcode, 0)


if __name__ == "__main__":
    unittest.main()
