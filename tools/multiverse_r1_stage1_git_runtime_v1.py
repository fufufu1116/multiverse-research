"""Durable Git CAS runtime-state adapter for R1 Stage 1."""
from __future__ import annotations
import copy,json,os,tempfile
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Optional
from multiverse_r1_state_v1 import validate_state
from multiverse_r1_stage1_authority_v1 import CANONICAL_REPO,RUNTIME_BRANCH,_git,_run,_hex40,_nonempty,_normalize_origin

STAGE_SCHEMA="MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_SCHEMA_v2"
STAGE_ID="R1_LIMITED_INTERNAL_RUNTIME_STAGE1"
RUNTIME_REF=f"refs/heads/{RUNTIME_BRANCH}"
HIGH_WATER_REF="refs/heads/runtime/r1-source-audit-stage1-v1-highwater"
CONTROL_PATH="runtime/r1_source_audit_stage1/tasks/_stage1_control.json"
R1_STATE_PATH="runtime/r1_source_audit_stage1/receipts/r1_state.json"
MAX_TERMINAL_TASKS=25;WINDOW_DAYS=7;INVOCATION_LEASE_MINUTES=15
ALLOWED_PREFIXES=("runtime/r1_source_audit_stage1/cache/","runtime/r1_source_audit_stage1/tasks/","runtime/r1_source_audit_stage1/receipts/","runtime/r1_source_audit_stage1/exceptions/")
CONTROL_FIELDS={"schema_version","stage_id","activation_receipt_id","canonical_main","audited_implementation_head","runtime_branch","runtime_genesis","activated_at","terminal_count","counted_receipt_ids","paused","pause_reason","runtime_generation","invocation_lease"}
LEASE_FIELDS={"claim_id","worker_id","claimed_at","expires_at","base_head"}
AUTHORITY_ROLES={"OWNER_GATE","AUTHORIZATION_GRANT","PERMISSION_EVIDENCE","SOURCE_ADMISSION_RECEIPT","CANONICAL_GOVERNANCE_FACT"}

class Stage1Denied(RuntimeError):pass
class Stage1Paused(Stage1Denied):pass
class Stage1Tamper(Stage1Denied):pass
class RemoteCasConflict(Stage1Denied):pass
def _deny(c:str,e=Stage1Denied):raise e(c)
def _strict_int(v:Any)->bool:return isinstance(v,int) and not isinstance(v,bool) and v>=0
def _utc(v:str)->datetime:
    try:o=datetime.fromisoformat(v.replace("Z","+00:00"))
    except Exception as exc:raise Stage1Denied("TIME_INVALID") from exc
    if o.tzinfo is None:_deny("TIME_NOT_OFFSET_AWARE")
    return o.astimezone(timezone.utc)
def _iso(v:datetime)->str:
    if v.tzinfo is None:_deny("TIME_NOT_OFFSET_AWARE")
    return v.astimezone(timezone.utc).isoformat()
def _json_bytes(v:Mapping[str,Any])->bytes:return (json.dumps(v,sort_keys=True,indent=2)+"\n").encode()

def validate_write_path(branch:str,path:str)->None:
    if branch!=RUNTIME_BRANCH:_deny("RUNTIME_WRONG_BRANCH")
    if not _nonempty(path):_deny("RUNTIME_PATH_INVALID")
    p=PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:_deny("RUNTIME_PATH_TRAVERSAL")
    n=str(p)
    if n.startswith("governance/") or n=="governance" or n.startswith(".github/"):_deny("RUNTIME_CANONICAL_OR_GOVERNANCE_WRITE_DENIED")
    if not any(n.startswith(x) for x in ALLOWED_PREFIXES):_deny("RUNTIME_PATH_OUTSIDE_ALLOWED_PREFIX")
def reject_runtime_artifact_as_authority(role:str,artifact:Mapping[str,Any])->None:
    if role in AUTHORITY_ROLES:_deny("RUNTIME_ARTIFACT_CANNOT_BE_AUTHORITY")
    _deny("UNKNOWN_AUTHORITY_ROLE_DENIED")

