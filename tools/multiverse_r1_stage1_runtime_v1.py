#!/usr/bin/env python3
"""R1 Limited Internal Runtime Stage 1 dormant orchestration candidate."""
from __future__ import annotations
import argparse,copy,hashlib,json,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any,Mapping,Optional
from multiverse_r1_auth_v1 import AuthorizationDenied,validate_authorization
from multiverse_r1_engine_v1 import R1Engine
from multiverse_r1_state_v1 import AuditState,PersistentStore,empty_state,validate_state
from multiverse_r1_stage1_authority_v1 import AUTH_CONTRACT_PATH,ENQUEUE_OPERATION,ENQUEUE_SCOPE,ENQUEUE_TARGET,GRANT_PATH,OWNER_GATE_PATH,GitCanonicalAuthorityAdapter,_git
from multiverse_r1_stage1_git_runtime_v1 import CONTROL_PATH,HIGH_WATER_REF,R1_STATE_PATH,RUNTIME_REF,RUNTIME_BRANCH,GitRuntimeStateAdapter,RemoteCasConflict,Stage1Denied,Stage1Paused,Stage1Tamper,empty_control,reject_runtime_artifact_as_authority,validate_control,validate_write_path

ENQUEUE_SCHEMA="MULTIVERSE_R1_STAGE1_ENQUEUE_ENVELOPE_v2";STAGE_ID="R1_LIMITED_INTERNAL_RUNTIME_STAGE1";WINDOW_DAYS=7
ENQUEUE_FIELDS={"schema_version","stage_id","candidate_id","docs_hash","requested_final_state","verdict_reason","evidence_refs"}

def _nonempty(v:Any)->bool:return isinstance(v,str) and bool(v)
def _validate_envelope(e:Mapping[str,Any])->None:
    if not isinstance(e,dict) or set(e)!=ENQUEUE_FIELDS:raise Stage1Denied("ENQUEUE_SCHEMA")
    if e["schema_version"]!=ENQUEUE_SCHEMA or e["stage_id"]!=STAGE_ID:raise Stage1Denied("ENQUEUE_IDENTITY")
    if not all(_nonempty(e[x]) for x in ("candidate_id","docs_hash","verdict_reason")):raise Stage1Denied("ENQUEUE_STRING")
    if not isinstance(e["evidence_refs"],list) or not all(_nonempty(x) for x in e["evidence_refs"]):raise Stage1Denied("ENQUEUE_EVIDENCE")
    if e["requested_final_state"] not in {AuditState.REVIEWED_NO_ADMISSION.value,AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT.value}:raise Stage1Denied("ENQUEUE_FINAL_STATE")
    if e["requested_final_state"]==AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT.value and not e["evidence_refs"]:raise Stage1Denied("ENQUEUE_INELIGIBLE_EVIDENCE_REQUIRED")
def _deadline(c:Mapping[str,Any])->datetime:
    validate_control(c);return datetime.fromisoformat(c["activated_at"].replace("Z","+00:00")).astimezone(timezone.utc)+timedelta(days=WINDOW_DAYS)
def _load_store(root:Path,state:Mapping[str,Any])->PersistentStore:
    validate_state(dict(state));s=PersistentStore(root);s.state_path.write_text(json.dumps(dict(state),sort_keys=True,indent=2)+"\n");s.read();return s

