"""Pinned R1 cache/task/receipt state schema and durable local store."""
import copy,json,os,tempfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Callable,Optional,TypeVar
import fcntl

SCHEMA_VERSION="MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SCHEMA_v3"
STATE_FIELDS={"schema_version","generation","cache","tasks","task_by_idempotency","receipts_by_idempotency"}
CACHE_FIELDS={"candidate_id","source_class","evidence_refs","terms_or_docs_hashes","docs_hash","last_checked_at","audit_state","verdict_reason","freshness_state","recheck_trigger","version"}
TASK_FIELDS={"task_id","idempotency_key","candidate_id","input_hash","attempt_count","retry_budget","checkpoint_ref","lease_owner","lease_expires_at","heartbeat_at","lease_epoch","expected_cache_version","dead_letter_reason","authorization_ref","durable_receipt_ref"}
RECEIPT_FIELDS={"receipt_id","schema_version","idempotency_key","payload_hash","candidate_id","committed_state","cache_version_after","authorization_decision_id","operation_owner_gate_ref","lease_epoch","worker_id","canonical_main"}
T=TypeVar("T")
class SchemaError(RuntimeError):pass
class StaleState(RuntimeError):pass
class AuditState(str,Enum):
    UNKNOWN="UNKNOWN";REVIEW_REQUIRED="REVIEW_REQUIRED";REVIEWED_NO_ADMISSION="REVIEWED_NO_ADMISSION";CHANGED_REVIEW_REQUIRED="CHANGED_REVIEW_REQUIRED";EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT="EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT"
FINAL={AuditState.REVIEWED_NO_ADMISSION,AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT}
def _strings(v):return isinstance(v,list) and all(isinstance(x,str) for x in v)
def empty_state():return {"schema_version":SCHEMA_VERSION,"generation":0,"cache":{},"tasks":{},"task_by_idempotency":{},"receipts_by_idempotency":{}}
def validate_state(s:dict)->None:
    if not isinstance(s,dict) or set(s)!=STATE_FIELDS or s.get("schema_version")!=SCHEMA_VERSION:raise SchemaError("STATE_SCHEMA")
    if not isinstance(s["generation"],int) or isinstance(s["generation"],bool) or s["generation"]<0:raise SchemaError("STATE_GENERATION")
    for section in ("cache","tasks","task_by_idempotency","receipts_by_idempotency"):
        if not isinstance(s[section],dict):raise SchemaError("STATE_SECTION")
    for cid,x in s["cache"].items():
        if not isinstance(x,dict) or set(x)!=CACHE_FIELDS or x["candidate_id"]!=cid:raise SchemaError("CACHE_SCHEMA")
        if not all(isinstance(x[f],str) for f in ("source_class","docs_hash","verdict_reason","freshness_state","recheck_trigger")):raise SchemaError("CACHE_TYPES")
        if not _strings(x["evidence_refs"]) or not _strings(x["terms_or_docs_hashes"]) or x["docs_hash"] not in x["terms_or_docs_hashes"]:raise SchemaError("CACHE_HASH_EVIDENCE")
        if x["last_checked_at"] is not None and not isinstance(x["last_checked_at"],str):raise SchemaError("CACHE_TIME")
        if not isinstance(x["version"],int) or isinstance(x["version"],bool) or x["version"]<0:raise SchemaError("CACHE_VERSION")
        try:AuditState(x["audit_state"])
        except Exception as exc:raise SchemaError("CACHE_ENUM") from exc
    for tid,x in s["tasks"].items():
        if not isinstance(x,dict) or set(x)!=TASK_FIELDS or x["task_id"]!=tid:raise SchemaError("TASK_SCHEMA")
        for f in ("task_id","idempotency_key","candidate_id","input_hash","authorization_ref"):
            if not isinstance(x[f],str) or not x[f]:raise SchemaError("TASK_STRING")
        for f in ("attempt_count","retry_budget","lease_epoch","expected_cache_version"):
            if not isinstance(x[f],int) or isinstance(x[f],bool) or x[f]<0:raise SchemaError("TASK_INT")
        for f in ("checkpoint_ref","lease_owner","dead_letter_reason","durable_receipt_ref"):
            if x[f] is not None and not isinstance(x[f],str):raise SchemaError("TASK_OPTIONAL_STRING")
        for f in ("lease_expires_at","heartbeat_at"):
            if x[f] is not None and (not isinstance(x[f],int) or isinstance(x[f],bool)):raise SchemaError("TASK_OPTIONAL_INT")
        if x["candidate_id"] not in s["cache"]:raise SchemaError("TASK_CACHE_REF")
        if s["task_by_idempotency"].get(x["idempotency_key"])!=tid:raise SchemaError("TASK_INDEX")
    for idem,tid in s["task_by_idempotency"].items():
        if tid not in s["tasks"] or s["tasks"][tid]["idempotency_key"]!=idem:raise SchemaError("IDEMPOTENCY_INDEX")
    for idem,x in s["receipts_by_idempotency"].items():
        if not isinstance(x,dict) or set(x)!=RECEIPT_FIELDS or x["schema_version"]!=SCHEMA_VERSION or x["idempotency_key"]!=idem:raise SchemaError("RECEIPT_SCHEMA")
        if not isinstance(x["payload_hash"],str) or len(x["payload_hash"])!=64 or x["receipt_id"]!="receipt-"+x["payload_hash"][:20]:raise SchemaError("RECEIPT_IDENTITY")
        try:state=AuditState(x["committed_state"])
        except Exception as exc:raise SchemaError("RECEIPT_ENUM") from exc
        if state not in FINAL:raise SchemaError("RECEIPT_FINAL_STATE")
        tid=s["task_by_idempotency"].get(idem)
        if not tid or s["tasks"][tid]["durable_receipt_ref"]!=x["receipt_id"] or s["tasks"][tid]["candidate_id"]!=x["candidate_id"]:raise SchemaError("RECEIPT_TASK_REF")
        if not isinstance(x["cache_version_after"],int) or not isinstance(x["lease_epoch"],int):raise SchemaError("RECEIPT_INT")
class PersistentStore:
    def __init__(self,root:Path):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.state_path=self.root/"r1_state.json";self.lock_path=self.root/"r1_state.lock"
        with self.locked():
            if not self.state_path.exists():self._write(empty_state())
            else:self._read()
    @contextmanager
    def locked(self):
        self.lock_path.touch(exist_ok=True)
        with open(self.lock_path,"r+") as fh:
            fcntl.flock(fh.fileno(),fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
    def _read(self):
        try:s=json.loads(self.state_path.read_text())
        except Exception as exc:raise SchemaError("STATE_READ") from exc
        validate_state(s);return s
    def _write(self,s):
        validate_state(s);fd,name=tempfile.mkstemp(dir=self.root,prefix="r1-",suffix=".tmp")
        try:
            with os.fdopen(fd,"w") as fh:fh.write(json.dumps(s,sort_keys=True,indent=2)+"\n");fh.flush();os.fsync(fh.fileno())
            os.replace(name,self.state_path)
        finally:
            if os.path.exists(name):os.unlink(name)
    def read(self):
        with self.locked():return copy.deepcopy(self._read())
    def transact(self,fn:Callable[[dict],T],expected_generation:Optional[int]=None)->T:
        with self.locked():
            s=self._read()
            if expected_generation is not None and s["generation"]!=expected_generation:raise StaleState("CAS_GENERATION_CONFLICT")
            before=copy.deepcopy(s);out=fn(s);validate_state(s)
            if s!=before:s["generation"]=before["generation"]+1;self._write(s)
            return out
