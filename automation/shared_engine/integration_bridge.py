"""MULTIVERSE convergence bridge v0.2.

Transport/provider receipts are evidence only. SQLite task state remains the sole
workflow authority, and every worker-owned transition is fenced.
"""
from __future__ import annotations
import hashlib, json, sqlite3, time
from dataclasses import dataclass
from typing import Any
import db

class BridgeError(Exception): pass

@dataclass(frozen=True)
class IntegrationBinding:
    canonical_main:str; candidate_branch:str; candidate_head:str; provider_adapter_head:str
    def validate(self)->None:
        for name,value in (("canonical_main",self.canonical_main),("candidate_head",self.candidate_head),("provider_adapter_head",self.provider_adapter_head)):
            if not (isinstance(value,str) and len(value)==40 and all(c in "0123456789abcdef" for c in value)): raise BridgeError(f"INVALID_SHA:{name}")
        if not isinstance(self.candidate_branch,str) or not self.candidate_branch.startswith("agent/"): raise BridgeError("INVALID_CANDIDATE_BRANCH")

ROLE_NEXT_STATE={"IMPLEMENT":"IN_LAB","LAB":"IN_AUDIT","AUDIT":"DONE"}
ROLE_EXPECTED_STATES={"IMPLEMENT":{"IN_IMPLEMENT"},"LAB":{"IN_LAB"},"AUDIT":{"IN_AUDIT"}}
AUTHORITY={"candidate_only":True,"external_effect":False,"live_provider":False,"network":False,"production":False,"runtime":False,"secret_credential":False,"spend":False}

def _canon(obj:Any)->str:return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def validate_receipt(binding:IntegrationBinding,receipt:dict[str,Any])->dict[str,Any]:
    binding.validate()
    required={"operation_key","task_id","role","semantic_generation","candidate_branch","candidate_head","canonical_main","provider_adapter_head","evidence_ref","result","authority"}
    if not isinstance(receipt,dict):raise BridgeError("RECEIPT_SHAPE")
    if set(receipt)!=required:raise BridgeError("RECEIPT_KEYS")
    if receipt["role"] not in ROLE_NEXT_STATE:raise BridgeError("RECEIPT_ROLE")
    if not isinstance(receipt["operation_key"],str) or not receipt["operation_key"]:raise BridgeError("RECEIPT_OPERATION_KEY")
    if not isinstance(receipt["task_id"],str) or not receipt["task_id"]:raise BridgeError("RECEIPT_TASK_ID")
    if not isinstance(receipt["semantic_generation"],int) or isinstance(receipt["semantic_generation"],bool) or receipt["semantic_generation"]<0:raise BridgeError("RECEIPT_GENERATION")
    if not isinstance(receipt["evidence_ref"],str) or not receipt["evidence_ref"]:raise BridgeError("RECEIPT_EVIDENCE_REQUIRED")
    if receipt["candidate_branch"]!=binding.candidate_branch:raise BridgeError("RECEIPT_BRANCH_MISMATCH")
    if receipt["candidate_head"]!=binding.candidate_head:raise BridgeError("RECEIPT_HEAD_MISMATCH")
    if receipt["canonical_main"]!=binding.canonical_main:raise BridgeError("RECEIPT_MAIN_MISMATCH")
    if receipt["provider_adapter_head"]!=binding.provider_adapter_head:raise BridgeError("RECEIPT_ADAPTER_HEAD_MISMATCH")
    if receipt["authority"]!=AUTHORITY:raise BridgeError("RECEIPT_AUTHORITY_DENIED")
    result=receipt["result"]
    if not isinstance(result,dict):raise BridgeError("RECEIPT_RESULT_SHAPE")
    role=receipt["role"]
    if role=="IMPLEMENT":
        if result.get("status")!="READY":raise BridgeError("IMPLEMENT_STATUS")
        if result.get("candidate_head")!=binding.candidate_head:raise BridgeError("IMPLEMENT_RESULT_HEAD")
        d,c=result.get("diff_lines"),result.get("cost_microusd")
        if not isinstance(d,int) or isinstance(d,bool) or d<0:raise BridgeError("IMPLEMENT_DIFF_LINES")
        if not isinstance(c,int) or isinstance(c,bool) or c!=0:raise BridgeError("IMPLEMENT_COST")
    else:
        if result.get("reviewed_head")!=binding.candidate_head:raise BridgeError(f"{role}_RESULT_HEAD")
        if result.get("verdict") not in ("PASS","FIX_REQUIRED"):raise BridgeError(f"{role}_VERDICT")
        if result["verdict"]=="FIX_REQUIRED":
            if not isinstance(result.get("code"),str) or not result["code"]:raise BridgeError(f"{role}_FIX_CODE")
            if not isinstance(result.get("detail"),str):raise BridgeError(f"{role}_FIX_DETAIL")
    return receipt

