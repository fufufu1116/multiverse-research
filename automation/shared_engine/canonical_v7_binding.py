"""Exact GitHub PR #88 v7 contract binding for shared engine Candidate."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from integration_bridge import IntegrationBinding, BridgeError, validate_receipt
CANONICAL_REPO="fufufu1116/multiverse-research"
V7_HEAD="4a72ef46116043094c7a8e494404956925a5b3bf"
V7_BRANCH="agent/automation-orchestrator-provider-adapter-contract-v7-20260903-v1"
V7_PREDECESSOR="e8c27fafcdb2e9ed4c54fdbc4f72d6d2fd386f0f"
CANONICAL_MAIN="040d37f0a4e426cf2e119706484c90cbb48f0e56"
V7_MANIFEST_SHA256="35a769362d97af06259c49b7d415e5885f258c215c84f3eab63528b98c639652"
V7_REQUEST_AUTHORITY={"candidate_only":True,"external_effect":False,"live_provider":False,"network":False,"production":False,"runtime":False,"secret_credential":False,"spend":False}
@dataclass(frozen=True)
class CanonicalV7Provenance:
    repo:str=CANONICAL_REPO; head:str=V7_HEAD; branch:str=V7_BRANCH; predecessor:str=V7_PREDECESSOR; canonical_main:str=CANONICAL_MAIN; manifest_sha256:str=V7_MANIFEST_SHA256
    def assert_fresh_binding(self,*,fresh_main:str,fresh_v7_head:str)->None:
        if fresh_main!=self.canonical_main: raise BridgeError("CANONICAL_V7_MAIN_DRIFT")
        if fresh_v7_head!=self.head: raise BridgeError("CANONICAL_V7_HEAD_DRIFT")

def v7_result_to_bridge_receipt(job:dict[str,Any],result:dict[str,Any],*,local_binding:IntegrationBinding)->dict[str,Any]:
    if job.get("authority")!={"candidate_only":True,"live_provider":False,"production":False,"runtime":False,"spend":False}: raise BridgeError("CANONICAL_V7_JOB_AUTHORITY")
    if job.get("canonical_main")!=CANONICAL_MAIN: raise BridgeError("CANONICAL_V7_JOB_MAIN")
    if job.get("role") not in {"IMPLEMENT","LAB","AUDIT"}: raise BridgeError("CANONICAL_V7_JOB_ROLE")
    if not isinstance(result,dict) or not isinstance(result.get("evidence_ref"),str) or not result["evidence_ref"]: raise BridgeError("CANONICAL_V7_EVIDENCE_REQUIRED")
    role=job["role"]
    if role=="IMPLEMENT":
        if result.get("status")!="READY" or result.get("candidate_head")!=job.get("candidate_head"): raise BridgeError("CANONICAL_V7_IMPLEMENT_INVALID")
        d,c=result.get("diff_lines"),result.get("cost_microusd")
        if not isinstance(d,int) or isinstance(d,bool) or d<0: raise BridgeError("CANONICAL_V7_IMPLEMENT_DIFF_LINES")
        if not isinstance(c,int) or isinstance(c,bool) or c!=0: raise BridgeError("CANONICAL_V7_IMPLEMENT_COST")
        bridge_result=dict(result); bridge_result["code"]="canonical-v7-accepted-result"
    else:
        if result.get("reviewed_head")!=job.get("candidate_head"): raise BridgeError(f"CANONICAL_V7_{role}_HEAD")
        if result.get("verdict") not in {"PASS","FIX_REQUIRED"}: raise BridgeError(f"CANONICAL_V7_{role}_VERDICT")
        if result["verdict"]=="FIX_REQUIRED" and (not isinstance(result.get("code"),str) or not result["code"] or not isinstance(result.get("detail"),str)): raise BridgeError(f"CANONICAL_V7_{role}_FIX_SCHEMA")
        bridge_result=dict(result)
    receipt={"operation_key":job["operation_key"],"task_id":job["task_id"],"role":role,"semantic_generation":job["semantic_generation"],"candidate_branch":local_binding.candidate_branch,"candidate_head":local_binding.candidate_head,"canonical_main":local_binding.canonical_main,"provider_adapter_head":V7_HEAD,"evidence_ref":result["evidence_ref"],"result":bridge_result,"authority":dict(V7_REQUEST_AUTHORITY)}
    return validate_receipt(local_binding,receipt)
