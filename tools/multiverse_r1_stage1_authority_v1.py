"""Canonical Git authority adapter for R1 Stage 1.

Reads the separate Stage-1 P1 grant, Owner Gate record, and Authorization
Contract only from the exact expected canonical main commit. Caller-supplied
grant/revocation/safe-mode state is never accepted.
"""
from __future__ import annotations
import hashlib,json,subprocess
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any
from multiverse_r1_auth_v1 import AuthorizationDenied,AuthorizationRuntime,validate_authorization

CANONICAL_REPO="fufufu1116/multiverse-research"
RUNTIME_BRANCH="runtime/r1-source-audit-stage1-v1"
GRANT_PATH="governance/MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_OPERATION_GRANT_20260821_v1.json"
OWNER_GATE_PATH="governance/MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_OWNER_GATE_APPROVAL_20260821_v1.json"
AUTH_CONTRACT_PATH="multiverse_vnext/VNEXT_AUTHORIZATION_CONTRACT_v0.json"
ENQUEUE_OPERATION="R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK"
ENQUEUE_TARGET=RUNTIME_BRANCH
ENQUEUE_SCOPE="GITHUB_INTERNAL_SOURCE_AUDIT_ADMIN_METADATA_ONLY"

class Stage1AuthorityDenied(RuntimeError):pass

