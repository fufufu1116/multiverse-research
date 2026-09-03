"""Exact v7 -> Shared Engine execution harness for Integration v8 construction.

Uses the actual stacked PR #88 provider adapter implementation already present in
`automation/`. The provider receipt store remains subordinate evidence; only the
shared Engine SQLite task store can advance workflow state.
"""
from __future__ import annotations
import pathlib
from typing import Any
import db
from domain_registry import validate_domain_task
from integration_bridge import BridgeError, IntegrationBinding, DurableReceiptBoundary, apply_receipt, ROLE_EXPECTED_STATES
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD, v7_result_to_bridge_receipt
from orchestrator_provider_adapter_v7 import (
    ProviderAdapterManifest, DeterministicLocalAdapter, ProviderAdapterReceiptStore,
    provider_request_from_job,
)

V7_MANIFEST = pathlib.Path(__file__).resolve().parents[1] / "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_V7.json"
JOB_AUTHORITY={"candidate_only":True,"live_provider":False,"production":False,"runtime":False,"spend":False}

class ExactV7SharedEngine:
    def __init__(self,binding:IntegrationBinding,bridge_receipt_db:str,provider_receipt_db:str):
        binding.validate()
        if binding.canonical_main!=CANONICAL_MAIN or binding.provider_adapter_head!=V7_HEAD: raise ValueError("EXACT_V7_BINDING_REQUIRED")
        self.binding=binding; self.bridge_receipts=DurableReceiptBoundary(bridge_receipt_db,binding)
        self.manifest=ProviderAdapterManifest.load(V7_MANIFEST)
        self.provider_receipt_db=provider_receipt_db
    def close(self): self.bridge_receipts.close()
    def _validate_persisted_task(self,task_id:str):
        task=db.get_task(task_id)
        if task is None: raise BridgeError("UNKNOWN_TASK")
        validate_domain_task(task['domain'],task['task_type'])
        return task
    def submit(self,domain:str,task_type:str,goal:str,*,requested_capabilities:dict[str,Any]|None=None,resources:set[str]|None=None,priority:int=0)->str:
        validate_domain_task(domain,task_type,requested_capabilities,resources)
        return db.create_task(domain,goal,task_type=task_type,priority=priority)
    def claim_and_start(self,task_id:str,worker_id:str)->int:
        # Revalidate durable task identity at the execution boundary. The DB is the
        # workflow authority, but direct low-level insertion must not bypass domain policy.
        self._validate_persisted_task(task_id)
        gen=db.claim_task(task_id,worker_id)
        db.transition(task_id,"IN_IMPLEMENT",actor="exact_v7_shared_engine",event_type="START",fencing=(worker_id,gen)); return gen
    def renew(self,task_id:str,worker_id:str,claim_generation:int,*,lease_seconds:int|float|None=None)->float:
        return db.renew_lease(task_id,worker_id,claim_generation,lease_seconds=lease_seconds)
    def reclaim_expired(self,task_id:str,worker_id:str,*,lease_seconds:int|None=None)->int:
        return db.reclaim_expired_task(task_id,worker_id,lease_seconds=lease_seconds)
    def _job(self,task_id:str,role:str,generation:int,operation_key:str)->dict[str,Any]:
        task=self._validate_persisted_task(task_id)
        return {"operation_key":operation_key,"task_id":task_id,"role":role,"semantic_generation":generation,
                "candidate_head":self.binding.candidate_head,"candidate_branch":self.binding.candidate_branch,
                "canonical_main":self.binding.canonical_main,"objective":task["goal"],"authority":dict(JOB_AUTHORITY)}
    def _assert_role_precondition(self,task_id:str,role:str,worker_id:str,claim_generation:int):
        db.assert_unexpired_fence(task_id,worker_id,claim_generation)
        task=self._validate_persisted_task(task_id)
        expected=ROLE_EXPECTED_STATES.get(role)
        if expected is None: raise BridgeError(f"RECEIPT_ROLE:{role}")
        if task['state'] not in expected: raise BridgeError(f"ROLE_STATE_MISMATCH:{role}:{task['state']}")
        return task
    def execute_role(self,task_id:str,role:str,semantic_generation:int,operation_key:str,worker_id:str,claim_generation:int,result:dict[str,Any])->str:
        # Reject wrong-state work before provider execution or durable receipt creation.
        # apply_receipt() still repeats the authoritative state/fence checks at mutation.
        self._assert_role_precondition(task_id,role,worker_id,claim_generation)
        job=self._job(task_id,role,semantic_generation,operation_key)
        request=provider_request_from_job(job,self.manifest)
        script={role:{str(semantic_generation+1):dict(result)}}
        store=ProviderAdapterReceiptStore(self.provider_receipt_db,self.manifest)
        try:
            canonical_result=store.execute_local_once(operation_key,request,DeterministicLocalAdapter(script))
        finally: store.close()
        bridge=v7_result_to_bridge_receipt(job,canonical_result,local_binding=self.binding)
        durable=self.bridge_receipts.record(bridge)
        return apply_receipt(task_id,durable,self.binding,worker_id,claim_generation)
    def run_happy_path(self,task_id:str,worker_id:str)->str:
        gen=self.claim_and_start(task_id,worker_id); head=self.binding.candidate_head
        self.execute_role(task_id,"IMPLEMENT",0,f"{task_id}:implement",worker_id,gen,{"status":"READY","candidate_head":head,"diff_lines":1,"cost_microusd":0,"evidence_ref":f"evidence:{task_id}:implement"})
        self.execute_role(task_id,"LAB",0,f"{task_id}:lab",worker_id,gen,{"verdict":"PASS","reviewed_head":head,"evidence_ref":f"evidence:{task_id}:lab"})
        return self.execute_role(task_id,"AUDIT",0,f"{task_id}:audit",worker_id,gen,{"verdict":"PASS","reviewed_head":head,"evidence_ref":f"evidence:{task_id}:audit"})
