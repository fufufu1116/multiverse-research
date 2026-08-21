#!/usr/bin/env python3
"""Multiverse R1 Source vertical-slice implementation candidate v1.

Bounded internal implementation only. This module does not schedule itself, perform
network access, admit sources, collect real/live PRE, contact providers, spend money,
open protected data, access RESULT/PAYOUT/Holdout, or promote models.

Design target:
Source Audit Cache -> Reliable Task Execution -> Owner Exception View.

Reliability target is retry-safe convergence, NOT exactly-once execution.
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
from typing import Any, Dict, Iterator, Optional

try:
    import fcntl
except ImportError as exc:  # fail closed on unsupported runtime
    raise RuntimeError("R1_REQUIRES_FCNTL_FILE_LOCKING") from exc


SCHEMA_VERSION = "MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SCHEMA_v1"
OWNER_GATE_COMMENT_ID = 5365031899
AUDITOR_COMMENT_ID = 5364979656
CANONICAL_ASSESSMENT_MERGE = "ddf0b808aa8e4014dad59dd350c225970f916b89"

PERMISSION_ORDER = {
    "P0_READ_PUBLIC_OR_CANONICAL": 0,
    "P1_REVERSIBLE_INTERNAL_WRITE": 1,
    "P2_EXTERNAL_OR_SHARED_WRITE": 2,
    "P3_MATERIAL_OPERATION": 3,
    "P4_OWNER_GATE_REQUIRED": 4,
    "P5_PROHIBITED": 5,
}

REQUIRED_AUTH_FIELDS = {
    "authorization_decision_id",
    "policy_generation",
    "policy_digest",
    "actor_role",
    "actor_instance",
    "operation",
    "target",
    "permission_class_requested",
    "permission_ceiling",
    "scope",
    "data_exposure_scope",
    "issued_at",
    "expires_at",
    "grant_ref",
    "owner_gate_ref",
    "revocation_generation_seen",
    "safe_mode_generation_seen",
    "decision",
    "reason_codes",
    "evidence_refs",
}


class R1Error(RuntimeError):
    pass


class AuthorizationDenied(R1Error):
    pass


class StaleState(R1Error):
    pass


class FencingConflict(R1Error):
    pass


class ReceiptConflict(R1Error):
    pass


class DeadLettered(R1Error):
    pass


class SchemaError(R1Error):
    pass


class AuditState(str, Enum):
    UNKNOWN = "UNKNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED_NO_ADMISSION = "REVIEWED_NO_ADMISSION"
    CHANGED_REVIEW_REQUIRED = "CHANGED_REVIEW_REQUIRED"
    EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT = (
        "EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT"
    )


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
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_authorization(
    decision: Dict[str, Any],
    runtime: AuthorizationRuntime,
    *,
    operation: str,
    target: str,
    permission_class: str,
    data_exposure_scope: str,
    owner_gate_required: bool = False,
) -> None:
    """Enforce the existing authorization-decision contract fail-closed.

    This implementation intentionally consumes an already-issued decision. It cannot
    mint, widen, downgrade, or elevate grants.
    """
    if not isinstance(decision, dict):
        raise AuthorizationDenied("AUTH_DECISION_NOT_OBJECT")
    missing = sorted(REQUIRED_AUTH_FIELDS - set(decision))
    if missing:
        raise AuthorizationDenied("AUTH_REQUIRED_FIELDS_MISSING:" + ",".join(missing))
    if decision.get("decision") != "ALLOW":
        raise AuthorizationDenied("AUTH_DECISION_NOT_ALLOW")
    if decision.get("policy_generation") != runtime.policy_generation:
        raise AuthorizationDenied("AUTH_POLICY_GENERATION_STALE")
    if decision.get("policy_digest") != runtime.policy_digest:
        raise AuthorizationDenied("AUTH_POLICY_DIGEST_STALE")
    if decision.get("revocation_generation_seen") != runtime.revocation_generation:
        raise AuthorizationDenied("AUTH_REVOCATION_GENERATION_STALE")
    if decision.get("safe_mode_generation_seen") != runtime.safe_mode_generation:
        raise AuthorizationDenied("AUTH_SAFE_MODE_GENERATION_STALE")
    if _parse_time(decision["issued_at"]) > runtime.now.astimezone(timezone.utc):
        raise AuthorizationDenied("AUTH_ISSUED_IN_FUTURE")
    if _parse_time(decision["expires_at"]) <= runtime.now.astimezone(timezone.utc):
        raise AuthorizationDenied("AUTH_EXPIRED")
    if decision.get("operation") != operation:
        raise AuthorizationDenied("AUTH_OPERATION_MISMATCH")
    if decision.get("target") != target:
        raise AuthorizationDenied("AUTH_TARGET_MISMATCH")
    if decision.get("data_exposure_scope") != data_exposure_scope:
        raise AuthorizationDenied("AUTH_DATA_EXPOSURE_SCOPE_MISMATCH")
    requested = decision.get("permission_class_requested")
    ceiling = decision.get("permission_ceiling")
    if requested not in PERMISSION_ORDER or ceiling not in PERMISSION_ORDER:
        raise AuthorizationDenied("AUTH_PERMISSION_CLASS_UNKNOWN")
    if requested != permission_class:
        raise AuthorizationDenied("AUTH_PERMISSION_CLASS_REQUEST_MISMATCH")
    if PERMISSION_ORDER[permission_class] > PERMISSION_ORDER[ceiling]:
        raise AuthorizationDenied("AUTH_PERMISSION_CEILING_EXCEEDED")
    scope = decision.get("scope")
    if not isinstance(scope, dict):
        raise AuthorizationDenied("AUTH_SCOPE_NOT_OBJECT")
    if scope.get("operation") != operation or scope.get("target") != target:
        raise AuthorizationDenied("AUTH_SCOPE_MISMATCH")
    if permission_class != "P0_READ_PUBLIC_OR_CANONICAL" and not decision.get("grant_ref"):
        raise AuthorizationDenied("AUTH_GRANT_REQUIRED")
    if owner_gate_required:
        if not runtime.expected_owner_gate_ref:
            raise AuthorizationDenied("AUTH_RUNTIME_OWNER_GATE_REF_UNKNOWN")
        if decision.get("owner_gate_ref") != runtime.expected_owner_gate_ref:
            raise AuthorizationDenied("AUTH_OWNER_GATE_MISSING_OR_MISMATCHED")


def _empty_state() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generation": 0,
        "cache": {},
        "tasks": {},
        "task_by_idempotency": {},
        "receipts_by_idempotency": {},
    }


def _validate_state(state: Dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise SchemaError("STATE_NOT_OBJECT")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError("UNKNOWN_OR_STALE_SCHEMA_VERSION")
    if not isinstance(state.get("generation"), int) or state["generation"] < 0:
        raise SchemaError("INVALID_STATE_GENERATION")
    for key in ("cache", "tasks", "task_by_idempotency", "receipts_by_idempotency"):
        if not isinstance(state.get(key), dict):
            raise SchemaError(f"INVALID_STATE_SECTION:{key}")
    for rec in state["cache"].values():
        try:
            AuditState(rec["audit_state"])
        except (KeyError, ValueError, TypeError) as exc:
            raise SchemaError("UNKNOWN_CACHE_AUDIT_STATE") from exc


class PersistentStore:
    """Single-file durable state with process lock + generation CAS.

    This is an internal implementation candidate, not a networked service. All writes
    are atomic replace under an exclusive lock and carry an expected generation.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "r1_state.json"
        self.lock_path = self.root / "r1_state.lock"
        if not self.state_path.exists():
            self._write_raw(_empty_state())

    def _read_raw(self) -> Dict[str, Any]:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SchemaError("STATE_READ_FAILED") from exc
        _validate_state(state)
        return state

    def _write_raw(self, state: Dict[str, Any]) -> None:
        _validate_state(state)
        temp_path = self.state_path.with_suffix(".tmp")
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        with open(temp_path, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, self.state_path)

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.lock_path.touch(exist_ok=True)
        with open(self.lock_path, "r+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    def read(self) -> Dict[str, Any]:
        with self.locked():
            return copy.deepcopy(self._read_raw())

    def cas_write(self, expected_generation: int, new_state: Dict[str, Any]) -> int:
        with self.locked():
            current = self._read_raw()
            if current["generation"] != expected_generation:
                raise StaleState(
                    f"CAS_GENERATION_CONFLICT:{expected_generation}:CURRENT:{current['generation']}"
                )
            candidate = copy.deepcopy(new_state)
            candidate["generation"] = expected_generation + 1
            self._write_raw(candidate)
            return candidate["generation"]


class R1Engine:
    def __init__(self, store: PersistentStore, canonical_main: str):
        self.store = store
        self.canonical_main = canonical_main

    def _require_current_main(self, current_main: str) -> None:
        if current_main != self.canonical_main:
            raise StaleState(f"STALE_CANONICAL_MAIN:{current_main}")

    @staticmethod
    def _idem(candidate_id: str, docs_hash: str) -> str:
        return f"source-review:{candidate_id}:{docs_hash}"

    def inspect_candidate(
        self,
        *,
        current_main: str,
        candidate_id: str,
        docs_hash: str,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> Optional[str]:
        self._require_current_main(current_main)
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            target=f"source-candidate:{candidate_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY",
        )

        state = self.store.read()
        generation = state["generation"]
        existing = state["cache"].get(candidate_id)
        idem = self._idem(candidate_id, docs_hash)

        if existing and existing.get("docs_hash") == docs_hash:
            audit_state = AuditState(existing["audit_state"])
            if audit_state in {
                AuditState.REVIEWED_NO_ADMISSION,
                AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT,
            }:
                return None
            task_id = state["task_by_idempotency"].get(idem)
            if task_id:
                return task_id

        if existing is None:
            record = {
                "candidate_id": candidate_id,
                "source_class": "UNKNOWN",
                "evidence_refs": [],
                "terms_or_docs_hashes": [docs_hash],
                "docs_hash": docs_hash,
                "last_checked_at": None,
                "audit_state": AuditState.REVIEW_REQUIRED.value,
                "verdict_reason": "",
                "freshness_state": "NEW",
                "recheck_trigger": "INITIAL_REVIEW",
                "version": 0,
            }
            state["cache"][candidate_id] = record
        else:
            existing["docs_hash"] = docs_hash
            hashes = existing.setdefault("terms_or_docs_hashes", [])
            if docs_hash not in hashes:
                hashes.append(docs_hash)
            existing["audit_state"] = AuditState.CHANGED_REVIEW_REQUIRED.value
            existing["freshness_state"] = "CHANGED"
            existing["recheck_trigger"] = "DOC_HASH_CHANGED"
            existing["verdict_reason"] = ""
            existing["version"] += 1
            record = existing

        task_id = state["task_by_idempotency"].get(idem)
        if task_id:
            return task_id

        task_id = f"task-{_digest(idem)[:16]}"
        state["tasks"][task_id] = {
            "task_id": task_id,
            "idempotency_key": idem,
            "candidate_id": candidate_id,
            "input_hash": docs_hash,
            "attempt_count": 0,
            "retry_budget": 2,
            "checkpoint_ref": None,
            "lease_owner": None,
            "lease_expires_at": None,
            "heartbeat_at": None,
            "lease_epoch": 0,
            "expected_cache_version": record["version"],
            "dead_letter_reason": None,
            "authorization_ref": authorization["authorization_decision_id"],
            "durable_receipt_ref": None,
        }
        state["task_by_idempotency"][idem] = task_id
        self.store.cas_write(generation, state)
        return task_id

    def checkpoint(
        self,
        *,
        task_id: str,
        checkpoint_ref: str,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> None:
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_TASK_CHECKPOINT",
            target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="INTERNAL_R1_STATE_ONLY",
        )
        state = self.store.read()
        generation = state["generation"]
        task = state["tasks"].get(task_id)
        if not task:
            raise StaleState("TASK_NOT_FOUND")
        task["checkpoint_ref"] = checkpoint_ref
        self.store.cas_write(generation, state)

    def acquire_lease(
        self,
        *,
        task_id: str,
        worker_id: str,
        now_tick: int,
        lease_ticks: int,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> int:
        if lease_ticks <= 0:
            raise ValueError("lease_ticks must be positive")
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_TASK_ACQUIRE_LEASE",
            target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="INTERNAL_R1_STATE_ONLY",
        )
        state = self.store.read()
        generation = state["generation"]
        task = state["tasks"].get(task_id)
        if not task:
            raise StaleState("TASK_NOT_FOUND")
        if task.get("dead_letter_reason"):
            raise DeadLettered(task["dead_letter_reason"])
        task["lease_epoch"] += 1
        task["lease_owner"] = worker_id
        task["heartbeat_at"] = now_tick
        task["lease_expires_at"] = now_tick + lease_ticks
        epoch = task["lease_epoch"]
        self.store.cas_write(generation, state)
        return epoch

    def heartbeat(
        self,
        *,
        task_id: str,
        worker_id: str,
        lease_epoch: int,
        now_tick: int,
        lease_ticks: int,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> None:
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_TASK_HEARTBEAT",
            target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="INTERNAL_R1_STATE_ONLY",
        )
        state = self.store.read()
        generation = state["generation"]
        task = state["tasks"].get(task_id)
        if not task:
            raise StaleState("TASK_NOT_FOUND")
        self._assert_current_lease(task, worker_id, lease_epoch, now_tick)
        task["heartbeat_at"] = now_tick
        task["lease_expires_at"] = now_tick + lease_ticks
        self.store.cas_write(generation, state)

    @staticmethod
    def _assert_current_lease(
        task: Dict[str, Any], worker_id: str, lease_epoch: int, now_tick: int
    ) -> None:
        if task.get("lease_owner") != worker_id or task.get("lease_epoch") != lease_epoch:
            raise FencingConflict("STALE_OR_NONOWNER_LEASE_EPOCH")
        expires = task.get("lease_expires_at")
        if not isinstance(expires, int) or now_tick >= expires:
            raise FencingConflict("LEASE_EXPIRED")

    def record_failure(
        self,
        *,
        task_id: str,
        reason: str,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> None:
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_TASK_RECORD_FAILURE",
            target=f"task:{task_id}",
            permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
            data_exposure_scope="INTERNAL_R1_STATE_ONLY",
        )
        state = self.store.read()
        generation = state["generation"]
        task = state["tasks"].get(task_id)
        if not task:
            raise StaleState("TASK_NOT_FOUND")
        task["attempt_count"] += 1
        if task["attempt_count"] > task["retry_budget"]:
            task["dead_letter_reason"] = reason
        self.store.cas_write(generation, state)

    def commit_review(
        self,
        *,
        current_main: str,
        task_id: str,
        worker_id: str,
        lease_epoch: int,
        now_tick: int,
        committed_state: str,
        verdict_reason: str,
        evidence_refs: list[str],
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> Dict[str, Any]:
        self._require_current_main(current_main)

        # Condition B: full auth contract is rechecked immediately before governed write.
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_SOURCE_REVIEW_COMMIT",
            target=f"task:{task_id}",
            permission_class="P3_MATERIAL_OPERATION",
            data_exposure_scope="PUBLIC_TERMS_METADATA_ONLY",
            owner_gate_required=True,
        )

        state = self.store.read()
        generation = state["generation"]
        task = state["tasks"].get(task_id)
        if not task:
            raise StaleState("TASK_NOT_FOUND")
        if task.get("dead_letter_reason"):
            raise DeadLettered(task["dead_letter_reason"])

        # Condition A: stale/expired ownership is rejected BEFORE success receipt return.
        self._assert_current_lease(task, worker_id, lease_epoch, now_tick)

        try:
            target_state = AuditState(committed_state)
        except ValueError as exc:
            raise SchemaError("UNKNOWN_CACHE_AUDIT_STATE") from exc
        if target_state not in {
            AuditState.REVIEWED_NO_ADMISSION,
            AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT,
        }:
            raise SchemaError("R1_COMMIT_STATE_NOT_FINAL_REVIEW_STATE")
        if target_state is AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT and not evidence_refs:
            raise SchemaError("EXPLICIT_INELIGIBILITY_REQUIRES_EVIDENCE")

        payload = {
            "task_id": task_id,
            "candidate_id": task["candidate_id"],
            "input_hash": task["input_hash"],
            "committed_state": target_state.value,
            "verdict_reason": verdict_reason,
            "evidence_refs": sorted(evidence_refs),
        }
        payload_hash = _digest(payload)

        # Retry-safe convergence: same active lease + same payload gets same durable receipt.
        existing_receipt = state["receipts_by_idempotency"].get(task["idempotency_key"])
        if existing_receipt:
            if existing_receipt["payload_hash"] != payload_hash:
                raise ReceiptConflict("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD")
            return copy.deepcopy(existing_receipt)

        record = state["cache"].get(task["candidate_id"])
        if not record:
            raise StaleState("CACHE_RECORD_NOT_FOUND")
        if record["version"] != task["expected_cache_version"]:
            raise StaleState(
                f"CACHE_VERSION_CONFLICT:{task['expected_cache_version']}:CURRENT:{record['version']}"
            )
        if record["docs_hash"] != task["input_hash"]:
            raise StaleState("CACHE_DOC_HASH_DRIFT")

        record["audit_state"] = target_state.value
        record["verdict_reason"] = verdict_reason
        record["evidence_refs"] = list(evidence_refs)
        record["freshness_state"] = "REVIEWED"
        record["recheck_trigger"] = "DOC_HASH_CHANGE_OR_MANUAL_RECHECK"
        record["last_checked_at"] = auth_runtime.now.astimezone(timezone.utc).isoformat()
        record["version"] += 1

        receipt = {
            "receipt_id": f"receipt-{payload_hash[:20]}",
            "schema_version": SCHEMA_VERSION,
            "idempotency_key": task["idempotency_key"],
            "payload_hash": payload_hash,
            "candidate_id": task["candidate_id"],
            "committed_state": target_state.value,
            "cache_version_after": record["version"],
            "authorization_decision_id": authorization["authorization_decision_id"],
            "owner_gate_ref": authorization["owner_gate_ref"],
            "lease_epoch": lease_epoch,
            "worker_id": worker_id,
            "canonical_main": current_main,
        }
        state["receipts_by_idempotency"][task["idempotency_key"]] = receipt
        task["durable_receipt_ref"] = receipt["receipt_id"]
        self.store.cas_write(generation, state)
        return copy.deepcopy(receipt)

    def read_receipt(
        self,
        *,
        idempotency_key: str,
        authorization: Dict[str, Any],
        auth_runtime: AuthorizationRuntime,
    ) -> Optional[Dict[str, Any]]:
        # Distinct read-only operation; does not pretend a stale commit succeeded.
        validate_authorization(
            authorization,
            auth_runtime,
            operation="R1_RECEIPT_READ",
            target=f"receipt-idempotency:{idempotency_key}",
            permission_class="P0_READ_PUBLIC_OR_CANONICAL",
            data_exposure_scope="INTERNAL_R1_RECEIPT_ONLY",
        )
        state = self.store.read()
        receipt = state["receipts_by_idempotency"].get(idempotency_key)
        return copy.deepcopy(receipt) if receipt else None

    @staticmethod
    def owner_exception_view(
        *,
        what_changed: str,
        what_ran_automatically: str,
        blocked_reason: Optional[str] = None,
        next_safe_action: str = "NONE",
    ) -> Dict[str, Any]:
        """Observability only. This method cannot approve or execute blocked work."""
        return {
            "what_changed": what_changed,
            "what_ran_automatically": what_ran_automatically,
            "what_did_not_run": "BLOCKED_STEP_NOT_EXECUTED" if blocked_reason else "NONE",
            "what_is_blocked_and_why": blocked_reason or "NONE",
            "owner_action_required": bool(blocked_reason),
            "next_safe_action": next_safe_action,
            "approval_authority": "NONE_OBSERVABILITY_ONLY",
        }


def _auth(
    *,
    operation: str,
    target: str,
    permission: str,
    data_scope: str,
    owner_gate_ref: Optional[str] = None,
    decision: str = "ALLOW",
    policy_generation: str = "g1",
    policy_digest: str = "d1",
    revocation: int = 3,
    safe_mode: int = 5,
) -> Dict[str, Any]:
    return {
        "authorization_decision_id": f"auth-{_digest([operation,target,permission,data_scope,owner_gate_ref])[:12]}",
        "policy_generation": policy_generation,
        "policy_digest": policy_digest,
        "actor_role": "EXECUTION",
        "actor_instance": "fake-worker-harness",
        "operation": operation,
        "target": target,
        "permission_class_requested": permission,
        "permission_ceiling": "P4_OWNER_GATE_REQUIRED",
        "scope": {"operation": operation, "target": target},
        "data_exposure_scope": data_scope,
        "issued_at": "2026-08-21T03:00:00+00:00",
        "expires_at": "2026-08-21T06:00:00+00:00",
        "grant_ref": None if permission == "P0_READ_PUBLIC_OR_CANONICAL" else "grant-r1-test",
        "owner_gate_ref": owner_gate_ref,
        "revocation_generation_seen": revocation,
        "safe_mode_generation_seen": safe_mode,
        "decision": decision,
        "reason_codes": ["FAKE_HARNESS"],
        "evidence_refs": [],
    }


def _runtime(owner_gate_ref: Optional[str] = None) -> AuthorizationRuntime:
    return AuthorizationRuntime(
        policy_generation="g1",
        policy_digest="d1",
        revocation_generation=3,
        safe_mode_generation=5,
        now=datetime.fromisoformat("2026-08-21T04:00:00+00:00"),
        expected_owner_gate_ref=owner_gate_ref,
    )


def run_selftest() -> int:
    MAIN = CANONICAL_ASSESSMENT_MERGE
    OWNER_REF = f"github-pr45-comment:{OWNER_GATE_COMMENT_ID}"

    with tempfile.TemporaryDirectory(prefix="multiverse-r1-") as temp:
        store = PersistentStore(Path(temp))
        engine = R1Engine(store, MAIN)

        def auth(operation: str, target: str, permission: str, scope: str, owner=False, decision="ALLOW"):
            return _auth(
                operation=operation,
                target=target,
                permission=permission,
                data_scope=scope,
                owner_gate_ref=OWNER_REF if owner else None,
                decision=decision,
            )

        # UNKNOWN/new candidate -> one staged task; duplicate candidate -> same task.
        a_inspect = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            "source-candidate:s1",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
        )
        t1 = engine.inspect_candidate(
            current_main=MAIN,
            candidate_id="s1",
            docs_hash="h1",
            authorization=a_inspect,
            auth_runtime=_runtime(),
        )
        t2 = engine.inspect_candidate(
            current_main=MAIN,
            candidate_id="s1",
            docs_hash="h1",
            authorization=a_inspect,
            auth_runtime=_runtime(),
        )
        assert t1 == t2 and t1 is not None

        # Checkpoint then lease takeover; old worker must be rejected.
        a_checkpoint = auth(
            "R1_TASK_CHECKPOINT",
            f"task:{t1}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "INTERNAL_R1_STATE_ONLY",
        )
        engine.checkpoint(
            task_id=t1,
            checkpoint_ref="checkpoint://fake/1",
            authorization=a_checkpoint,
            auth_runtime=_runtime(),
        )
        a_lease = auth(
            "R1_TASK_ACQUIRE_LEASE",
            f"task:{t1}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "INTERNAL_R1_STATE_ONLY",
        )
        epoch_a = engine.acquire_lease(
            task_id=t1,
            worker_id="worker-a",
            now_tick=10,
            lease_ticks=10,
            authorization=a_lease,
            auth_runtime=_runtime(),
        )
        epoch_b = engine.acquire_lease(
            task_id=t1,
            worker_id="worker-b",
            now_tick=21,
            lease_ticks=10,
            authorization=a_lease,
            auth_runtime=_runtime(),
        )
        assert epoch_b > epoch_a
        takeover_state = store.read()
        assert takeover_state["tasks"][t1]["checkpoint_ref"] == "checkpoint://fake/1"

        a_commit = auth(
            "R1_SOURCE_REVIEW_COMMIT",
            f"task:{t1}",
            "P3_MATERIAL_OPERATION",
            "PUBLIC_TERMS_METADATA_ONLY",
            owner=True,
        )
        try:
            engine.commit_review(
                current_main=MAIN,
                task_id=t1,
                worker_id="worker-a",
                lease_epoch=epoch_a,
                now_tick=22,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
                verdict_reason="FAKE",
                evidence_refs=["e1"],
                authorization=a_commit,
                auth_runtime=_runtime(OWNER_REF),
            )
            raise AssertionError("old worker revival commit must fail")
        except FencingConflict:
            pass

        # New worker commits; same current lease retry returns same receipt.
        receipt1 = engine.commit_review(
            current_main=MAIN,
            task_id=t1,
            worker_id="worker-b",
            lease_epoch=epoch_b,
            now_tick=22,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
            verdict_reason="FAKE",
            evidence_refs=["e1"],
            authorization=a_commit,
            auth_runtime=_runtime(OWNER_REF),
        )
        receipt2 = engine.commit_review(
            current_main=MAIN,
            task_id=t1,
            worker_id="worker-b",
            lease_epoch=epoch_b,
            now_tick=22,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
            verdict_reason="FAKE",
            evidence_refs=["e1"],
            authorization=a_commit,
            auth_runtime=_runtime(OWNER_REF),
        )
        assert receipt1 == receipt2

        # Cache prevents repeated review of unchanged already-reviewed evidence.
        assert engine.inspect_candidate(
            current_main=MAIN,
            candidate_id="s1",
            docs_hash="h1",
            authorization=a_inspect,
            auth_runtime=_runtime(),
        ) is None

        # Condition A: once a newer lease exists, old epoch cannot get success receipt.
        epoch_c = engine.acquire_lease(
            task_id=t1,
            worker_id="worker-c",
            now_tick=23,
            lease_ticks=10,
            authorization=a_lease,
            auth_runtime=_runtime(),
        )
        assert epoch_c > epoch_b
        try:
            engine.commit_review(
                current_main=MAIN,
                task_id=t1,
                worker_id="worker-b",
                lease_epoch=epoch_b,
                now_tick=24,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
                verdict_reason="FAKE",
                evidence_refs=["e1"],
                authorization=a_commit,
                auth_runtime=_runtime(OWNER_REF),
            )
            raise AssertionError("stale worker must not receive commit success receipt")
        except FencingConflict:
            pass

        # Dedicated read-only receipt lookup still works with separate auth.
        idem = R1Engine._idem("s1", "h1")
        a_read = auth(
            "R1_RECEIPT_READ",
            f"receipt-idempotency:{idem}",
            "P0_READ_PUBLIC_OR_CANONICAL",
            "INTERNAL_R1_RECEIPT_ONLY",
        )
        assert engine.read_receipt(
            idempotency_key=idem,
            authorization=a_read,
            auth_runtime=_runtime(),
        ) == receipt1

        # Stale canonical input fails.
        try:
            engine.inspect_candidate(
                current_main="stale-main",
                candidate_id="s2",
                docs_hash="h2",
                authorization=auth(
                    "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                    "source-candidate:s2",
                    "P1_REVERSIBLE_INTERNAL_WRITE",
                    "PUBLIC_TERMS_METADATA_ONLY",
                ),
                auth_runtime=_runtime(),
            )
            raise AssertionError("stale canonical must fail")
        except StaleState:
            pass

        # DENY and Owner Gate mismatch fail.
        try:
            engine.inspect_candidate(
                current_main=MAIN,
                candidate_id="s2",
                docs_hash="h2",
                authorization=auth(
                    "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                    "source-candidate:s2",
                    "P1_REVERSIBLE_INTERNAL_WRITE",
                    "PUBLIC_TERMS_METADATA_ONLY",
                    decision="DENY",
                ),
                auth_runtime=_runtime(),
            )
            raise AssertionError("DENY must fail")
        except AuthorizationDenied:
            pass

        try:
            engine.commit_review(
                current_main=MAIN,
                task_id=t1,
                worker_id="worker-c",
                lease_epoch=epoch_c,
                now_tick=24,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
                verdict_reason="FAKE",
                evidence_refs=["e1"],
                authorization=_auth(
                    operation="R1_SOURCE_REVIEW_COMMIT",
                    target=f"task:{t1}",
                    permission="P3_MATERIAL_OPERATION",
                    data_scope="PUBLIC_TERMS_METADATA_ONLY",
                    owner_gate_ref="wrong-owner-gate",
                ),
                auth_runtime=_runtime(OWNER_REF),
            )
            raise AssertionError("Owner gate mismatch must fail")
        except AuthorizationDenied:
            pass

        # Protected data scope cannot be silently widened.
        try:
            validate_authorization(
                auth(
                    "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                    "source-candidate:s3",
                    "P1_REVERSIBLE_INTERNAL_WRITE",
                    "PUBLIC_TERMS_METADATA_ONLY",
                ),
                _runtime(),
                operation="R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                target="source-candidate:s3",
                permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
                data_exposure_scope="SEALED_PROTECTED_DATA",
            )
            raise AssertionError("protected data scope mismatch must fail")
        except AuthorizationDenied:
            pass

        # Retry exhaustion -> dead letter.
        a_inspect3 = auth(
            "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
            "source-candidate:s3",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "PUBLIC_TERMS_METADATA_ONLY",
        )
        t3 = engine.inspect_candidate(
            current_main=MAIN,
            candidate_id="s3",
            docs_hash="h3",
            authorization=a_inspect3,
            auth_runtime=_runtime(),
        )
        a_fail = auth(
            "R1_TASK_RECORD_FAILURE",
            f"task:{t3}",
            "P1_REVERSIBLE_INTERNAL_WRITE",
            "INTERNAL_R1_STATE_ONLY",
        )
        engine.record_failure(task_id=t3, reason="timeout", authorization=a_fail, auth_runtime=_runtime())
        engine.record_failure(task_id=t3, reason="timeout", authorization=a_fail, auth_runtime=_runtime())
        engine.record_failure(task_id=t3, reason="timeout", authorization=a_fail, auth_runtime=_runtime())
        try:
            engine.acquire_lease(
                task_id=t3,
                worker_id="worker-z",
                now_tick=1,
                lease_ticks=5,
                authorization=auth(
                    "R1_TASK_ACQUIRE_LEASE",
                    f"task:{t3}",
                    "P1_REVERSIBLE_INTERNAL_WRITE",
                    "INTERNAL_R1_STATE_ONLY",
                ),
                auth_runtime=_runtime(),
            )
            raise AssertionError("dead-lettered task must not reacquire")
        except DeadLettered:
            pass

        # Conflicting payload reuse: create candidate s4, commit, then same current lease different payload.
        t4 = engine.inspect_candidate(
            current_main=MAIN,
            candidate_id="s4",
            docs_hash="h4",
            authorization=auth(
                "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                "source-candidate:s4",
                "P1_REVERSIBLE_INTERNAL_WRITE",
                "PUBLIC_TERMS_METADATA_ONLY",
            ),
            auth_runtime=_runtime(),
        )
        e4 = engine.acquire_lease(
            task_id=t4,
            worker_id="worker-4",
            now_tick=1,
            lease_ticks=20,
            authorization=auth(
                "R1_TASK_ACQUIRE_LEASE",
                f"task:{t4}",
                "P1_REVERSIBLE_INTERNAL_WRITE",
                "INTERNAL_R1_STATE_ONLY",
            ),
            auth_runtime=_runtime(),
        )
        c4 = auth(
            "R1_SOURCE_REVIEW_COMMIT",
            f"task:{t4}",
            "P3_MATERIAL_OPERATION",
            "PUBLIC_TERMS_METADATA_ONLY",
            owner=True,
        )
        engine.commit_review(
            current_main=MAIN,
            task_id=t4,
            worker_id="worker-4",
            lease_epoch=e4,
            now_tick=2,
            committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
            verdict_reason="A",
            evidence_refs=["e"],
            authorization=c4,
            auth_runtime=_runtime(OWNER_REF),
        )
        try:
            engine.commit_review(
                current_main=MAIN,
                task_id=t4,
                worker_id="worker-4",
                lease_epoch=e4,
                now_tick=2,
                committed_state=AuditState.REVIEWED_NO_ADMISSION.value,
                verdict_reason="B",
                evidence_refs=["e"],
                authorization=c4,
                auth_runtime=_runtime(OWNER_REF),
            )
            raise AssertionError("conflicting payload reuse must fail")
        except ReceiptConflict:
            pass

        # Concurrent version conflict: stale copy cannot overwrite newer generation.
        stale = store.read()
        current = store.read()
        cg = current["generation"]
        current["cache"]["s4"]["freshness_state"] = "TOUCHED"
        store.cas_write(cg, current)
        try:
            store.cas_write(stale["generation"], stale)
            raise AssertionError("stale CAS write must fail")
        except StaleState:
            pass

        # Unknown enum fails closed.
        bad = store.read()
        bg = bad["generation"]
        bad["cache"]["s4"]["audit_state"] = "MADE_UP_STATE"
        try:
            store.cas_write(bg, bad)
            raise AssertionError("unknown state must fail")
        except SchemaError:
            pass

        # Owner view is observability only.
        view = engine.owner_exception_view(
            what_changed="R1_SELFTEST",
            what_ran_automatically="FAKE_INTERNAL_TESTS_ONLY",
            blocked_reason="RUNTIME_ACTIVATION_NOT_AUTHORIZED",
            next_safe_action="IMPLEMENTATION_REVIEW",
        )
        assert view["owner_action_required"] is True
        assert view["approval_authority"] == "NONE_OBSERVABILITY_ONLY"

    print("MULTIVERSE_R1_SOURCE_VERTICAL_SLICE_SELFTEST_PASS")
    print("SCHEMA_PINNED=true")
    print("FENCING_BEFORE_COMMIT_SUCCESS=true")
    print("AUTHORIZATION_CONTRACT_PRECONDITIONS_ENFORCED=true")
    print("DURABLE_RECEIPT_SEPARATE_READ=true")
    print("EXACTLY_ONCE_CLAIM=false")
    print("NETWORK_ACCESS_PERFORMED=false")
    print("SOURCE_ADMISSION_PERFORMED=false")
    print("REAL_LIVE_PRE_ACCESSED=false")
    print("EXTERNAL_PROVIDER_CONTACT_PERFORMED=false")
    print("PROTECTED_DATA_ACCESSED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()
    print("R1_LIBRARY_ONLY_NO_AUTORUN_RUNTIME_ACTIVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