def _deny(code:str,exc=Stage1AuthorityDenied):raise exc(code)
def _nonempty(v:Any)->bool:return isinstance(v,str) and bool(v)
def _hex40(v:Any)->bool:return _nonempty(v) and len(v)==40 and all(c in "0123456789abcdef" for c in v.lower())
def _strict_int(v:Any)->bool:return isinstance(v,int) and not isinstance(v,bool) and v>=0
def _iso(v:datetime)->str:
    if v.tzinfo is None:_deny("AUTHORITY_TIME_NOT_AWARE")
    return v.astimezone(timezone.utc).isoformat()
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _run(cmd:list[str],*,cwd:Path,input_bytes:bytes|None=None,env:dict|None=None,check:bool=True)->subprocess.CompletedProcess:
    p=subprocess.run(cmd,cwd=cwd,input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if check and p.returncode!=0:raise Stage1AuthorityDenied("GIT_COMMAND_FAILED:"+p.stderr.decode(errors="replace").strip())
    return p
def _git(cwd:Path,*args:str,input_bytes:bytes|None=None,env:dict|None=None,check:bool=True)->str:
    return _run(["git",*args],cwd=cwd,input_bytes=input_bytes,env=env,check=check).stdout.decode().strip()
def _normalize_origin(url:str)->str:
    u=url.strip()
    if u.endswith(".git"):u=u[:-4]
    if u.startswith("git@github.com:"):u="https://github.com/"+u.split(":",1)[1]
    return u.rstrip("/")

@dataclass(frozen=True)
class AuthorityDecision:
    decision:dict
    runtime:AuthorizationRuntime

class GitCanonicalAuthorityAdapter:
    """Control-plane decision issuer backed only by exact canonical Git facts."""
    def __init__(self,repo_path:Path,expected_main:str,*,allow_test_remote:bool=False):
        self.repo_path=Path(repo_path);self.expected_main=expected_main;self.allow_test_remote=allow_test_remote
        if not _hex40(expected_main):_deny("AUTHORITY_EXPECTED_MAIN_INVALID")
        origin=_git(self.repo_path,"remote","get-url","origin")
        if not allow_test_remote and _normalize_origin(origin)!=f"https://github.com/{CANONICAL_REPO}":_deny("AUTHORITY_ORIGIN_NOT_CANONICAL")
        self._refresh_and_load()
    @classmethod
    def production(cls,repo_path:Path,expected_main:str):return cls(repo_path,expected_main,allow_test_remote=False)
    @classmethod
    def _selftest(cls,repo_path:Path,expected_main:str):return cls(repo_path,expected_main,allow_test_remote=True)
    def _refresh_and_load(self)->None:
        _git(self.repo_path,"fetch","--quiet","origin","main")
        current=_git(self.repo_path,"rev-parse","FETCH_HEAD")
        if current!=self.expected_main:_deny("AUTHORITY_CANONICAL_MAIN_DRIFT")
        try:
            grant=json.loads(_git(self.repo_path,"show",f"{current}:{GRANT_PATH}"))
            gate=json.loads(_git(self.repo_path,"show",f"{current}:{OWNER_GATE_PATH}"))
            policy=json.loads(_git(self.repo_path,"show",f"{current}:{AUTH_CONTRACT_PATH}"))
        except Exception as exc:raise Stage1AuthorityDenied("AUTHORITY_CANONICAL_JSON_INVALID") from exc
        grant_blob=_git(self.repo_path,"rev-parse",f"{current}:{GRANT_PATH}")
        policy_blob=_git(self.repo_path,"rev-parse",f"{current}:{AUTH_CONTRACT_PATH}")
        if grant.get("status")!="ACTIVE_ONLY_WHEN_READ_FROM_CANONICAL_MAIN_AFTER_AUDIT":_deny("AUTHORITY_GRANT_STATUS_INVALID")
        if grant.get("canonical_repo")!=CANONICAL_REPO or grant.get("owner_gate_approval_comment")!=5367308652:_deny("AUTHORITY_GRANT_OWNER_SCOPE_MISMATCH")
        if gate.get("owner_decision",{}).get("github_record_comment_id")!=5367308652:_deny("AUTHORITY_OWNER_GATE_RECORD_MISMATCH")
        p=grant.get("authorization_contract",{})
        if p.get("path")!=AUTH_CONTRACT_PATH or p.get("blob_sha")!=policy_blob:_deny("AUTHORITY_POLICY_PROVENANCE_MISMATCH")
        if policy.get("record")!="VNEXT_AUTHORIZATION_CONTRACT_v0":_deny("AUTHORITY_POLICY_RECORD_MISMATCH")
        g=grant.get("grant",{})
        if g.get("permission_class")!="P1_REVERSIBLE_INTERNAL_WRITE" or g.get("permission_ceiling")!="P1_REVERSIBLE_INTERNAL_WRITE":_deny("AUTHORITY_GRANT_PERMISSION_INVALID")
        if g.get("safe_mode_active") is not False or not _strict_int(g.get("revocation_generation")) or not _strict_int(g.get("safe_mode_generation")):_deny("AUTHORITY_GRANT_GENERATIONS_INVALID")
        for f in ("grant_ref","router_actor_instance","worker_actor_instance"):
            if not _nonempty(g.get(f)):_deny("AUTHORITY_GRANT_ACTOR_INVALID")
        ops=g.get("operations")
        if not isinstance(ops,list) or len(ops)!=5:_deny("AUTHORITY_GRANT_OPERATIONS_INVALID")
        rules={o["operation"]:o for o in ops if isinstance(o,dict) and _nonempty(o.get("operation"))}
        if len(rules)!=len(ops):_deny("AUTHORITY_OPERATION_RULE_DUPLICATE")
        ttl=g.get("decision_ttl_seconds",300)
        if not _strict_int(ttl) or ttl<1 or ttl>900:_deny("AUTHORITY_DECISION_TTL_INVALID")
        self.grant=grant;self.grant_blob_sha=grant_blob;self.policy_blob_sha=policy_blob;self.operation_rules=rules
        self.router_actor=g["router_actor_instance"];self.worker_actor=g["worker_actor_instance"];self.grant_ref=g["grant_ref"]
        self.revocation_generation=g["revocation_generation"];self.safe_mode_generation=g["safe_mode_generation"];self.safe_mode_active=g["safe_mode_active"];self.decision_ttl_seconds=ttl
    def _rule(self,operation:str,target:str,scope:str,actor:str)->None:
        self._refresh_and_load();r=self.operation_rules.get(operation)
        if not r:_deny("AUTHORITY_OPERATION_NOT_GRANTED",AuthorizationDenied)
        if r.get("scope")!=scope or r.get("actor_instance")!=actor:_deny("AUTHORITY_RULE_SCOPE_ACTOR_MISMATCH",AuthorizationDenied)
        exact,prefix=r.get("target_exact"),r.get("target_prefix")
        if exact is not None:
            if target!=exact:_deny("AUTHORITY_TARGET_MISMATCH",AuthorizationDenied)
        elif _nonempty(prefix):
            if not target.startswith(prefix) or target==prefix:_deny("AUTHORITY_TARGET_PREFIX_MISMATCH",AuthorizationDenied)
        else:_deny("AUTHORITY_TARGET_RULE_INVALID")
    def authorize(self,*,operation:str,target:str,scope:str,actor_kind:str,now:datetime,activation_deadline:datetime)->AuthorityDecision:
        actor=self.router_actor if actor_kind=="router" else self.worker_actor if actor_kind=="worker" else None
        if actor is None:_deny("AUTHORITY_ACTOR_KIND_INVALID")
        self._rule(operation,target,scope,actor)
        if now.tzinfo is None or activation_deadline.tzinfo is None:_deny("AUTHORITY_TIME_NOT_AWARE")
        n=now.astimezone(timezone.utc);deadline=activation_deadline.astimezone(timezone.utc)
        if n>=deadline:_deny("AUTHORITY_STAGE_DEADLINE_REACHED")
        exp=min(n+timedelta(seconds=self.decision_ttl_seconds),deadline)
        d={"authorization_decision_id":"auth-stage1-"+_digest([self.expected_main,self.grant_blob_sha,operation,target,actor,_iso(n)])[:20],"policy_generation":self.grant["authorization_contract"]["policy_generation"],"policy_digest":self.policy_blob_sha,"actor_role":"EXECUTION","actor_instance":actor,"operation":operation,"target":target,"permission_class_requested":"P1_REVERSIBLE_INTERNAL_WRITE","permission_ceiling":"P1_REVERSIBLE_INTERNAL_WRITE","scope":{"operation":operation,"target":target,"data_exposure_scope":scope},"data_exposure_scope":scope,"issued_at":_iso(n),"expires_at":_iso(exp),"grant_ref":self.grant_ref,"owner_gate_ref":None,"revocation_generation_seen":self.revocation_generation,"safe_mode_generation_seen":self.safe_mode_generation,"decision":"ALLOW","reason_codes":["CANONICAL_STAGE1_P1_GRANT"],"evidence_refs":[f"git:{self.expected_main}:{GRANT_PATH}:{self.grant_blob_sha}"]}
        runtime=AuthorizationRuntime(d["policy_generation"],self.policy_blob_sha,self.revocation_generation,self.safe_mode_generation,n,"EXECUTION",actor,frozenset({self.grant_ref}),None,self.safe_mode_active)
        validate_authorization(d,runtime,operation=operation,target=target,permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope=scope)
        return AuthorityDecision(d,runtime)