def empty_control(*,activation_receipt_id:str,canonical_main:str,audited_implementation_head:str,runtime_genesis:str,activated_at:datetime)->dict:
    if not _nonempty(activation_receipt_id) or not all(_hex40(x) for x in (canonical_main,audited_implementation_head,runtime_genesis)):_deny("ACTIVATION_IDENTITY_INVALID")
    return {"schema_version":STAGE_SCHEMA,"stage_id":STAGE_ID,"activation_receipt_id":activation_receipt_id,"canonical_main":canonical_main,"audited_implementation_head":audited_implementation_head,"runtime_branch":RUNTIME_BRANCH,"runtime_genesis":runtime_genesis,"activated_at":_iso(activated_at),"terminal_count":0,"counted_receipt_ids":[],"paused":False,"pause_reason":None,"runtime_generation":0,"invocation_lease":None}
def validate_control(c:Mapping[str,Any])->None:
    if not isinstance(c,dict) or set(c)!=CONTROL_FIELDS:_deny("STAGE_CONTROL_SCHEMA")
    if c["schema_version"]!=STAGE_SCHEMA or c["stage_id"]!=STAGE_ID or c["runtime_branch"]!=RUNTIME_BRANCH:_deny("STAGE_CONTROL_IDENTITY")
    if not _nonempty(c["activation_receipt_id"]) or not all(_hex40(c[x]) for x in ("canonical_main","audited_implementation_head","runtime_genesis")):_deny("STAGE_CONTROL_IDENTITY_FIELDS")
    _utc(c["activated_at"])
    if not _strict_int(c["terminal_count"]) or not _strict_int(c["runtime_generation"]):_deny("STAGE_CONTROL_INT")
    ids=c["counted_receipt_ids"]
    if not isinstance(ids,list) or not all(_nonempty(x) for x in ids) or len(ids)!=len(set(ids)) or c["terminal_count"]!=len(ids):_deny("STAGE_CONTROL_RECEIPTS")
    if not isinstance(c["paused"],bool):_deny("STAGE_CONTROL_PAUSED_TYPE")
    if c["pause_reason"] is not None and not _nonempty(c["pause_reason"]):_deny("STAGE_CONTROL_PAUSE_REASON")
    l=c["invocation_lease"]
    if l is not None:
        if not isinstance(l,dict) or set(l)!=LEASE_FIELDS:_deny("STAGE_CONTROL_LEASE_SCHEMA")
        if not all(_nonempty(l[x]) for x in ("claim_id","worker_id","base_head")) or not _hex40(l["base_head"]):_deny("STAGE_CONTROL_LEASE_IDENTITY")
        if _utc(l["expires_at"])<=_utc(l["claimed_at"]):_deny("STAGE_CONTROL_LEASE_TIME")
def reconcile_receipts(c:Mapping[str,Any],state:Mapping[str,Any])->dict:
    validate_control(c);validate_state(dict(state));ids=sorted({r["receipt_id"] for r in state["receipts_by_idempotency"].values()});known=set(c["counted_receipt_ids"]);missing=[x for x in ids if x not in known];o=copy.deepcopy(c)
    if o["terminal_count"]+len(missing)>MAX_TERMINAL_TASKS:_deny("RECONCILE_RECEIPTS_EXCEED_TERMINAL_CEILING",Stage1Tamper)
    o["counted_receipt_ids"].extend(missing);o["terminal_count"]+=len(missing)
    if o["terminal_count"]>=MAX_TERMINAL_TASKS:o["paused"]=True;o["pause_reason"]="STAGE_TERMINAL_CEILING_REACHED"
    validate_control(o);return o

@dataclass(frozen=True)
class RuntimeClaim:
    claim_id:str;worker_id:str;runtime_head:str;control:dict;r1_state:dict

