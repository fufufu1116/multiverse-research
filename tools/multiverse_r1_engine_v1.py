"""R1 Source Audit Cache + Reliable Task Execution + Owner Exception View."""
import copy,hashlib,json
from datetime import timezone
from multiverse_r1_auth_v1 import AuthorizationDenied,validate_authorization
from multiverse_r1_state_v1 import AuditState,FINAL,PersistentStore,SCHEMA_VERSION,SchemaError,StaleState
CANONICAL_DESIGN_MERGE="ddf0b808aa8e4014dad59dd350c225970f916b89"
class FencingConflict(RuntimeError):pass
class ReceiptConflict(RuntimeError):pass
class DeadLettered(RuntimeError):pass
def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
class R1Engine:
    def __init__(self,store:PersistentStore,canonical_main:str):self.store=store;self.canonical_main=canonical_main
    def _main(self,m):
        if m!=self.canonical_main:raise StaleState("STALE_CANONICAL_MAIN")
    def idem(self,c,h):return f"source-review:{c}:{h}"
    def inspect_candidate(self,*,current_main,candidate_id,docs_hash,authorization,auth_runtime):
        self._main(current_main);validate_authorization(authorization,auth_runtime,operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE",target=f"source-candidate:{candidate_id}",permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY");idem=self.idem(candidate_id,docs_hash)
        def mutate(s):
            x=s["cache"].get(candidate_id)
            if x and x["docs_hash"]==docs_hash:
                if AuditState(x["audit_state"]) in FINAL:return None
                if idem in s["task_by_idempotency"]:return s["task_by_idempotency"][idem]
            if not x:
                x={"candidate_id":candidate_id,"source_class":"UNKNOWN","evidence_refs":[],"terms_or_docs_hashes":[docs_hash],"docs_hash":docs_hash,"last_checked_at":None,"audit_state":AuditState.REVIEW_REQUIRED.value,"verdict_reason":"","freshness_state":"NEW","recheck_trigger":"INITIAL_REVIEW","version":0};s["cache"][candidate_id]=x
            else:
                x["docs_hash"]=docs_hash
                if docs_hash not in x["terms_or_docs_hashes"]:x["terms_or_docs_hashes"].append(docs_hash)
                x.update(audit_state=AuditState.CHANGED_REVIEW_REQUIRED.value,freshness_state="CHANGED",recheck_trigger="DOC_HASH_CHANGED",verdict_reason="");x["version"]+=1
            if idem in s["task_by_idempotency"]:return s["task_by_idempotency"][idem]
            tid="task-"+_digest(idem)[:16];s["tasks"][tid]={"task_id":tid,"idempotency_key":idem,"candidate_id":candidate_id,"input_hash":docs_hash,"attempt_count":0,"retry_budget":2,"checkpoint_ref":None,"lease_owner":None,"lease_expires_at":None,"heartbeat_at":None,"lease_epoch":0,"expected_cache_version":x["version"],"dead_letter_reason":None,"authorization_ref":authorization["authorization_decision_id"],"durable_receipt_ref":None};s["task_by_idempotency"][idem]=tid;return tid
        return self.store.transact(mutate)
    def checkpoint(self,*,task_id,checkpoint_ref,authorization,auth_runtime):
        validate_authorization(authorization,auth_runtime,operation="R1_TASK_CHECKPOINT",target=f"task:{task_id}",permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(s):
            if task_id not in s["tasks"]:raise StaleState("TASK_NOT_FOUND")
            s["tasks"][task_id]["checkpoint_ref"]=checkpoint_ref
        self.store.transact(mutate)
    def acquire_lease(self,*,task_id,worker_id,now_tick,lease_ticks,authorization,auth_runtime):
        if worker_id!=auth_runtime.actor_instance:raise AuthorizationDenied("WORKER_ACTOR_MISMATCH")
        validate_authorization(authorization,auth_runtime,operation="R1_TASK_ACQUIRE_LEASE",target=f"task:{task_id}",permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(s):
            t=s["tasks"].get(task_id)
            if not t:raise StaleState("TASK_NOT_FOUND")
            if t["dead_letter_reason"]:raise DeadLettered(t["dead_letter_reason"])
            if t["lease_owner"] is not None and now_tick<t["lease_expires_at"]:raise FencingConflict("LEASE_ALREADY_ACTIVE")
            t["lease_epoch"]+=1;t["lease_owner"]=worker_id;t["heartbeat_at"]=now_tick;t["lease_expires_at"]=now_tick+lease_ticks;return t["lease_epoch"]
        return self.store.transact(mutate)
    @staticmethod
    def _lease(t,w,e,n):
        if t["lease_owner"]!=w or t["lease_epoch"]!=e or n>=t["lease_expires_at"]:raise FencingConflict("STALE_EXPIRED_OR_NONOWNER_LEASE")
    def record_failure(self,*,task_id,reason,authorization,auth_runtime):
        validate_authorization(authorization,auth_runtime,operation="R1_TASK_RECORD_FAILURE",target=f"task:{task_id}",permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(s):
            t=s["tasks"].get(task_id)
            if not t:raise StaleState("TASK_NOT_FOUND")
            t["attempt_count"]+=1
            if t["attempt_count"]>t["retry_budget"]:t["dead_letter_reason"]=reason
        self.store.transact(mutate)
    def commit_review(self,*,current_main,task_id,worker_id,lease_epoch,now_tick,committed_state,verdict_reason,evidence_refs,authorization,auth_runtime):
        self._main(current_main)
        if worker_id!=auth_runtime.actor_instance:raise AuthorizationDenied("WORKER_ACTOR_MISMATCH")
        validate_authorization(authorization,auth_runtime,operation="R1_SOURCE_REVIEW_COMMIT",target=f"task:{task_id}",permission_class="P1_REVERSIBLE_INTERNAL_WRITE",data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY")
        try:state=AuditState(committed_state)
        except Exception as exc:raise SchemaError("COMMIT_ENUM") from exc
        if state not in FINAL or (state==AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT and not evidence_refs):raise SchemaError("COMMIT_STATE_OR_EVIDENCE")
        def mutate(s):
            t=s["tasks"].get(task_id)
            if not t:raise StaleState("TASK_NOT_FOUND")
            if t["dead_letter_reason"]:raise DeadLettered(t["dead_letter_reason"])
            self._lease(t,worker_id,lease_epoch,now_tick)
            payload={"task_id":task_id,"candidate_id":t["candidate_id"],"input_hash":t["input_hash"],"committed_state":state.value,"verdict_reason":verdict_reason,"evidence_refs":sorted(evidence_refs)};ph=_digest(payload);old=s["receipts_by_idempotency"].get(t["idempotency_key"])
            if old:
                if old["payload_hash"]!=ph:raise ReceiptConflict("IDEMPOTENCY_PAYLOAD_CONFLICT")
                return copy.deepcopy(old)
            x=s["cache"].get(t["candidate_id"])
            if not x or x["version"]!=t["expected_cache_version"] or x["docs_hash"]!=t["input_hash"]:raise StaleState("CACHE_CAS_OR_HASH_CONFLICT")
            x.update(audit_state=state.value,verdict_reason=verdict_reason,evidence_refs=list(evidence_refs),freshness_state="REVIEWED",recheck_trigger="DOC_HASH_CHANGE_OR_MANUAL_RECHECK",last_checked_at=auth_runtime.now.astimezone(timezone.utc).isoformat());x["version"]+=1
            r={"receipt_id":"receipt-"+ph[:20],"schema_version":SCHEMA_VERSION,"idempotency_key":t["idempotency_key"],"payload_hash":ph,"candidate_id":t["candidate_id"],"committed_state":state.value,"cache_version_after":x["version"],"authorization_decision_id":authorization["authorization_decision_id"],"operation_owner_gate_ref":authorization.get("owner_gate_ref"),"lease_epoch":lease_epoch,"worker_id":worker_id,"canonical_main":current_main};s["receipts_by_idempotency"][t["idempotency_key"]]=r;t["durable_receipt_ref"]=r["receipt_id"];return copy.deepcopy(r)
        return self.store.transact(mutate)
    def read_receipt(self,*,idempotency_key,authorization,auth_runtime):
        validate_authorization(authorization,auth_runtime,operation="R1_RECEIPT_READ",target=f"receipt-idempotency:{idempotency_key}",permission_class="P0_READ_PUBLIC_OR_CANONICAL",data_exposure_scope="INTERNAL_R1_RECEIPT_ONLY");return copy.deepcopy(self.store.read()["receipts_by_idempotency"].get(idempotency_key))
    @staticmethod
    def owner_exception_view(*,what_changed,what_ran_automatically,blocked_reason=None,next_safe_action="NONE"):return {"what_changed":what_changed,"what_ran_automatically":what_ran_automatically,"what_did_not_run":"BLOCKED_STEP_NOT_EXECUTED" if blocked_reason else "NONE","what_is_blocked_and_why":blocked_reason or "NONE","owner_action_required":bool(blocked_reason),"next_safe_action":next_safe_action,"approval_authority":"NONE_OBSERVABILITY_ONLY"}