class DurableReceiptBoundary:
    def __init__(self,path:str,binding:IntegrationBinding):
        binding.validate();self.binding=binding
        self.conn=sqlite3.connect(path,timeout=10);self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL");self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS receipts(operation_key TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,receipt_json TEXT NOT NULL,created_at REAL NOT NULL)");self.conn.commit()
    def close(self):self.conn.close()
    def record(self,receipt:dict[str,Any])->dict[str,Any]:
        receipt=validate_receipt(self.binding,receipt);text=_canon(receipt);fp=hashlib.sha256(text.encode()).hexdigest();self.conn.execute("BEGIN IMMEDIATE")
        try:
            row=self.conn.execute("SELECT fingerprint,receipt_json FROM receipts WHERE operation_key=?",(receipt["operation_key"],)).fetchone()
            if row:
                if row["fingerprint"]!=fp:raise BridgeError("CONFLICTING_RECEIPT_REPLAY")
                out=json.loads(row["receipt_json"]);validate_receipt(self.binding,out);self.conn.commit();return out
            self.conn.execute("INSERT INTO receipts VALUES(?,?,?,?)",(receipt["operation_key"],fp,text,time.time()));self.conn.commit();return receipt
        except BaseException:self.conn.rollback();raise

def apply_receipt(task_id:str,receipt:dict[str,Any],binding:IntegrationBinding,worker_id:str,claim_generation:int)->str:
    validate_receipt(binding,receipt)
    if receipt["task_id"]!=task_id:raise BridgeError("TASK_BINDING_MISMATCH")
    task=db.get_task(task_id)
    if task is None:raise BridgeError("UNKNOWN_TASK")
    if task["claimed_by"]!=worker_id or task["claim_generation"]!=claim_generation:raise db.LostLeaseError("bridge fencing token is stale")
    role=receipt["role"]
    if task["state"] not in ROLE_EXPECTED_STATES[role]:raise BridgeError(f"ROLE_STATE_MISMATCH:{role}:{task['state']}")
    result=receipt["result"]
    if role in ("LAB","AUDIT") and result["verdict"]=="FIX_REQUIRED":
        target="LAB_FIX_REQUIRED" if role=="LAB" else "AUDIT_FIX_REQUIRED"
        db.transition(task_id,target,actor="integration_bridge",event_type=f"{role}_FIX_REQUIRED",detail={"evidence_ref":receipt["evidence_ref"],"code":result["code"],"detail":result["detail"]},result_update={"last_review_evidence":receipt["evidence_ref"],"last_review_detail":result["detail"]},fencing=(worker_id,claim_generation));return target
    target=ROLE_NEXT_STATE[role];result_update={"last_transport_evidence":receipt["evidence_ref"],"candidate_head":binding.candidate_head}
    db.transition(task_id,target,actor="integration_bridge",event_type=f"{role}_RECEIPT_APPLIED",detail={"evidence_ref":receipt["evidence_ref"],"operation_key":receipt["operation_key"]},result_update=result_update,release=(target=="DONE"),fencing=(worker_id,claim_generation));return target
