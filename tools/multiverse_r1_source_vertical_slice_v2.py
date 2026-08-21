#!/usr/bin/env python3
"""Multiverse R1 Source vertical-slice implementation candidate v2.

Bounded internal library only. No scheduler, watcher, network collection, source
admission, provider contact, protected-data access, spend, economics, or model
promotion. Reliability target: retry-safe convergence, not exactly-once.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, TypeVar

try:
    import fcntl
except ImportError as exc:
    raise RuntimeError("R1_REQUIRES_FCNTL_FILE_LOCKING") from exc

SCHEMA_VERSION = "MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SCHEMA_v2"
CANONICAL_DESIGN_MERGE = "ddf0b808aa8e4014dad59dd350c225970f916b89"

PERMISSION_ORDER = {
    "P0_READ_PUBLIC_OR_CANONICAL": 0,
    "P1_REVERSIBLE_INTERNAL_WRITE": 1,
    "P2_EXTERNAL_OR_SHARED_WRITE": 2,
    "P3_MATERIAL_OPERATION": 3,
    "P4_OWNER_GATE_REQUIRED": 4,
    "P5_PROHIBITED": 5,
}
REQUIRED_AUTH_FIELDS = {
    "authorization_decision_id", "policy_generation", "policy_digest",
    "actor_role", "actor_instance", "operation", "target",
    "permission_class_requested", "permission_ceiling", "scope",
    "data_exposure_scope", "issued_at", "expires_at", "grant_ref",
    "owner_gate_ref", "revocation_generation_seen", "safe_mode_generation_seen",
    "decision", "reason_codes", "evidence_refs",
}
T = TypeVar("T")

class R1Error(RuntimeError): pass
class AuthorizationDenied(R1Error): pass
class StaleState(R1Error): pass
class FencingConflict(R1Error): pass
class ReceiptConflict(R1Error): pass
class DeadLettered(R1Error): pass
class SchemaError(R1Error): pass

class AuditState(str, Enum):
    UNKNOWN = "UNKNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED_NO_ADMISSION = "REVIEWED_NO_ADMISSION"
    CHANGED_REVIEW_REQUIRED = "CHANGED_REVIEW_REQUIRED"
    EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT = "EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT"

@dataclass(frozen=True)
class AuthorizationRuntime:
    policy_generation: str
    policy_digest: str
    revocation_generation: int
    safe_mode_generation: int
    now: datetime
    expected_owner_gate_ref: Optional[str] = None

def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AuthorizationDenied("AUTH_TIME_MALFORMED") from exc
    if parsed.tzinfo is None:
        raise AuthorizationDenied("AUTH_TIME_MUST_BE_OFFSET_AWARE")
    return parsed.astimezone(timezone.utc)

def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()

def validate_authorization(
    decision: Dict[str, Any], runtime: AuthorizationRuntime, *, operation: str,
    target: str, permission_class: str, data_exposure_scope: str,
    owner_gate_required: bool = False,
) -> None:
    """Consume an already-issued full decision; never mint/elevate a grant."""
    if not isinstance(decision, dict):
        raise AuthorizationDenied("AUTH_DECISION_NOT_OBJECT")
    missing = sorted(REQUIRED_AUTH_FIELDS - set(decision))
    if missing:
        raise AuthorizationDenied("AUTH_REQUIRED_FIELDS_MISSING:" + ",".join(missing))
    if decision["decision"] != "ALLOW":
        raise AuthorizationDenied("AUTH_DECISION_NOT_ALLOW")
    if decision["policy_generation"] != runtime.policy_generation:
        raise AuthorizationDenied("AUTH_POLICY_GENERATION_STALE")
    if decision["policy_digest"] != runtime.policy_digest:
        raise AuthorizationDenied("AUTH_POLICY_DIGEST_STALE")
    if decision["revocation_generation_seen"] != runtime.revocation_generation:
        raise AuthorizationDenied("AUTH_REVOCATION_GENERATION_STALE")
    if decision["safe_mode_generation_seen"] != runtime.safe_mode_generation:
        raise AuthorizationDenied("AUTH_SAFE_MODE_GENERATION_STALE")
    now = runtime.now.astimezone(timezone.utc)
    if _parse_time(decision["issued_at"]) > now:
        raise AuthorizationDenied("AUTH_ISSUED_IN_FUTURE")
    if _parse_time(decision["expires_at"]) <= now:
        raise AuthorizationDenied("AUTH_EXPIRED")
    if decision["operation"] != operation:
        raise AuthorizationDenied("AUTH_OPERATION_MISMATCH")
    if decision["target"] != target:
        raise AuthorizationDenied("AUTH_TARGET_MISMATCH")
    if decision["data_exposure_scope"] != data_exposure_scope:
        raise AuthorizationDenied("AUTH_DATA_EXPOSURE_SCOPE_MISMATCH")
    requested, ceiling = decision["permission_class_requested"], decision["permission_ceiling"]
    if requested not in PERMISSION_ORDER or ceiling not in PERMISSION_ORDER:
        raise AuthorizationDenied("AUTH_PERMISSION_CLASS_UNKNOWN")
    if requested != permission_class:
        raise AuthorizationDenied("AUTH_PERMISSION_CLASS_REQUEST_MISMATCH")
    if PERMISSION_ORDER[permission_class] > PERMISSION_ORDER[ceiling]:
        raise AuthorizationDenied("AUTH_PERMISSION_CEILING_EXCEEDED")
    scope = decision["scope"]
    if not isinstance(scope, dict) or scope.get("operation") != operation or scope.get("target") != target:
        raise AuthorizationDenied("AUTH_SCOPE_MISMATCH")
    if permission_class != "P0_READ_PUBLIC_OR_CANONICAL" and not decision["grant_ref"]:
        raise AuthorizationDenied("AUTH_GRANT_REQUIRED")
    if owner_gate_required:
        if not runtime.expected_owner_gate_ref:
            raise AuthorizationDenied("AUTH_RUNTIME_OWNER_GATE_REF_UNKNOWN")
        if decision["owner_gate_ref"] != runtime.expected_owner_gate_ref:
            raise AuthorizationDenied("AUTH_OWNER_GATE_MISSING_OR_MISMATCHED")

def _empty_state() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "generation": 0, "cache": {}, "tasks": {},
            "task_by_idempotency": {}, "receipts_by_idempotency": {}}

def _validate_state(state: Dict[str, Any]) -> None:
    if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError("UNKNOWN_OR_STALE_SCHEMA_VERSION")
    if not isinstance(state.get("generation"), int) or state["generation"] < 0:
        raise SchemaError("INVALID_STATE_GENERATION")
    for key in ("cache", "tasks", "task_by_idempotency", "receipts_by_idempotency"):
        if not isinstance(state.get(key), dict):
            raise SchemaError("INVALID_STATE_SECTION:" + key)
    for rec in state["cache"].values():
        try: AuditState(rec["audit_state"])
        except (KeyError, ValueError, TypeError) as exc: raise SchemaError("UNKNOWN_CACHE_AUDIT_STATE") from exc

class PersistentStore:
    """Locked, durable single-file state with generation CAS and atomic replace."""
    def __init__(self, root: Path):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "r1_state.json"; self.lock_path = self.root / "r1_state.lock"
        with self.locked():
            if not self.state_path.exists(): self._write_raw(_empty_state())
            else: self._read_raw()

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.lock_path.touch(exist_ok=True)
        with open(self.lock_path, "r+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def _read_raw(self) -> Dict[str, Any]:
        try: state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise SchemaError("STATE_READ_FAILED") from exc
        _validate_state(state); return state

    def _write_raw(self, state: Dict[str, Any]) -> None:
        _validate_state(state)
        fd, name = tempfile.mkstemp(prefix="r1-state-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                fh.flush(); os.fsync(fh.fileno())
            os.replace(name, self.state_path)
        finally:
            if os.path.exists(name): os.unlink(name)

    def read(self) -> Dict[str, Any]:
        with self.locked(): return copy.deepcopy(self._read_raw())

    def transact(self, fn: Callable[[Dict[str, Any]], T], expected_generation: Optional[int] = None) -> T:
        with self.locked():
            state = self._read_raw()
            if expected_generation is not None and state["generation"] != expected_generation:
                raise StaleState(f"CAS_GENERATION_CONFLICT:{expected_generation}:CURRENT:{state['generation']}")
            before = state["generation"]
            result = fn(state)
            _validate_state(state)
            state["generation"] = before + 1
            self._write_raw(state)
            return result

class R1Engine:
    def __init__(self, store: PersistentStore, canonical_main: str):
        self.store, self.canonical_main = store, canonical_main
    def _require_current_main(self, current_main: str) -> None:
        if current_main != self.canonical_main: raise StaleState("STALE_CANONICAL_MAIN:" + current_main)
    @staticmethod
    def _idem(candidate_id: str, docs_hash: str) -> str: return f"source-review:{candidate_id}:{docs_hash}"

    def inspect_candidate(self, *, current_main: str, candidate_id: str, docs_hash: str,
                          authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> Optional[str]:
        self._require_current_main(current_main)
        validate_authorization(authorization, auth_runtime, operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            target=f"source-candidate:{candidate_id}", permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY")
        idem = self._idem(candidate_id, docs_hash)
        def mutate(state: Dict[str, Any]) -> Optional[str]:
            existing = state["cache"].get(candidate_id)
            if existing and existing.get("docs_hash") == docs_hash:
                audit_state = AuditState(existing["audit_state"])
                if audit_state in {AuditState.REVIEWED_NO_ADMISSION, AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT}:
                    return None
                task_id = state["task_by_idempotency"].get(idem)
                if task_id: return task_id
            if existing is None:
                existing = {"candidate_id": candidate_id, "source_class": "UNKNOWN", "evidence_refs": [],
                    "terms_or_docs_hashes": [docs_hash], "docs_hash": docs_hash, "last_checked_at": None,
                    "audit_state": AuditState.REVIEW_REQUIRED.value, "verdict_reason": "",
                    "freshness_state": "NEW", "recheck_trigger": "INITIAL_REVIEW", "version": 0}
                state["cache"][candidate_id] = existing
            else:
                existing["docs_hash"] = docs_hash
                if docs_hash not in existing.setdefault("terms_or_docs_hashes", []): existing["terms_or_docs_hashes"].append(docs_hash)
                existing.update(audit_state=AuditState.CHANGED_REVIEW_REQUIRED.value, freshness_state="CHANGED",
                                recheck_trigger="DOC_HASH_CHANGED", verdict_reason="")
                existing["version"] += 1
            task_id = state["task_by_idempotency"].get(idem)
            if task_id: return task_id
            task_id = "task-" + _digest(idem)[:16]
            state["tasks"][task_id] = {"task_id": task_id, "idempotency_key": idem, "candidate_id": candidate_id,
                "input_hash": docs_hash, "attempt_count": 0, "retry_budget": 2, "checkpoint_ref": None,
                "lease_owner": None, "lease_expires_at": None, "heartbeat_at": None, "lease_epoch": 0,
                "expected_cache_version": existing["version"], "dead_letter_reason": None,
                "authorization_ref": authorization["authorization_decision_id"], "durable_receipt_ref": None}
            state["task_by_idempotency"][idem] = task_id
            return task_id
        return self.store.transact(mutate)

    def checkpoint(self, *, task_id: str, checkpoint_ref: str, authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> None:
        validate_authorization(authorization, auth_runtime, operation="R1_TASK_CHECKPOINT", target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE", data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(state):
            if task_id not in state["tasks"]: raise StaleState("TASK_NOT_FOUND")
            state["tasks"][task_id]["checkpoint_ref"] = checkpoint_ref
        self.store.transact(mutate)

    def acquire_lease(self, *, task_id: str, worker_id: str, now_tick: int, lease_ticks: int,
                      authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> int:
        if lease_ticks <= 0: raise ValueError("lease_ticks must be positive")
        validate_authorization(authorization, auth_runtime, operation="R1_TASK_ACQUIRE_LEASE", target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE", data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(state):
            task = state["tasks"].get(task_id)
            if not task: raise StaleState("TASK_NOT_FOUND")
            if task["dead_letter_reason"]: raise DeadLettered(task["dead_letter_reason"])
            task["lease_epoch"] += 1; task["lease_owner"] = worker_id
            task["heartbeat_at"] = now_tick; task["lease_expires_at"] = now_tick + lease_ticks
            return task["lease_epoch"]
        return self.store.transact(mutate)

    @staticmethod
    def _assert_current_lease(task: Dict[str, Any], worker_id: str, lease_epoch: int, now_tick: int) -> None:
        if task.get("lease_owner") != worker_id or task.get("lease_epoch") != lease_epoch:
            raise FencingConflict("STALE_OR_NONOWNER_LEASE_EPOCH")
        if not isinstance(task.get("lease_expires_at"), int) or now_tick >= task["lease_expires_at"]:
            raise FencingConflict("LEASE_EXPIRED")

    def record_failure(self, *, task_id: str, reason: str, authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> None:
        validate_authorization(authorization, auth_runtime, operation="R1_TASK_RECORD_FAILURE", target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE", data_exposure_scope="INTERNAL_R1_STATE_ONLY")
        def mutate(state):
            task = state["tasks"].get(task_id)
            if not task: raise StaleState("TASK_NOT_FOUND")
            task["attempt_count"] += 1
            if task["attempt_count"] > task["retry_budget"]: task["dead_letter_reason"] = reason
        self.store.transact(mutate)

    def commit_review(self, *, current_main: str, task_id: str, worker_id: str, lease_epoch: int, now_tick: int,
                      committed_state: str, verdict_reason: str, evidence_refs: list[str],
                      authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> Dict[str, Any]:
        """Commit only source-audit metadata. This is NOT source admission and does not reuse the implementation Owner Gate."""
        self._require_current_main(current_main)
        validate_authorization(authorization, auth_runtime, operation="R1_SOURCE_REVIEW_COMMIT", target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE", data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY",
            owner_gate_required=False)
        try: target_state = AuditState(committed_state)
        except ValueError as exc: raise SchemaError("UNKNOWN_CACHE_AUDIT_STATE") from exc
        if target_state not in {AuditState.REVIEWED_NO_ADMISSION, AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT}:
            raise SchemaError("R1_COMMIT_STATE_NOT_FINAL_REVIEW_STATE")
        if target_state is AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT and not evidence_refs:
            raise SchemaError("EXPLICIT_INELIGIBILITY_REQUIRES_EVIDENCE")
        def mutate(state):
            task = state["tasks"].get(task_id)
            if not task: raise StaleState("TASK_NOT_FOUND")
            if task["dead_letter_reason"]: raise DeadLettered(task["dead_letter_reason"])
            self._assert_current_lease(task, worker_id, lease_epoch, now_tick)
            payload = {"task_id": task_id, "candidate_id": task["candidate_id"], "input_hash": task["input_hash"],
                "committed_state": target_state.value, "verdict_reason": verdict_reason, "evidence_refs": sorted(evidence_refs)}
            payload_hash = _digest(payload)
            existing_receipt = state["receipts_by_idempotency"].get(task["idempotency_key"])
            if existing_receipt:
                if existing_receipt["payload_hash"] != payload_hash: raise ReceiptConflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD")
                return copy.deepcopy(existing_receipt)
            record = state["cache"].get(task["candidate_id"])
            if not record: raise StaleState("CACHE_RECORD_NOT_FOUND")
            if record["version"] != task["expected_cache_version"]: raise StaleState("CACHE_VERSION_CONFLICT")
            if record["docs_hash"] != task["input_hash"]: raise StaleState("CACHE_DOC_HASH_DRIFT")
            record.update(audit_state=target_state.value, verdict_reason=verdict_reason, evidence_refs=list(evidence_refs),
                          freshness_state="REVIEWED", recheck_trigger="DOC_HASH_CHANGE_OR_MANUAL_RECHECK",
                          last_checked_at=auth_runtime.now.astimezone(timezone.utc).isoformat())
            record["version"] += 1
            receipt = {"receipt_id": "receipt-" + payload_hash[:20], "schema_version": SCHEMA_VERSION,
                "idempotency_key": task["idempotency_key"], "payload_hash": payload_hash, "candidate_id": task["candidate_id"],
                "committed_state": target_state.value, "cache_version_after": record["version"],
                "authorization_decision_id": authorization["authorization_decision_id"],
                "operation_owner_gate_ref": authorization.get("owner_gate_ref"), "lease_epoch": lease_epoch,
                "worker_id": worker_id, "canonical_main": current_main}
            state["receipts_by_idempotency"][task["idempotency_key"]] = receipt
            task["durable_receipt_ref"] = receipt["receipt_id"]
            return copy.deepcopy(receipt)
        return self.store.transact(mutate)

    def read_receipt(self, *, idempotency_key: str, authorization: Dict[str, Any], auth_runtime: AuthorizationRuntime) -> Optional[Dict[str, Any]]:
        validate_authorization(authorization, auth_runtime, operation="R1_RECEIPT_READ", target=f"receipt-idempotency:{idempotency_key}",
            permission_class="P0_READ_PUBLIC_OR_CANONICAL", data_exposure_scope="INTERNAL_R1_RECEIPT_ONLY")
        return copy.deepcopy(self.store.read()["receipts_by_idempotency"].get(idempotency_key))

    @staticmethod
    def owner_exception_view(*, what_changed: str, what_ran_automatically: str, blocked_reason: Optional[str] = None,
                             next_safe_action: str = "NONE") -> Dict[str, Any]:
        return {"what_changed": what_changed, "what_ran_automatically": what_ran_automatically,
            "what_did_not_run": "BLOCKED_STEP_NOT_EXECUTED" if blocked_reason else "NONE",
            "what_is_blocked_and_why": blocked_reason or "NONE", "owner_action_required": bool(blocked_reason),
            "next_safe_action": next_safe_action, "approval_authority": "NONE_OBSERVABILITY_ONLY"}

def _auth(*, operation: str, target: str, permission: str, data_scope: str,
          owner_gate_ref: Optional[str] = None, decision: str = "ALLOW") -> Dict[str, Any]:
    return {"authorization_decision_id": "auth-" + _digest([operation,target,permission,data_scope,owner_gate_ref])[:12],
        "policy_generation": "g1", "policy_digest": "d1", "actor_role": "EXECUTION",
        "actor_instance": "fake-worker-harness", "operation": operation, "target": target,
        "permission_class_requested": permission, "permission_ceiling": "P4_OWNER_GATE_REQUIRED",
        "scope": {"operation": operation, "target": target}, "data_exposure_scope": data_scope,
        "issued_at": "2026-08-21T03:00:00+00:00", "expires_at": "2026-08-21T06:00:00+00:00",
        "grant_ref": None if permission == "P0_READ_PUBLIC_OR_CANONICAL" else "grant-r1-test",
        "owner_gate_ref": owner_gate_ref, "revocation_generation_seen": 3, "safe_mode_generation_seen": 5,
        "decision": decision, "reason_codes": ["FAKE_HARNESS"], "evidence_refs": []}

def _runtime(expected_owner_gate_ref: Optional[str] = None) -> AuthorizationRuntime:
    return AuthorizationRuntime("g1", "d1", 3, 5, datetime.fromisoformat("2026-08-21T04:00:00+00:00"), expected_owner_gate_ref)

def run_selftest() -> int:
    MAIN = CANONICAL_DESIGN_MERGE
    with tempfile.TemporaryDirectory(prefix="multiverse-r1-") as td:
        store = PersistentStore(Path(td)); engine = R1Engine(store, MAIN)
        def auth(op, target, perm, scope, gate=None, decision="ALLOW"):
            return _auth(operation=op, target=target, permission=perm, data_scope=scope, owner_gate_ref=gate, decision=decision)
        inspect = auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE", "source-candidate:s1", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY")
        t1 = engine.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h1", authorization=inspect, auth_runtime=_runtime())
        t2 = engine.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h1", authorization=inspect, auth_runtime=_runtime())
        assert t1 == t2 and t1
        cp = auth("R1_TASK_CHECKPOINT", f"task:{t1}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY")
        engine.checkpoint(task_id=t1, checkpoint_ref="checkpoint://fake/1", authorization=cp, auth_runtime=_runtime())
        lease = auth("R1_TASK_ACQUIRE_LEASE", f"task:{t1}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY")
        ea = engine.acquire_lease(task_id=t1, worker_id="a", now_tick=10, lease_ticks=10, authorization=lease, auth_runtime=_runtime())
        eb = engine.acquire_lease(task_id=t1, worker_id="b", now_tick=21, lease_ticks=10, authorization=lease, auth_runtime=_runtime())
        assert eb > ea and store.read()["tasks"][t1]["checkpoint_ref"] == "checkpoint://fake/1"
        commit = auth("R1_SOURCE_REVIEW_COMMIT", f"task:{t1}", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY")
        try:
            engine.commit_review(current_main=MAIN, task_id=t1, worker_id="a", lease_epoch=ea, now_tick=22,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="FAKE", evidence_refs=["e1"],
                authorization=commit, auth_runtime=_runtime())
            raise AssertionError("old worker commit must fail")
        except FencingConflict: pass
        r1 = engine.commit_review(current_main=MAIN, task_id=t1, worker_id="b", lease_epoch=eb, now_tick=22,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="FAKE", evidence_refs=["e1"],
            authorization=commit, auth_runtime=_runtime())
        r2 = engine.commit_review(current_main=MAIN, task_id=t1, worker_id="b", lease_epoch=eb, now_tick=22,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="FAKE", evidence_refs=["e1"],
            authorization=commit, auth_runtime=_runtime())
        assert r1 == r2 and r1["operation_owner_gate_ref"] is None
        assert engine.inspect_candidate(current_main=MAIN, candidate_id="s1", docs_hash="h1", authorization=inspect, auth_runtime=_runtime()) is None
        ec = engine.acquire_lease(task_id=t1, worker_id="c", now_tick=23, lease_ticks=10, authorization=lease, auth_runtime=_runtime())
        assert ec > eb
        try:
            engine.commit_review(current_main=MAIN, task_id=t1, worker_id="b", lease_epoch=eb, now_tick=24,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="FAKE", evidence_refs=["e1"],
                authorization=commit, auth_runtime=_runtime())
            raise AssertionError("stale worker must not receive success")
        except FencingConflict: pass
        idem = engine._idem("s1", "h1")
        read_auth = auth("R1_RECEIPT_READ", f"receipt-idempotency:{idem}", "P0_READ_PUBLIC_OR_CANONICAL", "INTERNAL_R1_RECEIPT_ONLY")
        assert engine.read_receipt(idempotency_key=idem, authorization=read_auth, auth_runtime=_runtime()) == r1
        try:
            engine.inspect_candidate(current_main="stale", candidate_id="s2", docs_hash="h2",
                authorization=auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE", "source-candidate:s2", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY"), auth_runtime=_runtime())
            raise AssertionError("stale main must fail")
        except StaleState: pass
        try:
            engine.inspect_candidate(current_main=MAIN, candidate_id="s2", docs_hash="h2",
                authorization=auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE", "source-candidate:s2", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY", decision="DENY"), auth_runtime=_runtime())
            raise AssertionError("DENY must fail")
        except AuthorizationDenied: pass
        p4 = auth("FAKE_P4_OPERATION", "fake-target", "P4_OWNER_GATE_REQUIRED", "INTERNAL_TEST_ONLY", gate="wrong-gate")
        try:
            validate_authorization(p4, _runtime("operation-specific-gate"), operation="FAKE_P4_OPERATION", target="fake-target",
                permission_class="P4_OWNER_GATE_REQUIRED", data_exposure_scope="INTERNAL_TEST_ONLY", owner_gate_required=True)
            raise AssertionError("P4 gate mismatch must fail")
        except AuthorizationDenied: pass
        try:
            validate_authorization(inspect, _runtime(), operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE", target="source-candidate:s1",
                permission_class="P1_REVERSIBLE_INTERNAL_WRITE", data_exposure_scope="SEALED_PROTECTED_DATA")
            raise AssertionError("protected scope mismatch must fail")
        except AuthorizationDenied: pass
        ins3 = auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE", "source-candidate:s3", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY")
        t3 = engine.inspect_candidate(current_main=MAIN, candidate_id="s3", docs_hash="h3", authorization=ins3, auth_runtime=_runtime())
        fail = auth("R1_TASK_RECORD_FAILURE", f"task:{t3}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY")
        for _ in range(3): engine.record_failure(task_id=t3, reason="timeout", authorization=fail, auth_runtime=_runtime())
        try:
            engine.acquire_lease(task_id=t3, worker_id="z", now_tick=1, lease_ticks=5,
                authorization=auth("R1_TASK_ACQUIRE_LEASE", f"task:{t3}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY"), auth_runtime=_runtime())
            raise AssertionError("dead-lettered task must not reacquire")
        except DeadLettered: pass
        ins4 = auth("R1_SOURCE_CACHE_INSPECT_OR_STAGE", "source-candidate:s4", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY")
        t4 = engine.inspect_candidate(current_main=MAIN, candidate_id="s4", docs_hash="h4", authorization=ins4, auth_runtime=_runtime())
        l4 = auth("R1_TASK_ACQUIRE_LEASE", f"task:{t4}", "P1_REVERSIBLE_INTERNAL_WRITE", "INTERNAL_R1_STATE_ONLY")
        e4 = engine.acquire_lease(task_id=t4, worker_id="w4", now_tick=1, lease_ticks=20, authorization=l4, auth_runtime=_runtime())
        c4 = auth("R1_SOURCE_REVIEW_COMMIT", f"task:{t4}", "P1_REVERSIBLE_INTERNAL_WRITE", "PUBLIC_TERMS_METADATA_ONLY")
        engine.commit_review(current_main=MAIN, task_id=t4, worker_id="w4", lease_epoch=e4, now_tick=2,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="A", evidence_refs=["e"], authorization=c4, auth_runtime=_runtime())
        try:
            engine.commit_review(current_main=MAIN, task_id=t4, worker_id="w4", lease_epoch=e4, now_tick=2,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value, verdict_reason="B", evidence_refs=["e"], authorization=c4, auth_runtime=_runtime())
            raise AssertionError("conflicting payload must fail")
        except ReceiptConflict: pass
        snap = store.read(); g = snap["generation"]
        store.transact(lambda s: s["cache"]["s4"].update(freshness_state="TOUCHED"), expected_generation=g)
        try: store.transact(lambda s: None, expected_generation=g); raise AssertionError("stale CAS must fail")
        except StaleState: pass
        try: store.transact(lambda s: s["cache"]["s4"].update(audit_state="MADE_UP_STATE")); raise AssertionError
        except SchemaError: pass
        view = engine.owner_exception_view(what_changed="R1_SELFTEST", what_ran_automatically="FAKE_INTERNAL_TESTS_ONLY",
            blocked_reason="RUNTIME_ACTIVATION_NOT_AUTHORIZED", next_safe_action="IMPLEMENTATION_REVIEW")
        assert view["approval_authority"] == "NONE_OBSERVABILITY_ONLY" and view["owner_action_required"] is True
    print("MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SELFTEST_PASS")
    print("IMPLEMENTATION_OWNER_GATE_USED_AS_RUNTIME_GRANT=false")
    print("SOURCE_AUDIT_COMMIT_PERMISSION=P1_REVERSIBLE_INTERNAL_WRITE")
    print("FENCING_BEFORE_COMMIT_SUCCESS=true")
    print("AUTHORIZATION_CONTRACT_PRECONDITIONS_ENFORCED=true")
    print("DURABLE_RECEIPT_SEPARATE_READ=true")
    print("EXACTLY_ONCE_CLAIM=false")
    print("NETWORK_ACCESS_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--selftest", action="store_true"); args = p.parse_args()
    if args.selftest: return run_selftest()
    print("R1_LIBRARY_ONLY_NO_AUTORUN_RUNTIME_ACTIVATION"); return 0

if __name__ == "__main__": raise SystemExit(main())
