#!/usr/bin/env python3
"""Governed R1 entrypoint v2. Runtime activation remains disabled."""
import argparse,copy,hashlib,json,tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock
import multiverse_r1_state_v1 as state_mod
from multiverse_r1_auth_v1 import AuthorizationDenied,AuthorizationRuntime,validate_authorization
from multiverse_r1_engine_v1 import CANONICAL_DESIGN_MERGE,DeadLettered,FencingConflict,R1Engine,ReceiptConflict
from multiverse_r1_state_v1 import PersistentStore,SchemaError,StaleState

def dg(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
def auth(op,target,perm,scope,actor,*,gate=None,decision="ALLOW",grant=None):
    if grant is None and perm!="P0_READ_PUBLIC_OR_CANONICAL":grant="grant-r1-test"
    return {"authorization_decision_id":"auth-"+dg([op,target,perm,scope,actor,gate])[:12],"policy_generation":"g1","policy_digest":"d1","actor_role":"EXECUTION","actor_instance":actor,"operation":op,"target":target,"permission_class_requested":perm,"permission_ceiling":"P5_PROHIBITED" if perm=="P5_PROHIBITED" else "P4_OWNER_GATE_REQUIRED","scope":{"operation":op,"target":target,"data_exposure_scope":scope},"data_exposure_scope":scope,"issued_at":"2026-08-21T03:00:00+00:00","expires_at":"2026-08-21T06:00:00+00:00","grant_ref":grant,"owner_gate_ref":gate,"revocation_generation_seen":3,"safe_mode_generation_seen":5,"decision":decision,"reason_codes":["FAKE_HARNESS"],"evidence_refs":[]}
def runtime(actor,*,gate=None,grants=frozenset({"grant-r1-test"}),safe=False):return AuthorizationRuntime("g1","d1",3,5,datetime.fromisoformat("2026-08-21T04:00:00+00:00"),"EXECUTION",actor,grants,gate,safe)
def expect(exc,fn):
    try:fn()
    except exc:return
    raise AssertionError("expected "+exc.__name__)
def selftest():
    m=CANONICAL_DESIGN_MERGE
    with tempfile.TemporaryDirectory() as td:
        st=PersistentStore(Path(td));e=R1Engine(st,m);r="router"
        a=auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE","source-candidate:s1","P1_REVERSIBLE_INTERNAL_WRITE","PUBLIC_TERMS_METADATA_ONLY",r);t=e.inspect_candidate(current_main=m,candidate_id="s1",docs_hash="h1",authorization=a,auth_runtime=runtime(r));assert t==e.inspect_candidate(current_main=m,candidate_id="s1",docs_hash="h1",authorization=a,auth_runtime=runtime(r))
        la=auth("R1_TASK_ACQUIRE_LEASE",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wa");ea=e.acquire_lease(current_main=m,task_id=t,worker_id="wa",now_tick=1,lease_ticks=5,authorization=la,auth_runtime=runtime("wa"))
        cp_a=auth("R1_TASK_CHECKPOINT",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wa");e.checkpoint(current_main=m,task_id=t,worker_id="wa",lease_epoch=ea,now_tick=2,checkpoint_ref="cp1",authorization=cp_a,auth_runtime=runtime("wa"))
        lb=auth("R1_TASK_ACQUIRE_LEASE",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wb");expect(FencingConflict,lambda:e.acquire_lease(current_main=m,task_id=t,worker_id="wb",now_tick=2,lease_ticks=5,authorization=lb,auth_runtime=runtime("wb")));eb=e.acquire_lease(current_main=m,task_id=t,worker_id="wb",now_tick=7,lease_ticks=10,authorization=lb,auth_runtime=runtime("wb"));assert eb>ea and st.read()["tasks"][t]["checkpoint_ref"]=="cp1"
        before_attempts=st.read()["tasks"][t]["attempt_count"]
        expect(FencingConflict,lambda:e.checkpoint(current_main=m,task_id=t,worker_id="wa",lease_epoch=ea,now_tick=8,checkpoint_ref="stale-cp",authorization=cp_a,auth_runtime=runtime("wa")))
        fail_a=auth("R1_TASK_RECORD_FAILURE",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wa");expect(FencingConflict,lambda:e.record_failure(current_main=m,task_id=t,worker_id="wa",lease_epoch=ea,now_tick=8,reason="stale-failure",authorization=fail_a,auth_runtime=runtime("wa")));assert st.read()["tasks"][t]["attempt_count"]==before_attempts and st.read()["tasks"][t]["checkpoint_ref"]=="cp1"
        cp_b=auth("R1_TASK_CHECKPOINT",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wb");e.checkpoint(current_main=m,task_id=t,worker_id="wb",lease_epoch=eb,now_tick=8,checkpoint_ref="cp2",authorization=cp_b,auth_runtime=runtime("wb"));assert st.read()["tasks"][t]["checkpoint_ref"]=="cp2"
        expect(StaleState,lambda:e.checkpoint(current_main="0"*40,task_id=t,worker_id="wb",lease_epoch=eb,now_tick=8,checkpoint_ref="bad",authorization=cp_b,auth_runtime=runtime("wb")))
        fail_b=auth("R1_TASK_RECORD_FAILURE",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","wb");expect(StaleState,lambda:e.record_failure(current_main="0"*40,task_id=t,worker_id="wb",lease_epoch=eb,now_tick=8,reason="bad",authorization=fail_b,auth_runtime=runtime("wb")));expect(StaleState,lambda:e.acquire_lease(current_main="0"*40,task_id=t,worker_id="wb",now_tick=18,lease_ticks=5,authorization=lb,auth_runtime=runtime("wb")))
        ca=auth("R1_SOURCE_REVIEW_COMMIT",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","PUBLIC_TERMS_METADATA_ONLY","wa");cb=auth("R1_SOURCE_REVIEW_COMMIT",f"task:{t}","P1_REVERSIBLE_INTERNAL_WRITE","PUBLIC_TERMS_METADATA_ONLY","wb");expect(FencingConflict,lambda:e.commit_review(current_main=m,task_id=t,worker_id="wa",lease_epoch=ea,now_tick=9,committed_state="REVIEWED_NO_ADMISSION",verdict_reason="x",evidence_refs=["e"],authorization=ca,auth_runtime=runtime("wa")));rr=e.commit_review(current_main=m,task_id=t,worker_id="wb",lease_epoch=eb,now_tick=9,committed_state="REVIEWED_NO_ADMISSION",verdict_reason="x",evidence_refs=["e"],authorization=cb,auth_runtime=runtime("wb"));assert rr==e.commit_review(current_main=m,task_id=t,worker_id="wb",lease_epoch=eb,now_tick=9,committed_state="REVIEWED_NO_ADMISSION",verdict_reason="x",evidence_refs=["e"],authorization=cb,auth_runtime=runtime("wb"));assert e.inspect_candidate(current_main=m,candidate_id="s1",docs_hash="h1",authorization=a,auth_runtime=runtime(r)) is None
        idem=e.idem("s1","h1");rd=auth("R1_RECEIPT_READ",f"receipt-idempotency:{idem}","P0_READ_PUBLIC_OR_CANONICAL","INTERNAL_R1_RECEIPT_ONLY","reader");assert e.read_receipt(idempotency_key=idem,authorization=rd,auth_runtime=runtime("reader"))==rr
        expect(AuthorizationDenied,lambda:e.inspect_candidate(current_main=m,candidate_id="s2",docs_hash="h2",authorization=a,auth_runtime=runtime("other")));expect(AuthorizationDenied,lambda:e.inspect_candidate(current_main=m,candidate_id="s2",docs_hash="h2",authorization=a,auth_runtime=runtime(r,grants=frozenset())));expect(AuthorizationDenied,lambda:e.inspect_candidate(current_main=m,candidate_id="s2",docs_hash="h2",authorization=a,auth_runtime=runtime(r,safe=True)))
        p5=auth("x","y","P5_PROHIBITED","z","p5",grant="grant-r1-test");expect(AuthorizationDenied,lambda:validate_authorization(p5,runtime("p5"),operation="x",target="y",permission_class="P5_PROHIBITED",data_exposure_scope="z"));p4=auth("x","y","P4_OWNER_GATE_REQUIRED","z","p4",gate="wrong");expect(AuthorizationDenied,lambda:validate_authorization(p4,runtime("p4",gate="right"),operation="x",target="y",permission_class="P4_OWNER_GATE_REQUIRED",data_exposure_scope="z"))
        a3=auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE","source-candidate:s3","P1_REVERSIBLE_INTERNAL_WRITE","PUBLIC_TERMS_METADATA_ONLY","r3");t3=e.inspect_candidate(current_main=m,candidate_id="s3",docs_hash="h3",authorization=a3,auth_runtime=runtime("r3"));l3=auth("R1_TASK_ACQUIRE_LEASE",f"task:{t3}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","fw");e3=e.acquire_lease(current_main=m,task_id=t3,worker_id="fw",now_tick=1,lease_ticks=20,authorization=l3,auth_runtime=runtime("fw"));fa=auth("R1_TASK_RECORD_FAILURE",f"task:{t3}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","fw");[e.record_failure(current_main=m,task_id=t3,worker_id="fw",lease_epoch=e3,now_tick=tick,reason="timeout",authorization=fa,auth_runtime=runtime("fw")) for tick in (2,3,4)];lz=auth("R1_TASK_ACQUIRE_LEASE",f"task:{t3}","P1_REVERSIBLE_INTERNAL_WRITE","INTERNAL_R1_STATE_ONLY","z");expect(DeadLettered,lambda:e.acquire_lease(current_main=m,task_id=t3,worker_id="z",now_tick=30,lease_ticks=2,authorization=lz,auth_runtime=runtime("z")))
        good=st.read();bad=copy.deepcopy(good);bad["tasks"][t].pop("authorization_ref");st.state_path.write_text(json.dumps(bad));expect(SchemaError,st.read);st.state_path.write_text(json.dumps(good));bad=copy.deepcopy(good);bad["receipts_by_idempotency"][idem]["receipt_id"]="forged";st.state_path.write_text(json.dumps(bad));expect(SchemaError,st.read);st.state_path.write_text(json.dumps(good));bad=copy.deepcopy(good);bad["cache"]["s1"]["audit_state"]="FAKE";st.state_path.write_text(json.dumps(bad));expect(SchemaError,st.read);st.state_path.write_text(json.dumps(good))
        for field,bad_value in (("authorization_decision_id",[]),("worker_id",7),("canonical_main",None),("operation_owner_gate_ref",False),("cache_version_after",True),("lease_epoch",False)):
            bad=copy.deepcopy(good);bad["receipts_by_idempotency"][idem][field]=bad_value;st.state_path.write_text(json.dumps(bad));expect(SchemaError,st.read);st.state_path.write_text(json.dumps(good))
        g=st.read()["generation"];st.transact(lambda s:s["cache"]["s1"].update(freshness_state="TOUCHED"),expected_generation=g);expect(StaleState,lambda:st.transact(lambda s:None,expected_generation=g));assert e.owner_exception_view(what_changed="test",what_ran_automatically="fake",blocked_reason="RUNTIME_OFF")["approval_authority"]=="NONE_OBSERVABILITY_ONLY"
    with tempfile.TemporaryDirectory() as td:
        st2=PersistentStore(Path(td));snap=st2.read()
        with mock.patch.object(state_mod,"_fsync_parent_dir",wraps=state_mod._fsync_parent_dir) as parent_sync:
            st2._write(snap);assert parent_sync.call_count==1
    for x in ("AUTH_ACTOR_BINDING_ENFORCED","P5_DENY_PRECEDENCE_ENFORCED","GRANT_VALIDITY_BINDING_ENFORCED","SAFE_MODE_DENY_ENFORCED","TASK_AND_RECEIPT_SCHEMA_STRICT","RECEIPT_IDENTITY_STRICT","RECEIPT_SCALAR_TYPES_STRICT","BOOL_AS_INT_REJECTED","FENCING_BEFORE_COMMIT_SUCCESS","STALE_WORKER_CHECKPOINT_DENIED","STALE_WORKER_FAILURE_ACCOUNTING_DENIED","CANONICAL_FRESHNESS_ALL_TASK_WRITES","PARENT_DIRECTORY_FSYNC_AFTER_REPLACE"):print(x+"=true")
    print("EXACTLY_ONCE_CLAIM=false\nNETWORK_ACCESS_PERFORMED=false\nRUNTIME_ACTIVATION_PERFORMED=false\nMULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SELFTEST_PASS");return 0
def main():
    p=argparse.ArgumentParser();p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:return selftest()
    print("R1_LIBRARY_ONLY_NO_AUTORUN_RUNTIME_ACTIVATION");return 0
if __name__=="__main__":raise SystemExit(main())
