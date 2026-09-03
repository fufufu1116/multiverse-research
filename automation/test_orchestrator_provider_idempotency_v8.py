#!/usr/bin/env python3
import hashlib
import multiprocessing as mp
import pathlib
import tempfile
import unittest

from orchestrator_mvp_v2 import OrchestratorError, canonical_json
from orchestrator_provider_idempotency_v8 import (
    DeterministicRemoteSimulator, LocalIdempotencyJournal,
    SimulatedProviderStore, V8Manifest, execute_idempotent_simulated_remote,
    request_from_job,
)

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = HERE / "MULTIVERSE_AUTOMATION_PROVIDER_IDEMPOTENCY_V8.json"
MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
HEAD = "e803723309a045086287e613f924a90a880b5a3b"
BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"

def make_job(op="op-1", role="IMPLEMENT", gen=0):
    return {
        "operation_key": op, "task_id": "task-v8", "role": role,
        "semantic_generation": gen, "candidate_head": HEAD,
        "candidate_branch": BRANCH, "canonical_main": MAIN,
        "objective": "prove local simulated provider idempotency",
        "authority": {"candidate_only":True,"live_provider":False,"production":False,"runtime":False,"spend":False},
    }

def make_script():
    return {
        "IMPLEMENT":{"1":{"status":"READY","candidate_head":HEAD,"diff_lines":4,"cost_microusd":0,"evidence_ref":"v8-impl"}},
        "LAB":{"1":{"verdict":"PASS","reviewed_head":HEAD,"evidence_ref":"v8-lab"}},
        "AUDIT":{"1":{"verdict":"PASS","reviewed_head":HEAD,"evidence_ref":"v8-audit"}},
    }

def _remote_racer(db, req, script, q):
    store = SimulatedProviderStore(db)
    try:
        out = DeterministicRemoteSimulator(store, script).execute(req)
        q.put((out["provider_receipt_id"], out["effect_count"], None))
    except Exception as exc:
        q.put((None, None, f"{type(exc).__name__}:{exc}"))
    finally:
        store.close()

