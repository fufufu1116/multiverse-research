#!/usr/bin/env python3
import multiprocessing as mp
import os
import pathlib
import tempfile
import time
import unittest

from orchestrator_mvp_v2 import Orchestrator, OrchestratorStore, StaticBindingVerifier, demo_spec
from orchestrator_provider_idempotency_v8 import process_one
from orchestrator_role_relay_policy_source_v5 import SourceBoundPolicyRelayRoleWorker

HERE = pathlib.Path(__file__).resolve().parent
POLICY_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
V8_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_PROVIDER_IDEMPOTENCY_V8.json"
MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
TASK_HEAD = "e803723309a045086287e613f924a90a880b5a3b"
TASK_BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"

def _loop(relay_db, local_db, remote_db, script, expected_jobs):
    completed=0; deadline=time.time()+25; first=True
    while completed < expected_jobs and time.time() < deadline:
        out=process_one(relay_db,local_db,remote_db,str(POLICY_MANIFEST),str(V8_MANIFEST),"provider-idempotency-v8",script,lease_seconds=2,lose_response_after_commit=first)
        first=False
        if out=="COMPLETE": completed+=1
        else: time.sleep(0.01)
    if completed != expected_jobs: raise SystemExit(93)

class ProviderIdempotencyV8IntegrationTests(unittest.TestCase):
    def test_v2_v5_relay_v8_remote_simulator_reaches_done_with_response_loss(self):
        code_head=os.environ.get("MULTIVERSE_V8_CODE_HEAD"); main=os.environ.get("MULTIVERSE_CANONICAL_MAIN")
        if not code_head or not main: self.skipTest("exact v8 code-head/main supplied by mechanical gate")
        self.assertEqual(len(code_head),40); self.assertEqual(main,MAIN)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); relay=root/"relay.db"; local=root/"local.db"; remote=root/"remote.db"; orch=root/"orch.db"
            script={
                "IMPLEMENT":{
                    "1":{"status":"READY","candidate_head":TASK_HEAD,"diff_lines":10,"cost_microusd":0,"evidence_ref":"v8-i1"},
                    "2":{"status":"READY","candidate_head":TASK_HEAD,"diff_lines":11,"cost_microusd":0,"evidence_ref":"v8-i2"}},
                "LAB":{
                    "1":{"verdict":"FIX_REQUIRED","reviewed_head":TASK_HEAD,"code":"V8_DEMO_FIX","detail":"simulated","evidence_ref":"v8-l1"},
                    "2":{"verdict":"PASS","reviewed_head":TASK_HEAD,"evidence_ref":"v8-l2"}},
                "AUDIT":{"2":{"verdict":"PASS","reviewed_head":TASK_HEAD,"evidence_ref":"v8-a2"}},
            }
            ctx=mp.get_context("fork"); agent=ctx.Process(target=_loop,args=(str(relay),str(local),str(remote),script,5)); agent.start()
            spec=demo_spec("provider-idempotency-v8-e2e",canonical_main=main,candidate_head=TASK_HEAD); spec["domain"]="automation-v5"; spec["candidate_branch"]=TASK_BRANCH
            store=OrchestratorStore(orch)
            try:
                store.create_task(spec)
                worker=SourceBoundPolicyRelayRoleWorker(relay,POLICY_MANIFEST,poll_seconds=0.01,result_wait_seconds=5.0)
                final=Orchestrator(store,worker,StaticBindingVerifier(main,TASK_HEAD)).run_until_terminal(spec["task_id"]); task=store.get(spec["task_id"])
                self.assertEqual(final,"DONE"); self.assertEqual(task["result"]["owner_copy_paste_count"],0); self.assertEqual(task["result"]["owner_continue_prompt_count"],0); self.assertEqual(task["result"]["owner_keep_alive_count"],0)
            finally: store.close()
            agent.join(12); self.assertEqual(agent.exitcode,0)

if __name__=="__main__": unittest.main()