class GitRuntimeStateAdapter:
    def __init__(self,repo_path:Path,*,allow_test_remote:bool=False):
        self.repo_path=Path(repo_path);origin=_git(self.repo_path,"remote","get-url","origin")
        if not allow_test_remote and _normalize_origin(origin)!=f"https://github.com/{CANONICAL_REPO}":_deny("RUNTIME_ORIGIN_NOT_CANONICAL")
    @classmethod
    def production(cls,repo_path:Path):return cls(repo_path,allow_test_remote=False)
    @classmethod
    def _selftest(cls,repo_path:Path):return cls(repo_path,allow_test_remote=True)
    def _ls_ref(self,ref:str)->Optional[str]:
        o=_git(self.repo_path,"ls-remote","--heads","origin",ref)
        if not o:return None
        sha,name=o.split()[:2]
        if name!=ref or not _hex40(sha):_deny("RUNTIME_REMOTE_REF_INVALID")
        return sha
    def _fetch_ref(self,ref:str)->str:
        _git(self.repo_path,"fetch","--quiet","origin",ref);sha=_git(self.repo_path,"rev-parse","FETCH_HEAD")
        if not _hex40(sha):_deny("RUNTIME_FETCH_HEAD_INVALID")
        return sha
    def _is_ancestor(self,a:str,d:str)->bool:return _run(["git","merge-base","--is-ancestor",a,d],cwd=self.repo_path,check=False).returncode==0
    def _read_json(self,h:str,path:str)->dict:
        validate_write_path(RUNTIME_BRANCH,path)
        try:v=json.loads(_git(self.repo_path,"show",f"{h}:{path}"))
        except Exception as exc:raise Stage1Tamper("RUNTIME_JSON_INVALID") from exc
        if not isinstance(v,dict):_deny("RUNTIME_JSON_NOT_OBJECT",Stage1Tamper)
        return v
    def _commit_updates(self,base:str,updates:Mapping[str,Mapping[str,Any]],message:str)->str:
        if not _hex40(base) or not updates:_deny("RUNTIME_COMMIT_INPUT_INVALID")
        fd,name=tempfile.mkstemp(prefix="stage1-index-");os.close(fd);idx=Path(name);idx.unlink()
        try:
            env=os.environ.copy();env["GIT_INDEX_FILE"]=str(idx);env.setdefault("GIT_AUTHOR_NAME","Multiverse R1 Stage1");env.setdefault("GIT_AUTHOR_EMAIL","r1-stage1@users.noreply.github.com");env.setdefault("GIT_COMMITTER_NAME",env["GIT_AUTHOR_NAME"]);env.setdefault("GIT_COMMITTER_EMAIL",env["GIT_AUTHOR_EMAIL"])
            _git(self.repo_path,"read-tree",base,env=env)
            for p,v in updates.items():
                validate_write_path(RUNTIME_BRANCH,p);blob=_git(self.repo_path,"hash-object","-w","--stdin",input_bytes=_json_bytes(v));_git(self.repo_path,"update-index","--add","--cacheinfo","100644",blob,p,env=env)
            tree=_git(self.repo_path,"write-tree",env=env);commit=_git(self.repo_path,"commit-tree",tree,"-p",base,input_bytes=(message+"\n").encode(),env=env)
            if not _hex40(commit) or not self._is_ancestor(base,commit):_deny("RUNTIME_NON_FF_COMMIT_PROHIBITED")
            return commit
        finally:
            if idx.exists():idx.unlink()
    def _advance_high_water(self,h:str)->None:
        high=self._ls_ref(HIGH_WATER_REF)
        if high is None:_deny("RUNTIME_HIGH_WATER_REF_MISSING",Stage1Tamper)
        self._fetch_ref(HIGH_WATER_REF);self._fetch_ref(RUNTIME_REF)
        if not self._is_ancestor(high,h):_deny("RUNTIME_HIGH_WATER_NOT_ANCESTOR",Stage1Tamper)
        if high==h:return
        p=_run(["git","push","--quiet","origin",f"{h}:{HIGH_WATER_REF}"],cwd=self.repo_path,check=False)
        if p.returncode!=0:
            latest=self._ls_ref(HIGH_WATER_REF)
            if latest is None:_deny("RUNTIME_HIGH_WATER_DISAPPEARED",Stage1Tamper)
            self._fetch_ref(HIGH_WATER_REF);self._fetch_ref(RUNTIME_REF)
            if not self._is_ancestor(latest,h):_deny("RUNTIME_HIGH_WATER_CONFLICT",Stage1Tamper)
    def _cas_push(self,base:str,new:str)->None:
        if not self._is_ancestor(base,new):_deny("RUNTIME_NON_FF_PUSH_PROHIBITED")
        p=_run(["git","push","--quiet",f"--force-with-lease={RUNTIME_REF}:{base}","origin",f"{new}:{RUNTIME_REF}"],cwd=self.repo_path,check=False)
        if p.returncode!=0:raise RemoteCasConflict("RUNTIME_EXPECTED_OLD_HEAD_CAS_CONFLICT")
        self._advance_high_water(new)
    def _snapshot(self)->tuple[str,dict,dict]:
        h,high=self._ls_ref(RUNTIME_REF),self._ls_ref(HIGH_WATER_REF)
        if h is None or high is None:_deny("RUNTIME_REQUIRED_REFS_MISSING",Stage1Tamper)
        if self._fetch_ref(RUNTIME_REF)!=h:_deny("RUNTIME_REF_CHANGED_DURING_FETCH",RemoteCasConflict)
        self._fetch_ref(HIGH_WATER_REF);c=self._read_json(h,CONTROL_PATH);s=self._read_json(h,R1_STATE_PATH);validate_control(c);validate_state(s)
        if not self._is_ancestor(c["runtime_genesis"],h):_deny("RUNTIME_GENESIS_ANCESTRY_TAMPER",Stage1Tamper)
        if not self._is_ancestor(high,h):_deny("RUNTIME_BRANCH_ROLLBACK_OR_REWRITE_DETECTED",Stage1Tamper)
        self._advance_high_water(h);return h,c,s
    def claim(self,*,expected_main:str,worker_id:str,claim_id:str,now:datetime)->RuntimeClaim:
        if not _nonempty(worker_id) or not _nonempty(claim_id):_deny("RUNTIME_CLAIM_IDENTITY_INVALID")
        h,c,s=self._snapshot()
        if c["canonical_main"]!=expected_main:_deny("RUNTIME_CONTROL_MAIN_MISMATCH")
        r=reconcile_receipts(c,s);deadline=_utc(r["activated_at"])+timedelta(days=WINDOW_DAYS);n=now.astimezone(timezone.utc)
        if r["paused"] or r["terminal_count"]>=MAX_TERMINAL_TASKS:
            if r!=c:r["runtime_generation"]+=1;nh=self._commit_updates(h,{CONTROL_PATH:r},"Reconcile Stage1 receipts and pause");self._cas_push(h,nh)
            raise Stage1Paused("STAGE_ALREADY_PAUSED")
        if n>=deadline:
            r["paused"]=True;r["pause_reason"]="STAGE_TIME_CEILING_REACHED";r["invocation_lease"]=None;r["runtime_generation"]+=1;nh=self._commit_updates(h,{CONTROL_PATH:r},"Pause Stage1 at seven-day ceiling");self._cas_push(h,nh);raise Stage1Paused("STAGE_TIME_CEILING_REACHED")
        l=r["invocation_lease"]
        if l is not None and n<_utc(l["expires_at"]):_deny("SECOND_WORKER_OR_PARALLEL_INVOCATION")
        o=copy.deepcopy(r);o["invocation_lease"]={"claim_id":claim_id,"worker_id":worker_id,"claimed_at":_iso(n),"expires_at":_iso(min(n+timedelta(minutes=INVOCATION_LEASE_MINUTES),deadline)),"base_head":h};o["runtime_generation"]+=1;nh=self._commit_updates(h,{CONTROL_PATH:o},f"Claim Stage1 {claim_id}");self._cas_push(h,nh);return RuntimeClaim(claim_id,worker_id,nh,o,s)
    def persist_r1_state(self,claim:RuntimeClaim,state:Mapping[str,Any])->RuntimeClaim:
        validate_state(dict(state));remote=self._ls_ref(RUNTIME_REF)
        if remote!=claim.runtime_head:_deny("RUNTIME_CLAIM_HEAD_LOST",RemoteCasConflict)
        self._fetch_ref(RUNTIME_REF);c=self._read_json(remote,CONTROL_PATH);l=c.get("invocation_lease")
        if not l or l.get("claim_id")!=claim.claim_id or l.get("worker_id")!=claim.worker_id:_deny("RUNTIME_CLAIM_NOT_CURRENT",RemoteCasConflict)
        nh=self._commit_updates(remote,{R1_STATE_PATH:dict(state)},f"Persist Stage1 R1 state {claim.claim_id}");self._cas_push(remote,nh);return RuntimeClaim(claim.claim_id,claim.worker_id,nh,c,dict(state))
    def finish(self,claim:RuntimeClaim)->tuple[str,dict]:
        remote=self._ls_ref(RUNTIME_REF)
        if remote!=claim.runtime_head:_deny("RUNTIME_FINISH_HEAD_LOST",RemoteCasConflict)
        self._fetch_ref(RUNTIME_REF);c=self._read_json(remote,CONTROL_PATH);s=self._read_json(remote,R1_STATE_PATH);l=c.get("invocation_lease")
        if not l or l.get("claim_id")!=claim.claim_id or l.get("worker_id")!=claim.worker_id:_deny("RUNTIME_FINISH_CLAIM_NOT_CURRENT",RemoteCasConflict)
        o=reconcile_receipts(c,s);o["invocation_lease"]=None;o["runtime_generation"]+=1;nh=self._commit_updates(remote,{CONTROL_PATH:o},f"Finish Stage1 {claim.claim_id}");self._cas_push(remote,nh);return nh,o