def _process_claimed_one(*,store:PersistentStore,envelope:Mapping[str,Any],control:Mapping[str,Any],authority:GitCanonicalAuthorityAdapter,now:datetime)->Optional[dict]:
    _validate_envelope(envelope);validate_control(control);main=control["canonical_main"]
    if main!=authority.expected_main:raise Stage1Denied("STALE_CANONICAL_MAIN")
    deadline=_deadline(control);enq=authority.authorize(operation=ENQUEUE_OPERATION,target=ENQUEUE_TARGET,scope=ENQUEUE_SCOPE,actor_kind="router",now=now,activation_deadline=deadline)
    validate_authorization(enq.decision,enq.runtime,operation=ENQUEUE_OPERATION,target=ENQUEUE_TARGET,permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope=ENQUEUE_SCOPE)
    engine=R1Engine(store,main);cid=envelope["candidate_id"];worker=authority.worker_actor;tick=int(now.astimezone(timezone.utc).timestamp())
    a=authority.authorize(operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE",target=f"source-candidate:{cid}",scope="PUBLIC_TERMS_METADATA_ONLY",actor_kind="worker",now=now,activation_deadline=deadline)
    tid=engine.inspect_candidate(current_main=main,candidate_id=cid,docs_hash=envelope["docs_hash"],authorization=a.decision,auth_runtime=a.runtime)
    if tid is None:return None
    a=authority.authorize(operation="R1_TASK_ACQUIRE_LEASE",target=f"task:{tid}",scope="INTERNAL_R1_STATE_ONLY",actor_kind="worker",now=now,activation_deadline=deadline);epoch=engine.acquire_lease(current_main=main,task_id=tid,worker_id=worker,now_tick=tick,lease_ticks=10,authorization=a.decision,auth_runtime=a.runtime)
    a=authority.authorize(operation="R1_TASK_CHECKPOINT",target=f"task:{tid}",scope="INTERNAL_R1_STATE_ONLY",actor_kind="worker",now=now,activation_deadline=deadline);engine.checkpoint(current_main=main,task_id=tid,worker_id=worker,lease_epoch=epoch,now_tick=tick+1,checkpoint_ref="stage1:supplied-evidence-validated",authorization=a.decision,auth_runtime=a.runtime)
    a=authority.authorize(operation="R1_SOURCE_REVIEW_COMMIT",target=f"task:{tid}",scope="PUBLIC_TERMS_METADATA_ONLY",actor_kind="worker",now=now,activation_deadline=deadline);return engine.commit_review(current_main=main,task_id=tid,worker_id=worker,lease_epoch=epoch,now_tick=tick+2,committed_state=envelope["requested_final_state"],verdict_reason=envelope["verdict_reason"],evidence_refs=envelope["evidence_refs"],authorization=a.decision,auth_runtime=a.runtime)
def run_one(*,runtime:GitRuntimeStateAdapter,authority:GitCanonicalAuthorityAdapter,envelope:Mapping[str,Any],claim_id:str,now:datetime)->tuple[Optional[dict],str,dict]:
    claim=runtime.claim(expected_main=authority.expected_main,worker_id=authority.worker_actor,claim_id=claim_id,now=now)
    with tempfile.TemporaryDirectory() as td:
        store=_load_store(Path(td),claim.r1_state);receipt=_process_claimed_one(store=store,envelope=envelope,control=claim.control,authority=authority,now=now);persisted=runtime.persist_r1_state(claim,store.read())
    head,control=runtime.finish(persisted);return receipt,head,control
def owner_exception(reason:str,next_safe_action:str="PAUSE_AND_REVIEW")->dict:return R1Engine.owner_exception_view(what_changed="R1_STAGE1_RUNTIME",what_ran_automatically="BOUNDED_INTERNAL_ADMIN_ONLY",blocked_reason=reason,next_safe_action=next_safe_action)

def _blob(content:bytes)->str:return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()
def _write(p:Path,s:str)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def _grant(policy_blob:str)->dict:
    return {"record":"MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_OPERATION_GRANT_20260821_v1","status":"ACTIVE_ONLY_WHEN_READ_FROM_CANONICAL_MAIN_AFTER_AUDIT","canonical_repo":"fufufu1116/multiverse-research","owner_gate_approval_comment":5367308652,"authorization_contract":{"path":AUTH_CONTRACT_PATH,"blob_sha":policy_blob,"policy_generation":"VNEXT_AUTHORIZATION_CONTRACT_v0"},"grant":{"grant_ref":"grant-multiverse-r1-stage1-internal-admin-v1","permission_class":"P1_REVERSIBLE_INTERNAL_WRITE","permission_ceiling":"P1_REVERSIBLE_INTERNAL_WRITE","router_actor_instance":"r1-stage1-router-v1","worker_actor_instance":"r1-stage1-worker-v1","revocation_generation":1,"safe_mode_generation":1,"safe_mode_active":False,"decision_ttl_seconds":300,"operations":[{"operation":ENQUEUE_OPERATION,"target_exact":ENQUEUE_TARGET,"scope":ENQUEUE_SCOPE,"actor_instance":"r1-stage1-router-v1"},{"operation":"R1_SOURCE_CACHE_INSPECT_OR_STAGE","target_prefix":"source-candidate:","scope":"PUBLIC_TERMS_METADATA_ONLY","actor_instance":"r1-stage1-worker-v1"},{"operation":"R1_TASK_ACQUIRE_LEASE","target_prefix":"task:","scope":"INTERNAL_R1_STATE_ONLY","actor_instance":"r1-stage1-worker-v1"},{"operation":"R1_TASK_CHECKPOINT","target_prefix":"task:","scope":"INTERNAL_R1_STATE_ONLY","actor_instance":"r1-stage1-worker-v1"},{"operation":"R1_SOURCE_REVIEW_COMMIT","target_prefix":"task:","scope":"PUBLIC_TERMS_METADATA_ONLY","actor_instance":"r1-stage1-worker-v1"}]}}
def _repo(root:Path)->tuple[Path,str]:
    remote,seed=root/"remote.git",root/"seed";_git(root,"init","--bare",str(remote));_git(root,"init",str(seed));_git(seed,"config","user.name","stage1-selftest");_git(seed,"config","user.email","stage1@example.invalid");_git(seed,"remote","add","origin",str(remote));policy=json.dumps({"record":"VNEXT_AUTHORIZATION_CONTRACT_v0"},sort_keys=True,indent=2)+"\n";_write(seed/AUTH_CONTRACT_PATH,policy);_write(seed/GRANT_PATH,json.dumps(_grant(_blob(policy.encode())),sort_keys=True,indent=2)+"\n");_write(seed/OWNER_GATE_PATH,json.dumps({"owner_decision":{"github_record_comment_id":5367308652}},indent=2)+"\n");_git(seed,"add",AUTH_CONTRACT_PATH,GRANT_PATH,OWNER_GATE_PATH);_git(seed,"commit","-m","canonical authority");main=_git(seed,"rev-parse","HEAD");_git(seed,"branch","-M","main");_git(seed,"push","-u","origin","main")
    c=empty_control(activation_receipt_id="a",canonical_main=main,audited_implementation_head="b"*40,runtime_genesis=main,activated_at=datetime.fromisoformat("2026-08-21T07:30:00+00:00"));_write(seed/CONTROL_PATH,json.dumps(c,sort_keys=True,indent=2)+"\n");_write(seed/R1_STATE_PATH,json.dumps(empty_state(),sort_keys=True,indent=2)+"\n");_git(seed,"add",CONTROL_PATH,R1_STATE_PATH);_git(seed,"commit","-m","runtime anchor");anchor=_git(seed,"rev-parse","HEAD");c["runtime_genesis"]=anchor;_write(seed/CONTROL_PATH,json.dumps(c,sort_keys=True,indent=2)+"\n");_git(seed,"add",CONTROL_PATH);_git(seed,"commit","-m","runtime control");h=_git(seed,"rev-parse","HEAD");_git(seed,"push","origin",f"{h}:{RUNTIME_REF}");_git(seed,"push","origin",f"{h}:{HIGH_WATER_REF}");return remote,main
def _env()->dict:return {"schema_version":ENQUEUE_SCHEMA,"stage_id":STAGE_ID,"candidate_id":"source-a","docs_hash":"docs-a","requested_final_state":AuditState.REVIEWED_NO_ADMISSION.value,"verdict_reason":"supplied evidence supports no admission","evidence_refs":["governance:evidence-a"]}
def _expect(exc,fn):
    try:fn()
    except exc:return
    raise AssertionError("expected "+exc.__name__)
def selftest()->int:
    validate_write_path(RUNTIME_BRANCH,CONTROL_PATH);validate_write_path(RUNTIME_BRANCH,R1_STATE_PATH);_expect(Stage1Denied,lambda:validate_write_path("main",CONTROL_PATH));_expect(Stage1Denied,lambda:validate_write_path(RUNTIME_BRANCH,"governance/x"));_expect(Stage1Denied,lambda:reject_runtime_artifact_as_authority("AUTHORIZATION_GRANT",{}));bad=_env();bad["enqueue_authorization"]={};_expect(Stage1Denied,lambda:_validate_envelope(bad))
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);remote,main=_repo(root);c1,c2=root/"c1",root/"c2";_git(root,"clone","--quiet",str(remote),str(c1));_git(root,"clone","--quiet",str(remote),str(c2));a=GitCanonicalAuthorityAdapter._selftest(c1,main);d=a.authorize(operation=ENQUEUE_OPERATION,target=ENQUEUE_TARGET,scope=ENQUEUE_SCOPE,actor_kind="router",now=datetime.fromisoformat("2026-08-21T08:00:00+00:00"),activation_deadline=datetime.fromisoformat("2026-08-28T07:30:00+00:00"));assert d.decision["grant_ref"].startswith("grant-");_expect(AuthorizationDenied,lambda:a.authorize(operation=ENQUEUE_OPERATION,target="comment:1",scope=ENQUEUE_SCOPE,actor_kind="router",now=datetime.fromisoformat("2026-08-21T08:00:00+00:00"),activation_deadline=datetime.fromisoformat("2026-08-28T07:30:00+00:00")))
        r1,r2=GitRuntimeStateAdapter._selftest(c1),GitRuntimeStateAdapter._selftest(c2);old,x,_=r1._snapshot();old2,y,_=r2._snapshot();assert old==old2
        for ctrl,cid in ((x,"cas-a"),(y,"cas-b")):ctrl["runtime_generation"]+=1;ctrl["invocation_lease"]={"claim_id":cid,"worker_id":a.worker_actor,"claimed_at":"2026-08-21T08:00:00+00:00","expires_at":"2026-08-21T08:15:00+00:00","base_head":old}
        h1=r1._commit_updates(old,{CONTROL_PATH:x},"cas-a");h2=r2._commit_updates(old,{CONTROL_PATH:y},"cas-b");r1._cas_push(old,h1);_expect(RemoteCasConflict,lambda:r2._cas_push(old,h2));now=datetime.fromisoformat("2026-08-21T08:20:00+00:00");claim=r1.claim(expected_main=main,worker_id=a.worker_actor,claim_id="work-a",now=now)
        with tempfile.TemporaryDirectory() as sd:s=_load_store(Path(sd),claim.r1_state);receipt=_process_claimed_one(store=s,envelope=_env(),control=claim.control,authority=a,now=now);assert receipt;persisted=r1.persist_r1_state(claim,s.read())
        restart=GitRuntimeStateAdapter._selftest(c2);claim2=restart.claim(expected_main=main,worker_id=a.worker_actor,claim_id="work-b",now=datetime.fromisoformat("2026-08-21T08:40:00+00:00"));assert claim2.control["terminal_count"]==1;final,control=restart.finish(claim2);assert control["terminal_count"]==1 and control["invocation_lease"] is None;proc=__import__('multiverse_r1_stage1_authority_v1')._run(["git","push","--quiet","--force","origin",f"{old}:{RUNTIME_REF}"],cwd=c1,check=False);assert proc.returncode==0;_expect(Stage1Tamper,restart._snapshot)
    for m in ("CANONICAL_GIT_AUTHORITY_PROVENANCE_ENFORCED","CALLER_SUPPLIED_AUTHORIZATION_CONTEXT_REJECTED","EXPLICIT_AUTHORIZED_ENQUEUE_ONLY","RAW_GITHUB_EVENT_COMMENT_URL_NOT_AUTHORITY","REMOTE_SINGLE_INVOCATION_CAS_DISTINCT_PROCESS_REPLAY_REJECTED","RUNTIME_BRANCH_HIGH_WATER_ROLLBACK_DETECTED","DURABLE_R1_RECEIPT_RECONCILED_BEFORE_NEXT_CLAIM","TERMINAL_25_OR_7_DAY_AUTO_PAUSE_CONTRACT_ENFORCED","RUNTIME_STATE_SECOND_AUTHORITY_REJECTED","ADMITTED_AND_PERMISSION_LIKE_RUNTIME_STATE_DENIED","NETWORK_PUBLIC_WEB_ACCESS_PERFORMED=false","RUNTIME_ACTIVATION_PERFORMED=false"):print(m)
    print("MULTIVERSE_R1_STAGE1_CONTROL_PLANE_SELFTEST_PASS");return 0
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:return selftest()
    print("R1_STAGE1_LIBRARY_ONLY_RUNTIME_OFF_NO_ACTIVATION_WORKFLOW");return 0
if __name__=="__main__":raise SystemExit(main())
