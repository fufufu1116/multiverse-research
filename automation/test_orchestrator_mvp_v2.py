import pathlib, tempfile, unittest
from orchestrator_mvp_v2 import (
    InjectedCrash, Orchestrator, OrchestratorError, OrchestratorStore,
    DurableScriptedRoleWorker, StaticBindingVerifier, demo_script, demo_spec,
    operation_key, run_demo
)

class T(unittest.TestCase):
    def p(self,name):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); return pathlib.Path(td.name)/name
    def make(self, task_id="t", script=None):
        db=self.p("state.sqlite"); wdb=self.p("worker.sqlite"); spec=demo_spec(task_id)
        worker=DurableScriptedRoleWorker(wdb, script or demo_script(spec["candidate_head"]))
        store=OrchestratorStore(db); store.create_task(spec)
        orch=Orchestrator(store,worker,StaticBindingVerifier(spec["canonical_main"],spec["candidate_head"]))
        self.addCleanup(store.close); return spec,worker,store,orch

    def test_e2e(self):
        out=run_demo(self.p("s.sqlite"),self.p("w.sqlite"))
        self.assertEqual(out["final_state"],"DONE")
        r=out["task"]["result"]
        self.assertEqual((r["owner_copy_paste_count"],r["owner_continue_prompt_count"],r["owner_keep_alive_count"]),(0,0,0))
        self.assertEqual(r["semantic_retries"],1)

    def test_crash_after_worker_return_replays_same_operation_once(self):
        head="a"*40
        script={
            "IMPLEMENT":{"1:*":{"status":"READY","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"i"}},
            "LAB":{"1:*":{"verdict":"PASS","reviewed_head":head,"evidence_ref":"l"}},
            "AUDIT":{"1:*":{"verdict":"PASS","reviewed_head":head,"evidence_ref":"a"}},
        }
        spec,worker,store,orch=self.make("crash",script)
        op=operation_key(spec["task_id"],"IMPLEMENT",0)
        with self.assertRaises(InjectedCrash): orch.step(spec["task_id"],crash_after_worker_return="IMPLEMENT")
        self.assertEqual(worker.execution_count(op),1)
        task=store.get(spec["task_id"])
        store.recover_stale(at=task["heartbeat_at"]+spec["budgets"]["heartbeat_timeout_seconds"]+1)
        self.assertEqual(orch.run_until_terminal(spec["task_id"]),"DONE")
        self.assertEqual(worker.execution_count(op),1)
        self.assertEqual(store.get(spec["task_id"])["semantic_retry_count"],0)

    def test_transient_no_semantic_retry(self):
        head="a"*40
        script={
            "IMPLEMENT":{
                "1:1":{"raise":"TRANSIENT","detail":"network"},
                "1:2":{"status":"READY","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"i"},
            },
            "LAB":{"1:*":{"verdict":"PASS","reviewed_head":head,"evidence_ref":"l"}},
            "AUDIT":{"1:*":{"verdict":"PASS","reviewed_head":head,"evidence_ref":"a"}},
        }
        spec,worker,store,orch=self.make("trans",script)
        self.assertEqual(orch.step(spec["task_id"]),"IN_IMPLEMENT")
        t=store.get(spec["task_id"]); self.assertEqual(t["semantic_retry_count"],0); self.assertEqual(t["transient_retry_count"],1)
        self.assertEqual(orch.run_until_terminal(spec["task_id"]),"DONE")

    def test_repeated_failure_owner_gate(self):
        head="a"*40
        script={"IMPLEMENT":{
            "1:*":{"status":"BAD","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"x"},
            "2:*":{"status":"BAD","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"x"},
        }}
        spec,worker,store,orch=self.make("loop",script)
        self.assertEqual(orch.step(spec["task_id"]),"MECH_GATE_FAIL")
        self.assertEqual(orch.step(spec["task_id"]),"OWNER_GATE")
        self.assertEqual(store.get(spec["task_id"])["owner_gate_reason"],"REPEATED_FAILURE_FINGERPRINT")

    def test_budget_widening_denied(self):
        for key,val in [("transient_retry_budget",4),("diff_budget_lines",501),("execution_budget_seconds",301),("heartbeat_timeout_seconds",301),("semantic_retry_budget",3)]:
            spec=demo_spec("b"+key); spec["budgets"][key]=val
            with self.assertRaises(OrchestratorError):
                s=OrchestratorStore(self.p(key+".sqlite")); self.addCleanup(s.close); s.create_task(spec)

    def test_review_head_mismatch_owner_gate(self):
        head="a"*40
        script={
            "IMPLEMENT":{"1:*":{"status":"READY","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"i"}},
            "LAB":{"1:*":{"verdict":"PASS","reviewed_head":"c"*40,"evidence_ref":"l"}},
        }
        spec,worker,store,orch=self.make("mismatch",script)
        self.assertEqual(orch.step(spec["task_id"]),"IN_LAB")
        self.assertEqual(orch.step(spec["task_id"]),"OWNER_GATE")
        self.assertEqual(store.get(spec["task_id"])["owner_gate_reason"],"LAB_REVIEW_HEAD_MISMATCH")

    def test_binding_mismatch_owner_gate(self):
        spec=demo_spec("bind"); db=self.p("x.sqlite"); wdb=self.p("y.sqlite")
        worker=DurableScriptedRoleWorker(wdb,{})
        store=OrchestratorStore(db); self.addCleanup(store.close); store.create_task(spec)
        orch=Orchestrator(store,worker,StaticBindingVerifier(spec["canonical_main"],"c"*40))
        self.assertEqual(orch.step(spec["task_id"]),"OWNER_GATE")

    def test_unknown_safety_owner_gate(self):
        spec=demo_spec("unsafe"); spec["safety"]["unknown_risk"]=True
        db=self.p("u.sqlite"); wdb=self.p("uw.sqlite"); worker=DurableScriptedRoleWorker(wdb,{})
        store=OrchestratorStore(db); self.addCleanup(store.close); store.create_task(spec)
        orch=Orchestrator(store,worker,StaticBindingVerifier(spec["canonical_main"],spec["candidate_head"]))
        self.assertEqual(orch.step(spec["task_id"]),"OWNER_GATE")

    def test_hard_timeout_is_machine_enforced(self):
        spec=demo_spec("timeout"); spec["budgets"]["execution_budget_seconds"]=0
        head=spec["candidate_head"]
        script={"IMPLEMENT":{"1:*":{"sleep_seconds":0.2,"status":"READY","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":"i"}}}
        db=self.p("to.sqlite"); wdb=self.p("tow.sqlite"); worker=DurableScriptedRoleWorker(wdb,script)
        store=OrchestratorStore(db); self.addCleanup(store.close); store.create_task(spec)
        orch=Orchestrator(store,worker,StaticBindingVerifier(spec["canonical_main"],head))
        self.assertEqual(orch.step(spec["task_id"]),"MECH_GATE_FAIL")
        self.assertIn("EXECUTION_TIME",store.get(spec["task_id"])["last_checkpoint"])

    def test_rollback(self):
        spec,worker,store,orch=self.make("rb",{})
        self.assertEqual(orch.rollback(spec["task_id"],"test"),"ROLLED_BACK")
        self.assertFalse(store.get(spec["task_id"])["result"]["production_or_stable_mutation"])

if __name__=="__main__": unittest.main()
