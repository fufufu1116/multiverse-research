#!/usr/bin/env python3
"""R1 Limited Internal Runtime Stage 1 library.

Dormant by default. The production-shaped path never accepts caller-supplied
AuthorizationRuntime facts directly: it asks an independently reviewed
control-plane adapter for canonical authority facts and for durable remote-CAS
runtime state. No concrete live GitHub adapter is activated in this candidate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Protocol

from multiverse_r1_auth_v1 import AuthorizationDenied, AuthorizationRuntime, validate_authorization
from multiverse_r1_engine_v1 import R1Engine
from multiverse_r1_state_v1 import (
    AuditState,
    PersistentStore,
    SchemaError,
    StaleState,
    empty_state,
    validate_state,
)

STAGE_SCHEMA = "MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_SCHEMA_v2"
ENQUEUE_SCHEMA = "MULTIVERSE_R1_STAGE1_ENQUEUE_ENVELOPE_v1"
STAGE_ID = "R1_LIMITED_INTERNAL_RUNTIME_STAGE1"
RUNTIME_BRANCH = "runtime/r1-source-audit-stage1-v1"
ENQUEUE_OPERATION = "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK"
ENQUEUE_TARGET = RUNTIME_BRANCH
ENQUEUE_SCOPE = "GITHUB_INTERNAL_SOURCE_AUDIT_ADMIN_METADATA_ONLY"
MAX_WORKERS = 1
MAX_TASKS_PER_INVOCATION = 10
MAX_TERMINAL_TASKS = 25
WINDOW_DAYS = 7
RETRY_BUDGET = 2
INVOCATION_LEASE_MINUTES = 5
ALLOWED_PREFIXES = (
    "runtime/r1_source_audit_stage1/cache/",
    "runtime/r1_source_audit_stage1/tasks/",
    "runtime/r1_source_audit_stage1/receipts/",
    "runtime/r1_source_audit_stage1/exceptions/",
)
AUTHORITY_ROLES = {
    "OWNER_GATE",
    "AUTHORIZATION_GRANT",
    "PERMISSION_EVIDENCE",
    "SOURCE_ADMISSION_RECEIPT",
    "CANONICAL_GOVERNANCE_FACT",
}
ENQUEUE_FIELDS = {
    "schema_version",
    "stage_id",
    "candidate_id",
    "docs_hash",
    "worker_id",
    "requested_final_state",
    "verdict_reason",
    "evidence_refs",
    "enqueue_authorization",
    "operation_authorizations",
}
OP_AUTH_FIELDS = {"inspect", "lease", "checkpoint", "commit"}
CONTROL_FIELDS = {
    "schema_version",
    "stage_id",
    "activation_receipt_id",
    "canonical_main",
    "audited_implementation_head",
    "runtime_branch",
    "runtime_genesis",
    "activated_at",
    "terminal_count",
    "counted_receipt_ids",
    "paused",
    "pause_reason",
    "invocation_claim_id",
    "invocation_claim_expires_at",
}


class Stage1Denied(RuntimeError):
    pass


class Stage1Paused(Stage1Denied):
    pass


class Stage1Tamper(Stage1Denied):
    pass


class InjectedCrash(RuntimeError):
    pass


def _deny(code: str, exc=Stage1Denied):
    raise exc(code)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _hex40(value: Any) -> bool:
    return _nonempty(value) and len(value) == 40 and all(c in "0123456789abcdef" for c in value.lower())


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        _deny("TIME_INVALID")
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise Stage1Denied("TIME_INVALID") from exc
    if out.tzinfo is None:
        _deny("TIME_NOT_OFFSET_AWARE")
    return out.astimezone(timezone.utc)


def validate_write_path(branch: str, path: str) -> None:
    if branch != RUNTIME_BRANCH:
        _deny("RUNTIME_WRONG_BRANCH")
    if not _nonempty(path):
        _deny("RUNTIME_PATH_INVALID")
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        _deny("RUNTIME_PATH_TRAVERSAL")
    normalized = str(p)
    if normalized.startswith("governance/") or normalized == "governance" or normalized.startswith(".github/"):
        _deny("RUNTIME_CANONICAL_OR_GOVERNANCE_WRITE_DENIED")
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        _deny("RUNTIME_PATH_OUTSIDE_ALLOWED_PREFIX")


def reject_runtime_artifact_as_authority(claimed_role: str, artifact: Mapping[str, Any]) -> None:
    del artifact
    if claimed_role in AUTHORITY_ROLES:
        _deny("RUNTIME_ARTIFACT_CANNOT_BE_AUTHORITY")
    _deny("UNKNOWN_AUTHORITY_ROLE_DENIED")


def validate_runtime_cache_state(value: Any) -> str:
    try:
        state = AuditState(value)
    except Exception as exc:
        raise Stage1Denied("RUNTIME_CACHE_STATE_UNKNOWN") from exc
    if state.value == "ADMITTED":
        _deny("RUNTIME_ADMITTED_STATE_PROHIBITED")
    return state.value


@dataclass(frozen=True)
class TrustedAuthorityContext:
    enqueue_runtime: AuthorizationRuntime
    worker_runtime: AuthorizationRuntime
    canonical_main: str
    provenance_ref: str
    verified_from_canonical_authority: bool


@dataclass(frozen=True)
class RemoteSnapshot:
    remote_head: str
    canonical_main: str
    runtime_genesis: str
    genesis_is_ancestor: bool
    high_water_count: int
    control: dict
    r1_state: dict


class ControlPlaneAdapter(Protocol):
    """Pre-activation contract for an independently reviewed canonical adapter."""

    def load_snapshot(self) -> RemoteSnapshot: ...

    def load_trusted_authority(
        self,
        *,
        current_main: str,
        enqueue_actor_role: str,
        enqueue_actor_instance: str,
        worker_actor_instance: str,
        now: datetime,
    ) -> TrustedAuthorityContext: ...

    def claim_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        claimed_control: Mapping[str, Any],
    ) -> RemoteSnapshot: ...

    def persist_r1_state(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        r1_state: Mapping[str, Any],
    ) -> RemoteSnapshot: ...

    def release_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        released_control: Mapping[str, Any],
    ) -> RemoteSnapshot: ...


def empty_control(
    *,
    activation_receipt_id: str,
    canonical_main: str,
    audited_implementation_head: str,
    runtime_genesis: str,
    activated_at: datetime,
) -> dict:
    if (
        not _nonempty(activation_receipt_id)
        or not _hex40(canonical_main)
        or not _hex40(audited_implementation_head)
        or not _hex40(runtime_genesis)
    ):
        _deny("ACTIVATION_IDENTITY_INVALID")
    if activated_at.tzinfo is None:
        _deny("ACTIVATION_TIME_NOT_AWARE")
    return {
        "schema_version": STAGE_SCHEMA,
        "stage_id": STAGE_ID,
        "activation_receipt_id": activation_receipt_id,
        "canonical_main": canonical_main,
        "audited_implementation_head": audited_implementation_head,
        "runtime_branch": RUNTIME_BRANCH,
        "runtime_genesis": runtime_genesis,
        "activated_at": activated_at.astimezone(timezone.utc).isoformat(),
        "terminal_count": 0,
        "counted_receipt_ids": [],
        "paused": False,
        "pause_reason": None,
        "invocation_claim_id": None,
        "invocation_claim_expires_at": None,
    }


def validate_control(control: Mapping[str, Any]) -> None:
    if not isinstance(control, dict) or set(control) != CONTROL_FIELDS:
        _deny("STAGE_CONTROL_SCHEMA")
    if control["schema_version"] != STAGE_SCHEMA or control["stage_id"] != STAGE_ID:
        _deny("STAGE_CONTROL_IDENTITY")
    for field in ("activation_receipt_id", "runtime_branch"):
        if not _nonempty(control[field]):
            _deny("STAGE_CONTROL_STRING")
    for field in ("canonical_main", "audited_implementation_head", "runtime_genesis"):
        if not _hex40(control[field]):
            _deny("STAGE_CONTROL_SHA")
    if control["runtime_branch"] != RUNTIME_BRANCH:
        _deny("STAGE_CONTROL_BRANCH")
    _utc(control["activated_at"])
    if not _strict_int(control["terminal_count"]):
        _deny("STAGE_CONTROL_COUNT")
    ids = control["counted_receipt_ids"]
    if not isinstance(ids, list) or not all(_nonempty(x) for x in ids) or len(set(ids)) != len(ids):
        _deny("STAGE_CONTROL_RECEIPTS")
    if control["terminal_count"] != len(ids):
        _deny("STAGE_CONTROL_COUNT_RECEIPT_MISMATCH")
    if not isinstance(control["paused"], bool):
        _deny("STAGE_CONTROL_BOOL")
    if control["pause_reason"] is not None and not _nonempty(control["pause_reason"]):
        _deny("STAGE_CONTROL_PAUSE_REASON")
    claim_id = control["invocation_claim_id"]
    claim_expiry = control["invocation_claim_expires_at"]
    if (claim_id is None) != (claim_expiry is None):
        _deny("STAGE_CONTROL_CLAIM_PAIR")
    if claim_id is not None:
        if not _nonempty(claim_id):
            _deny("STAGE_CONTROL_CLAIM_ID")
        _utc(claim_expiry)


def validate_trusted_authority_context(trusted: TrustedAuthorityContext, *, current_main: str) -> None:
    if not isinstance(trusted, TrustedAuthorityContext):
        _deny("TRUSTED_AUTHORITY_CONTEXT_TYPE")
    if trusted.verified_from_canonical_authority is not True:
        _deny("TRUSTED_AUTHORITY_PROVENANCE_UNVERIFIED", AuthorizationDenied)
    if trusted.canonical_main != current_main or not _hex40(trusted.canonical_main):
        _deny("TRUSTED_AUTHORITY_CANONICAL_MAIN_MISMATCH", AuthorizationDenied)
    if not _nonempty(trusted.provenance_ref):
        _deny("TRUSTED_AUTHORITY_PROVENANCE_REF_MISSING", AuthorizationDenied)


def reconcile_terminal_receipts(control: Mapping[str, Any], r1_state: Mapping[str, Any]) -> dict:
    validate_control(control)
    state = copy.deepcopy(r1_state)
    validate_state(state)
    receipt_ids = sorted({r["receipt_id"] for r in state["receipts_by_idempotency"].values()})
    if len(receipt_ids) > MAX_TERMINAL_TASKS:
        _deny("DURABLE_RECEIPT_COUNT_EXCEEDS_STAGE_CEILING", Stage1Tamper)
    out = copy.deepcopy(control)
    known = set(out["counted_receipt_ids"])
    for receipt_id in receipt_ids:
        if receipt_id not in known:
            out["counted_receipt_ids"].append(receipt_id)
            known.add(receipt_id)
    out["terminal_count"] = len(out["counted_receipt_ids"])
    if out["terminal_count"] >= MAX_TERMINAL_TASKS:
        out["paused"] = True
        out["pause_reason"] = "STAGE_TERMINAL_CEILING_REACHED"
    validate_control(out)
    return out


def assert_ceiling_and_integrity(
    control: Mapping[str, Any],
    *,
    current_main: str,
    now: datetime,
    genesis_is_ancestor: bool,
    remote_high_water_count: int,
) -> None:
    validate_control(control)
    if current_main != control["canonical_main"]:
        _deny("STALE_CANONICAL_MAIN", StaleState)
    if not genesis_is_ancestor:
        _deny("RUNTIME_ANCESTRY_TAMPER", Stage1Tamper)
    if not _strict_int(remote_high_water_count):
        _deny("HIGH_WATER_INVALID")
    if control["terminal_count"] < remote_high_water_count:
        _deny("TERMINAL_COUNT_ROLLBACK_DETECTED", Stage1Tamper)
    if control["paused"]:
        _deny("STAGE_ALREADY_PAUSED", Stage1Paused)
    if control["terminal_count"] >= MAX_TERMINAL_TASKS:
        _deny("STAGE_TERMINAL_CEILING_REACHED", Stage1Paused)
    if now.tzinfo is None:
        _deny("NOW_NOT_OFFSET_AWARE")
    if now.astimezone(timezone.utc) >= _utc(control["activated_at"]) + timedelta(days=WINDOW_DAYS):
        _deny("STAGE_TIME_CEILING_REACHED", Stage1Paused)


def claim_control(control: Mapping[str, Any], *, claim_id: str, now: datetime) -> dict:
    validate_control(control)
    if not _nonempty(claim_id):
        _deny("INVOCATION_CLAIM_ID_INVALID")
    if now.tzinfo is None:
        _deny("NOW_NOT_OFFSET_AWARE")
    existing = control["invocation_claim_id"]
    expiry = control["invocation_claim_expires_at"]
    if existing is not None and now.astimezone(timezone.utc) < _utc(expiry):
        _deny("SECOND_WORKER_OR_PARALLEL_INVOCATION")
    out = copy.deepcopy(control)
    out["invocation_claim_id"] = claim_id
    out["invocation_claim_expires_at"] = (
        now.astimezone(timezone.utc) + timedelta(minutes=INVOCATION_LEASE_MINUTES)
    ).isoformat()
    validate_control(out)
    return out


def release_control(control: Mapping[str, Any], *, claim_id: str) -> dict:
    validate_control(control)
    if control["invocation_claim_id"] != claim_id:
        _deny("STALE_CONTROL_PLANE_CLAIM", Stage1Tamper)
    out = copy.deepcopy(control)
    out["invocation_claim_id"] = None
    out["invocation_claim_expires_at"] = None
    validate_control(out)
    return out


def record_terminal_receipt(control: Mapping[str, Any], receipt_id: str) -> dict:
    validate_control(control)
    if not _nonempty(receipt_id):
        _deny("RECEIPT_ID_INVALID")
    out = copy.deepcopy(control)
    if receipt_id not in out["counted_receipt_ids"]:
        if out["terminal_count"] >= MAX_TERMINAL_TASKS:
            _deny("TASK_26_DENIED", Stage1Paused)
        out["counted_receipt_ids"].append(receipt_id)
        out["terminal_count"] += 1
    if out["terminal_count"] >= MAX_TERMINAL_TASKS:
        out["paused"] = True
        out["pause_reason"] = "STAGE_TERMINAL_CEILING_REACHED"
    return out


def pause_for_integrity(control: Mapping[str, Any], reason: str) -> dict:
    validate_control(control)
    if not _nonempty(reason):
        _deny("PAUSE_REASON_INVALID")
    out = copy.deepcopy(control)
    out["paused"] = True
    out["pause_reason"] = reason
    out["invocation_claim_id"] = None
    out["invocation_claim_expires_at"] = None
    return out


def _validate_envelope_shape(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, dict) or set(envelope) != ENQUEUE_FIELDS:
        _deny("ENQUEUE_SCHEMA")
    if envelope["schema_version"] != ENQUEUE_SCHEMA or envelope["stage_id"] != STAGE_ID:
        _deny("ENQUEUE_IDENTITY")
    for field in ("candidate_id", "docs_hash", "worker_id", "verdict_reason"):
        if not _nonempty(envelope[field]):
            _deny("ENQUEUE_STRING")
    if not isinstance(envelope["evidence_refs"], list) or not all(_nonempty(x) for x in envelope["evidence_refs"]):
        _deny("ENQUEUE_EVIDENCE")
    if not isinstance(envelope["operation_authorizations"], dict) or set(envelope["operation_authorizations"]) != OP_AUTH_FIELDS:
        _deny("ENQUEUE_OPERATION_AUTH_SCHEMA")
    if envelope["requested_final_state"] not in {
        AuditState.REVIEWED_NO_ADMISSION.value,
        AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT.value,
    }:
        _deny("ENQUEUE_FINAL_STATE")
    if (
        envelope["requested_final_state"]
        == AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT.value
        and not envelope["evidence_refs"]
    ):
        _deny("ENQUEUE_INELIGIBLE_EVIDENCE_REQUIRED")


def validate_enqueue_authority(
    envelope: Mapping[str, Any],
    *,
    trusted: TrustedAuthorityContext,
    current_main: str,
) -> None:
    _validate_envelope_shape(envelope)
    validate_trusted_authority_context(trusted, current_main=current_main)
    validate_authorization(
        envelope["enqueue_authorization"],
        trusted.enqueue_runtime,
        operation=ENQUEUE_OPERATION,
        target=ENQUEUE_TARGET,
        permission_class="P1_REVERSIBLE_INTERNAL_WRITE",
        data_exposure_scope=ENQUEUE_SCOPE,
    )
    if envelope["worker_id"] != trusted.worker_runtime.actor_instance:
        _deny("ENQUEUE_WORKER_BINDING_MISMATCH", AuthorizationDenied)


def _materialize_store(root: Path, state: Mapping[str, Any]) -> PersistentStore:
    root.mkdir(parents=True, exist_ok=True)
    payload = copy.deepcopy(state)
    validate_state(payload)
    (root / "r1_state.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return PersistentStore(root)


def _process_claimed(
    *,
    adapter: ControlPlaneAdapter,
    claimed: RemoteSnapshot,
    envelope: Mapping[str, Any],
    trusted: TrustedAuthorityContext,
    now: datetime,
    now_tick: int,
    claim_id: str,
    failpoint: Optional[str] = None,
) -> tuple[Optional[dict], dict]:
    validate_enqueue_authority(envelope, trusted=trusted, current_main=claimed.canonical_main)
    with tempfile.TemporaryDirectory() as td:
        store = _materialize_store(Path(td), claimed.r1_state)
        engine = R1Engine(store, claimed.canonical_main)
        auths = envelope["operation_authorizations"]
        cid = envelope["candidate_id"]
        docs_hash = envelope["docs_hash"]
        worker = envelope["worker_id"]

        task_id = engine.inspect_candidate(
            current_main=claimed.canonical_main,
            candidate_id=cid,
            docs_hash=docs_hash,
            authorization=auths["inspect"],
            auth_runtime=trusted.worker_runtime,
        )
        claimed = adapter.persist_r1_state(
            expected_remote_head=claimed.remote_head,
            claim_id=claim_id,
            r1_state=store.read(),
        )
        if task_id is None:
            finished = reconcile_terminal_receipts(claimed.control, claimed.r1_state)
            finished = release_control(finished, claim_id=claim_id)
            released = adapter.release_invocation(
                expected_remote_head=claimed.remote_head,
                claim_id=claim_id,
                released_control=finished,
            )
            return None, released.control

        epoch = engine.acquire_lease(
            current_main=claimed.canonical_main,
            task_id=task_id,
            worker_id=worker,
            now_tick=now_tick,
            lease_ticks=10,
            authorization=auths["lease"],
            auth_runtime=trusted.worker_runtime,
        )
        claimed = adapter.persist_r1_state(
            expected_remote_head=claimed.remote_head,
            claim_id=claim_id,
            r1_state=store.read(),
        )
        engine.checkpoint(
            current_main=claimed.canonical_main,
            task_id=task_id,
            worker_id=worker,
            lease_epoch=epoch,
            now_tick=now_tick + 1,
            checkpoint_ref="stage1:supplied-evidence-validated",
            authorization=auths["checkpoint"],
            auth_runtime=trusted.worker_runtime,
        )
        claimed = adapter.persist_r1_state(
            expected_remote_head=claimed.remote_head,
            claim_id=claim_id,
            r1_state=store.read(),
        )
        receipt = engine.commit_review(
            current_main=claimed.canonical_main,
            task_id=task_id,
            worker_id=worker,
            lease_epoch=epoch,
            now_tick=now_tick + 2,
            committed_state=envelope["requested_final_state"],
            verdict_reason=envelope["verdict_reason"],
            evidence_refs=envelope["evidence_refs"],
            authorization=auths["commit"],
            auth_runtime=trusted.worker_runtime,
        )
        claimed = adapter.persist_r1_state(
            expected_remote_head=claimed.remote_head,
            claim_id=claim_id,
            r1_state=store.read(),
        )
        if failpoint == "AFTER_DURABLE_RECEIPT_BEFORE_STAGE_COUNT":
            raise InjectedCrash(failpoint)

        finished = reconcile_terminal_receipts(claimed.control, claimed.r1_state)
        finished = release_control(finished, claim_id=claim_id)
        released = adapter.release_invocation(
            expected_remote_head=claimed.remote_head,
            claim_id=claim_id,
            released_control=finished,
        )
        return receipt, released.control


def _process_one_controlled(
    *,
    adapter: ControlPlaneAdapter,
    envelope: Mapping[str, Any],
    now: datetime,
    now_tick: int,
    claim_id: str,
    failpoint: Optional[str] = None,
) -> tuple[Optional[dict], dict]:
    snapshot = adapter.load_snapshot()
    if not _hex40(snapshot.remote_head) or not _hex40(snapshot.canonical_main):
        _deny("CONTROL_PLANE_SNAPSHOT_IDENTITY")
    validate_state(copy.deepcopy(snapshot.r1_state))
    reconciled = reconcile_terminal_receipts(snapshot.control, snapshot.r1_state)
    assert_ceiling_and_integrity(
        reconciled,
        current_main=snapshot.canonical_main,
        now=now,
        genesis_is_ancestor=snapshot.genesis_is_ancestor,
        remote_high_water_count=snapshot.high_water_count,
    )
    claimed_control = claim_control(reconciled, claim_id=claim_id, now=now)
    claimed = adapter.claim_invocation(
        expected_remote_head=snapshot.remote_head,
        claim_id=claim_id,
        claimed_control=claimed_control,
    )
    enqueue_decision = envelope.get("enqueue_authorization")
    if not isinstance(enqueue_decision, dict):
        _deny("ENQUEUE_AUTHORIZATION_MISSING")
    trusted = adapter.load_trusted_authority(
        current_main=claimed.canonical_main,
        enqueue_actor_role=enqueue_decision.get("actor_role"),
        enqueue_actor_instance=enqueue_decision.get("actor_instance"),
        worker_actor_instance=envelope.get("worker_id"),
        now=now,
    )
    validate_trusted_authority_context(trusted, current_main=claimed.canonical_main)
    return _process_claimed(
        adapter=adapter,
        claimed=claimed,
        envelope=envelope,
        trusted=trusted,
        now=now,
        now_tick=now_tick,
        claim_id=claim_id,
        failpoint=failpoint,
    )


def process_one_controlled(
    *,
    adapter: ControlPlaneAdapter,
    envelope: Mapping[str, Any],
    now: datetime,
    now_tick: int,
    claim_id: str,
) -> tuple[Optional[dict], dict]:
    """Production-shaped entrypoint. No direct TrustedAuthorityContext argument."""
    return _process_one_controlled(
        adapter=adapter,
        envelope=envelope,
        now=now,
        now_tick=now_tick,
        claim_id=claim_id,
        failpoint=None,
    )


def owner_exception(reason: str, next_safe_action: str = "PAUSE_AND_REVIEW") -> dict:
    return R1Engine.owner_exception_view(
        what_changed="R1_STAGE1_RUNTIME",
        what_ran_automatically="BOUNDED_INTERNAL_ADMIN_ONLY",
        blocked_reason=reason,
        next_safe_action=next_safe_action,
    )


def _decision(operation: str, target: str, scope: str, actor: str, *, decision: str = "ALLOW") -> dict:
    return {
        "authorization_decision_id": f"auth-{operation}-{actor}",
        "policy_generation": "g-stage1-test",
        "policy_digest": "digest-stage1-test",
        "actor_role": "EXECUTION",
        "actor_instance": actor,
        "operation": operation,
        "target": target,
        "permission_class_requested": "P1_REVERSIBLE_INTERNAL_WRITE",
        "permission_ceiling": "P1_REVERSIBLE_INTERNAL_WRITE",
        "scope": {"operation": operation, "target": target, "data_exposure_scope": scope},
        "data_exposure_scope": scope,
        "issued_at": "2026-08-21T07:00:00+00:00",
        "expires_at": "2026-08-22T07:00:00+00:00",
        "grant_ref": "grant-stage1-test",
        "owner_gate_ref": None,
        "revocation_generation_seen": 4,
        "safe_mode_generation_seen": 2,
        "decision": decision,
        "reason_codes": ["SELFTEST_ONLY"],
        "evidence_refs": [],
    }


def _runtime(actor: str, now: datetime, *, valid=True, safe=False) -> AuthorizationRuntime:
    return AuthorizationRuntime(
        "g-stage1-test",
        "digest-stage1-test",
        4,
        2,
        now,
        "EXECUTION",
        actor,
        frozenset({"grant-stage1-test"}) if valid else frozenset(),
        None,
        safe,
    )


def _task_id(cid: str, docs: str) -> str:
    idem = f"source-review:{cid}:{docs}"
    encoded = json.dumps(idem, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return "task-" + digest[:16]


def _envelope(cid="source-a", docs="docs-a", actor="worker-1") -> dict:
    tid = _task_id(cid, docs)
    return {
        "schema_version": ENQUEUE_SCHEMA,
        "stage_id": STAGE_ID,
        "candidate_id": cid,
        "docs_hash": docs,
        "worker_id": actor,
        "requested_final_state": AuditState.REVIEWED_NO_ADMISSION.value,
        "verdict_reason": "supplied evidence supports no admission",
        "evidence_refs": ["governance:evidence-a"],
        "enqueue_authorization": _decision(ENQUEUE_OPERATION, ENQUEUE_TARGET, ENQUEUE_SCOPE, "router-1"),
        "operation_authorizations": {
            "inspect": _decision(
                "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
                f"source-candidate:{cid}",
                "PUBLIC_TERMS_METADATA_ONLY",
                actor,
            ),
            "lease": _decision("R1_TASK_ACQUIRE_LEASE", f"task:{tid}", "INTERNAL_R1_STATE_ONLY", actor),
            "checkpoint": _decision("R1_TASK_CHECKPOINT", f"task:{tid}", "INTERNAL_R1_STATE_ONLY", actor),
            "commit": _decision("R1_SOURCE_REVIEW_COMMIT", f"task:{tid}", "PUBLIC_TERMS_METADATA_ONLY", actor),
        },
    }


def _expect(exc, fn):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


class _SharedRemote:
    def __init__(self, control: dict, canonical_main: str, genesis: str):
        self.serial = 1
        self.head = "1" * 40
        self.control = copy.deepcopy(control)
        self.r1_state = empty_state()
        self.canonical_main = canonical_main
        self.genesis = genesis
        self.high_water = 0

    def advance(self, payload: Mapping[str, Any]) -> str:
        self.serial += 1
        raw = json.dumps(payload, sort_keys=True, default=str) + f":{self.serial}:{self.head}"
        self.head = hashlib.sha1(raw.encode()).hexdigest()
        return self.head


class _FakeControlPlaneAdapter:
    def __init__(self, shared: _SharedRemote, *, verified=True, valid_grant=True, safe=False):
        self.shared = shared
        self.verified = verified
        self.valid_grant = valid_grant
        self.safe = safe

    def _snapshot(self) -> RemoteSnapshot:
        return RemoteSnapshot(
            remote_head=self.shared.head,
            canonical_main=self.shared.canonical_main,
            runtime_genesis=self.shared.genesis,
            genesis_is_ancestor=True,
            high_water_count=self.shared.high_water,
            control=copy.deepcopy(self.shared.control),
            r1_state=copy.deepcopy(self.shared.r1_state),
        )

    def load_snapshot(self) -> RemoteSnapshot:
        return self._snapshot()

    def load_trusted_authority(
        self,
        *,
        current_main: str,
        enqueue_actor_role: str,
        enqueue_actor_instance: str,
        worker_actor_instance: str,
        now: datetime,
    ) -> TrustedAuthorityContext:
        if enqueue_actor_role != "EXECUTION":
            _deny("FAKE_CANONICAL_ACTOR_ROLE_DENY", AuthorizationDenied)
        if enqueue_actor_instance != "router-1" or worker_actor_instance != "worker-1":
            _deny("FAKE_CANONICAL_ACTOR_INSTANCE_DENY", AuthorizationDenied)
        return TrustedAuthorityContext(
            enqueue_runtime=_runtime("router-1", now, valid=self.valid_grant, safe=self.safe),
            worker_runtime=_runtime("worker-1", now, valid=self.valid_grant, safe=self.safe),
            canonical_main=current_main,
            provenance_ref="canonical:test-authority-snapshot",
            verified_from_canonical_authority=self.verified,
        )

    def _cas(self, expected_remote_head: str) -> None:
        if expected_remote_head != self.shared.head:
            _deny("REMOTE_EXPECTED_OLD_HEAD_CAS_CONFLICT", Stage1Tamper)

    def _claim_matches(self, claim_id: str) -> None:
        if self.shared.control["invocation_claim_id"] != claim_id:
            _deny("REMOTE_STALE_OR_NONOWNER_INVOCATION_CLAIM", Stage1Tamper)

    def claim_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        claimed_control: Mapping[str, Any],
    ) -> RemoteSnapshot:
        self._cas(expected_remote_head)
        validate_control(claimed_control)
        self.shared.control = copy.deepcopy(claimed_control)
        self.shared.advance({"kind": "claim", "claim_id": claim_id, "control": self.shared.control})
        return self._snapshot()

    def persist_r1_state(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        r1_state: Mapping[str, Any],
    ) -> RemoteSnapshot:
        self._cas(expected_remote_head)
        self._claim_matches(claim_id)
        state = copy.deepcopy(r1_state)
        validate_state(state)
        self.shared.r1_state = state
        self.shared.advance({"kind": "r1", "claim_id": claim_id, "generation": state["generation"]})
        return self._snapshot()

    def release_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        released_control: Mapping[str, Any],
    ) -> RemoteSnapshot:
        self._cas(expected_remote_head)
        self._claim_matches(claim_id)
        validate_control(released_control)
        if released_control["invocation_claim_id"] is not None:
            _deny("RELEASE_CONTROL_STILL_CLAIMED")
        self.shared.control = copy.deepcopy(released_control)
        self.shared.high_water = max(self.shared.high_water, self.shared.control["terminal_count"])
        self.shared.advance({"kind": "release", "claim_id": claim_id, "control": self.shared.control})
        return self._snapshot()


def selftest() -> int:
    main = "a" * 40
    impl = "b" * 40
    genesis = "c" * 40
    activated = datetime.fromisoformat("2026-08-21T07:30:00+00:00")
    control = empty_control(
        activation_receipt_id="activation-stage1-test",
        canonical_main=main,
        audited_implementation_head=impl,
        runtime_genesis=genesis,
        activated_at=activated,
    )

    validate_write_path(RUNTIME_BRANCH, "runtime/r1_source_audit_stage1/tasks/enqueue/a.json")
    for branch, path in (
        ("main", "runtime/r1_source_audit_stage1/tasks/x.json"),
        (RUNTIME_BRANCH, "governance/x.json"),
        (RUNTIME_BRANCH, "runtime/r1_source_audit_stage1/tasks/../../governance/x.json"),
        (RUNTIME_BRANCH, "README.md"),
    ):
        _expect(Stage1Denied, lambda b=branch, p=path: validate_write_path(b, p))

    for role in sorted(AUTHORITY_ROLES):
        _expect(Stage1Denied, lambda r=role: reject_runtime_artifact_as_authority(r, {"status": "ADMITTED"}))
    _expect(Stage1Denied, lambda: validate_runtime_cache_state("ADMITTED"))
    _expect(Stage1Denied, lambda: validate_runtime_cache_state("PERMISSION_GRANTED"))

    assert_ceiling_and_integrity(
        control,
        current_main=main,
        now=activated + timedelta(hours=1),
        genesis_is_ancestor=True,
        remote_high_water_count=0,
    )
    _expect(
        StaleState,
        lambda: assert_ceiling_and_integrity(
            control,
            current_main="d" * 40,
            now=activated + timedelta(hours=1),
            genesis_is_ancestor=True,
            remote_high_water_count=0,
        ),
    )
    _expect(
        Stage1Tamper,
        lambda: assert_ceiling_and_integrity(
            control,
            current_main=main,
            now=activated + timedelta(hours=1),
            genesis_is_ancestor=False,
            remote_high_water_count=0,
        ),
    )
    rollback = copy.deepcopy(control)
    _expect(
        Stage1Tamper,
        lambda: assert_ceiling_and_integrity(
            rollback,
            current_main=main,
            now=activated + timedelta(hours=1),
            genesis_is_ancestor=True,
            remote_high_water_count=1,
        ),
    )
    _expect(
        Stage1Paused,
        lambda: assert_ceiling_and_integrity(
            control,
            current_main=main,
            now=activated + timedelta(days=7),
            genesis_is_ancestor=True,
            remote_high_water_count=0,
        ),
    )

    c = copy.deepcopy(control)
    for i in range(25):
        c = record_terminal_receipt(c, f"receipt-{i:02d}")
    assert c["terminal_count"] == 25 and c["paused"] is True
    assert record_terminal_receipt(c, "receipt-24") == c
    _expect(Stage1Paused, lambda: record_terminal_receipt(c, "receipt-26"))

    env = _envelope()
    shared = _SharedRemote(control, main, genesis)
    a1 = _FakeControlPlaneAdapter(shared)
    a2 = _FakeControlPlaneAdapter(shared)
    stale_head = a2.load_snapshot().remote_head
    claim = claim_control(control, claim_id="claim-a", now=activated + timedelta(hours=1))
    first = a1.claim_invocation(expected_remote_head=stale_head, claim_id="claim-a", claimed_control=claim)
    _expect(
        Stage1Tamper,
        lambda: a2.claim_invocation(
            expected_remote_head=stale_head,
            claim_id="claim-b",
            claimed_control=claim_control(control, claim_id="claim-b", now=activated + timedelta(hours=1)),
        ),
    )
    _expect(
        Stage1Tamper,
        lambda: a2.persist_r1_state(
            expected_remote_head=first.remote_head,
            claim_id="claim-b",
            r1_state=first.r1_state,
        ),
    )

    shared = _SharedRemote(control, main, genesis)
    bad_provenance = _FakeControlPlaneAdapter(shared, verified=False)
    _expect(
        AuthorizationDenied,
        lambda: _process_one_controlled(
            adapter=bad_provenance,
            envelope=env,
            now=activated + timedelta(hours=1),
            now_tick=1,
            claim_id="bad-prov",
        ),
    )

    shared = _SharedRemote(control, main, genesis)
    good = _FakeControlPlaneAdapter(shared)
    receipt, out = process_one_controlled(
        adapter=good,
        envelope=env,
        now=activated + timedelta(hours=1),
        now_tick=1,
        claim_id="claim-good",
    )
    assert receipt and out["terminal_count"] == 1
    assert shared.high_water == 1
    assert shared.control["invocation_claim_id"] is None

    shared = _SharedRemote(control, main, genesis)
    crash_adapter = _FakeControlPlaneAdapter(shared)
    _expect(
        InjectedCrash,
        lambda: _process_one_controlled(
            adapter=crash_adapter,
            envelope=env,
            now=activated + timedelta(hours=1),
            now_tick=1,
            claim_id="claim-crash",
            failpoint="AFTER_DURABLE_RECEIPT_BEFORE_STAGE_COUNT",
        ),
    )
    assert len(shared.r1_state["receipts_by_idempotency"]) == 1
    assert shared.control["terminal_count"] == 0
    assert shared.control["invocation_claim_id"] == "claim-crash"

    later = activated + timedelta(hours=2)
    receipt2, out2 = process_one_controlled(
        adapter=_FakeControlPlaneAdapter(shared),
        envelope=env,
        now=later,
        now_tick=50,
        claim_id="claim-restart",
    )
    assert receipt2 is None
    assert out2["terminal_count"] == 1
    assert len(out2["counted_receipt_ids"]) == 1
    assert shared.high_water == 1
    again = reconcile_terminal_receipts(out2, shared.r1_state)
    assert again == out2

    tampered = copy.deepcopy(shared.control)
    tampered["terminal_count"] = 0
    tampered["counted_receipt_ids"] = []
    _expect(
        Stage1Tamper,
        lambda: assert_ceiling_and_integrity(
            tampered,
            current_main=main,
            now=later,
            genesis_is_ancestor=True,
            remote_high_water_count=1,
        ),
    )

    view = owner_exception("AUTHORIZATION_DENY")
    assert view["approval_authority"] == "NONE_OBSERVABILITY_ONLY"
    assert view["owner_action_required"] is True

    for marker in (
        "EXPLICIT_AUTHORIZED_ENQUEUE_ONLY",
        "RAW_GITHUB_EVENT_COMMENT_URL_NOT_AUTHORITY",
        "TRUSTED_AUTHORITY_CONTEXT_NOT_CALLER_INJECTABLE_ON_CONTROLLED_PATH",
        "TRUSTED_AUTHORITY_PROVENANCE_FAIL_CLOSED",
        "REMOTE_SINGLE_INVOCATION_CAS_SHARED_BACKEND_REJECTS_SECOND",
        "STALE_CONTROL_PLANE_CLAIM_REJECTED",
        "CROSS_STORE_RECEIPT_RECONCILIATION_AFTER_CRASH",
        "DURABLE_RECEIPT_COUNTED_EXACTLY_ONCE_AFTER_RESTART",
        "ROLLBACK_ANCESTRY_AND_HIGH_WATER_TAMPER_DENIED",
        "TERMINAL_25_OR_7_DAY_AUTO_PAUSE_ENFORCED",
        "RUNTIME_BRANCH_AND_PATH_BOUNDARY_ENFORCED",
        "RUNTIME_STATE_SECOND_AUTHORITY_REJECTED",
        "ADMITTED_AND_PERMISSION_LIKE_RUNTIME_STATE_DENIED",
        "CONCRETE_LIVE_CONTROL_PLANE_ADAPTER_STILL_REQUIRED",
        "NETWORK_ACCESS_PERFORMED=false",
        "RUNTIME_ACTIVATION_PERFORMED=false",
    ):
        print(marker)
    print("MULTIVERSE_R1_STAGE1_RUNTIME_SELFTEST_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    print("R1_STAGE1_LIBRARY_ONLY_RUNTIME_OFF_CONTROL_PLANE_ADAPTER_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