class ProviderIdempotencyV8Tests(unittest.TestCase):
    def test_idempotency_key_is_derived_not_injected(self):
        req = request_from_job(make_job()); bad = dict(req); bad["idempotency_key"] = "0"*64
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                with self.assertRaisesRegex(OrchestratorError,"V8_IDEMPOTENCY_KEY_DERIVATION"):
                    execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,make_script()),bad)
            finally: s.close(); j.close()

    def test_response_lost_after_provider_commit_recovers_same_receipt_effect_one(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                sim=DeterministicRemoteSimulator(s,make_script())
                out=execute_idempotent_simulated_remote(j,sim,req,lose_response_after_commit=True)
                self.assertEqual(out["status"],"READY"); self.assertEqual(s.effect_count(req["idempotency_key"]),1)
                self.assertEqual(execute_idempotent_simulated_remote(j,sim,req),out)
                self.assertEqual(s.effect_count(req["idempotency_key"]),1)
            finally: s.close(); j.close()

    def test_crash_before_remote_leaves_prepared_and_zero_effect(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                with self.assertRaisesRegex(RuntimeError,"V8_CRASH_BEFORE_REMOTE_EFFECT"):
                    execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,make_script()),req,crash_before_remote=True)
                self.assertEqual(j.state(req["operation_key"]),"PREPARED"); self.assertEqual(s.effect_count(req["idempotency_key"]),0)
            finally: s.close(); j.close()

    def test_crash_after_local_receipt_replays_without_second_effect(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            local=str(pathlib.Path(td)/"l.db"); remote=str(pathlib.Path(td)/"r.db"); m=V8Manifest(MANIFEST)
            j=LocalIdempotencyJournal(local,m); s=SimulatedProviderStore(remote)
            try:
                with self.assertRaisesRegex(RuntimeError,"V8_CRASH_AFTER_LOCAL_RECEIPT"):
                    execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,make_script()),req,crash_after_local_receipt=True)
                self.assertEqual(j.state(req["operation_key"]),"OBSERVED"); self.assertEqual(s.effect_count(req["idempotency_key"]),1)
            finally: s.close(); j.close()
            j=LocalIdempotencyJournal(local,m); s=SimulatedProviderStore(remote)
            try:
                self.assertEqual(execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,make_script()),req)["status"],"READY")
                self.assertEqual(s.effect_count(req["idempotency_key"]),1)
            finally: s.close(); j.close()

    def test_ambiguous_without_receipt_fails_closed(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                with self.assertRaisesRegex(OrchestratorError,"V8_REMOTE_STATUS_REQUIRED"):
                    execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,make_script()),req,ambiguous_without_receipt=True)
                self.assertEqual(s.effect_count(req["idempotency_key"]),0)
            finally: s.close(); j.close()

    def test_provider_receipt_tampering_rejected_before_observed(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                j.prepare(req); receipt=DeterministicRemoteSimulator(s,make_script()).execute(req); bad=dict(receipt); bad["result_hash"]="0"*64
                with self.assertRaisesRegex(OrchestratorError,"V8_PROVIDER_RECEIPT_RESULT_HASH"): j.record_observed(req,bad)
                self.assertEqual(j.state(req["operation_key"]),"PREPARED")
            finally: s.close(); j.close()

    def test_malformed_v7_role_result_never_becomes_observed(self):
        req=request_from_job(make_job()); bad={"IMPLEMENT":{"1":{"status":"READY","candidate_head":HEAD,"diff_lines":True,"cost_microusd":0,"evidence_ref":"bad"}}}
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                with self.assertRaisesRegex(OrchestratorError,"PROVIDER_ADAPTER_IMPLEMENT_DIFF_LINES"):
                    execute_idempotent_simulated_remote(j,DeterministicRemoteSimulator(s,bad),req)
                self.assertEqual(j.state(req["operation_key"]),"PREPARED"); self.assertEqual(s.effect_count(req["idempotency_key"]),1)
            finally: s.close(); j.close()

    def test_conflicting_request_cannot_reuse_key(self):
        req=request_from_job(make_job()); other=dict(req); other["objective"]="different"
        bare=dict(other); bare.pop("request_fingerprint"); bare.pop("idempotency_key")
        other["request_fingerprint"]=hashlib.sha256(canonical_json(bare).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                sim=DeterministicRemoteSimulator(s,make_script()); sim.execute(req)
                with self.assertRaisesRegex(OrchestratorError,"V8_IDEMPOTENCY_KEY_DERIVATION"): sim.execute(other)
            finally: s.close()

    def test_remote_concurrent_same_key_converges_one_effect(self):
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            db=str(pathlib.Path(td)/"r.db"); SimulatedProviderStore(db).close(); ctx=mp.get_context("fork"); q=ctx.Queue()
            ps=[ctx.Process(target=_remote_racer,args=(db,req,make_script(),q)) for _ in range(12)]
            for p in ps: p.start()
            for p in ps: p.join(10)
            rows=[q.get(timeout=2) for _ in ps]; self.assertTrue(all(x[2] is None for x in rows),rows); self.assertEqual(len({x[0] for x in rows}),1)
            s=SimulatedProviderStore(db)
            try: self.assertEqual(s.effect_count(req["idempotency_key"]),1)
            finally: s.close()

    def test_exact_class_injection_denied(self):
        class Evil(DeterministicRemoteSimulator): pass
        req=request_from_job(make_job())
        with tempfile.TemporaryDirectory() as td:
            j=LocalIdempotencyJournal(str(pathlib.Path(td)/"l.db"),V8Manifest(MANIFEST)); s=SimulatedProviderStore(str(pathlib.Path(td)/"r.db"))
            try:
                with self.assertRaisesRegex(OrchestratorError,"V8_REMOTE_SIMULATOR_INJECTION_DENIED"):
                    execute_idempotent_simulated_remote(j,Evil(s,make_script()),req)
            finally: s.close(); j.close()

if __name__ == "__main__": unittest.main()
