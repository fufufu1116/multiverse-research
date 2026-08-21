#!/usr/bin/env python3
"""R1 Limited Internal Runtime Stage 1 library.

This module is deliberately dormant by default. It consumes trusted current
AuthorizationRuntime objects supplied by an external canonical control-plane
adapter; it never derives, mints, or widens grants itself.
"""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional

from multiverse_r1_auth_v1 import AuthorizationDenied, AuthorizationRuntime, validate_authorization
from multiverse_r1_engine_v1 import R1Engine
from multiverse_r1_state_v1 import AuditState, PersistentStore, SchemaError, StaleState

STAGE_SCHEMA = "MULTIVERSE_R1_LIMITED_INTERNAL_RUNTIME_STAGE1_SCHEMA_v1"
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
    "last_runtime_head",
    "invocation_active",
}


class Stage1Denied(RuntimeError):
    pass


class Stage1Paused(Stage1Denied):
    pass


class Stage1Tamper(Stage1Denied):
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
    """Provided only by an already-trusted canonical control-plane adapter.

    The Stage-1 library deliberately has no file/JSON loader for this object so
    an enqueue payload cannot self-assert current grants, revocations, or safe
    mode. The adapter that constructs this object remains an audited
    pre-activation dependency.
    """

    enqueue_runtime: AuthorizationRuntime
    worker_runtime: AuthorizationRuntime


def empty_control(
    *,
    activation_receipt_id: str,
    canonical_main: str,
    audited_implementation_head: str,
    runtime_genesis: str,
    activated_at: datetime,
) -> dict:
    if not _nonempty(activation_receipt_id) or not _hex40(canonical_main) or not _hex40(audited_implementation_head) or not _hex40(runtime_genesis):
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
        "last_runtime_head": runtime_genesis,
        "invocation_active": False,
    }


def validate_control(control: Mapping[str, Any]) -> None:
    if not isinstance(control, dict) or set(control) != CONTROL_FIELDS:
        _deny("STAGE_CONTROL_SCHEMA")
    if control["schema_version"] != STAGE_SCHEMA or control["stage_id"] != STAGE_ID:
        _deny("STAGE_CONTROL_IDENTITY")
    for field in ("activation_receipt_id", "runtime_branch"):
        if not _nonempty(control[field]):
            _deny("STAGE_CONTROL_STRING")
    for field in ("canonical_main", "audited_implementation_head", "runtime_genesis", "last_runtime_head"):
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
    if not isinstance(control["paused"], bool) or not isinstance(control["invocation_active"], bool):
        _deny("STAGE_CONTROL_BOOL")
    if control["pause_reason"] is not None and not _nonempty(control["pause_reason"]):
        _deny("STAGE_CONTROL_PAUSE_REASON")


def assert_ceiling_and_integrity(
    control: Mapping[str, Any],
    *,
    current_main: str,
    current_runtime_head: str,
    now: datetime,
    genesis_is_ancestor: bool,
    remote_high_water_count: int,
) -> None:
    validate_control(control)
    if current_main != control["canonical_main"]:
        _deny("STALE_CANONICAL_MAIN", StaleState)
    if current_runtime_head != control["last_runtime_head"]:
        _deny("UNEXPECTED_RUNTIME_REF_MOVEMENT", Stage1Tamper)
    if not genesis_is_ancestor:
        _deny("RUNTIME_ANCESTRY_TAMPER", Stage1Tamper)
    if not _strict_int(remote_high_water_count):
        _deny("HIGH_WATER_INVALID")
    if control["terminal_count"] < remote_high_water_count:
        _deny("TERMINAL_COUNT_ROLLBACK_DETECTED", Stage1Tamper)
    if control["paused"]:
        _deny("STAGE_ALREADY_PAUSED", Stage1Paused)
    if control["invocation_active"]:
        _deny("SECOND_WORKER_OR_PARALLEL_INVOCATION", Stage1Denied)
    if control["terminal_count"] >= MAX_TERMINAL_TASKS:
        _deny("STAGE_TERMINAL_CEILING_REACHED", Stage1Paused)
    if now.tzinfo is None:
        _deny("NOW_NOT_OFFSET_AWARE")
    if now.astimezone(timezone.utc) >= _utc(control["activated_at"]) + timedelta(days=WINDOW_DAYS):
        _deny("STAGE_TIME_CEILING_REACHED", Stage1Paused)


def begin_invocation(control: Mapping[str, Any]) -> dict:
    validate_control(control)
    if control["invocation_active"]:
        _deny("SECOND_WORKER_OR_PARALLEL_INVOCATION")
    out = copy.deepcopy(control)
    out["invocation_active"] = True
    return out


def finish_invocation(control: Mapping[str, Any]) -> dict:
    validate_control(control)
    out = copy.deepcopy(control)
    out["invocation_active"] = False
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
    out["invocation_active"] = False
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
    if envelope["requested_final_state"] == AuditState.EXPLICIT_INELIGIBLE_ONLY_WHEN_EVIDENCE_SUPPORTS_IT.value and not envelope["evidence_refs"]:
        _deny("ENQUEUE_INELIGIBLE_EVIDENCE_REQUIRED")


def validate_enqueue_authority(
    envelope: Mapping[str, Any],
    *,
    trusted: TrustedAuthorityContext,
) -> None:
    _validate_envelope_shape(envelope)
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


def process_one(
    *,
    store: PersistentStore,
    envelope: Mapping[str, Any],
    control: Mapping[str, Any],
    trusted: TrustedAuthorityContext,
    current_main: str,
    current_runtime_head: str,
    now: datetime,
    now_tick: int,
    genesis_is_ancestor: bool,
    remote_high_water_count: int,
) -> tuple[Optional[dict], dict]:
    """Process exactly one supplied-evidence admin task without network access."""
    assert_ceiling_and_integrity(
        control,
        current_main=current_main,
        current_runtime_head=current_runtime_head,
        now=now,
        genesis_is_ancestor=genesis_is_ancestor,
        remote_high_water_count=remote_high_water_count,
    )
    validate_enqueue_authority(envelope, trusted=trusted)
    active = begin_invocation(control)
    engine = R1Engine(store, current_main)
    auths = envelope["operation_authorizations"]
    cid = envelope["candidate_id"]
    docs_hash = envelope["docs_hash"]
    worker = envelope["worker_id"]
    task_id = engine.inspect_candidate(
        current_main=current_main,
        candidate_id=cid,
        docs_hash=docs_hash,
        authorization=auths["inspect"],
        auth_runtime=trusted.worker_runtime,
    )
    if task_id is None:
        return None, finish_invocation(active)
    epoch = engine.acquire_lease(
        current_main=current_main,
        task_id=task_id,
        worker_id=worker,
        now_tick=now_tick,
        lease_ticks=10,
        authorization=auths["lease"],
        auth_runtime=trusted.worker_runtime,
    )
    engine.checkpoint(
        current_main=current_main,
        task_id=task_id,
        worker_id=worker,
        lease_epoch=epoch,
        now_tick=now_tick + 1,
        checkpoint_ref="stage1:supplied-evidence-validated",
        authorization=auths["checkpoint"],
        auth_runtime=trusted.worker_runtime,
    )
    receipt = engine.commit_review(
        current_main=current_main,
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
    completed = record_terminal_receipt(active, receipt["receipt_id"])
    return receipt, finish_invocation(completed)


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


def _runtime(actor: str, *, valid=True, safe=False) -> AuthorizationRuntime:
    return AuthorizationRuntime(
        "g-stage1-test",
        "digest-stage1-test",
        4,
        2,
        datetime.fromisoformat("2026-08-21T08:00:00+00:00"),
        "EXECUTION",
        actor,
        frozenset({"grant-stage1-test"}) if valid else frozenset(),
        None,
        safe,
    )


def _envelope(cid="source-a", docs="docs-a", actor="worker-1") -> dict:
    task_target = "PLACEHOLDER"
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
            "inspect": _decision("R1_SOURCE_CACHE_INSPECT_OR_STAGE", f"source-candidate:{cid}", "PUBLIC_TERMS_METADATA_ONLY", actor),
            "lease": _decision("R1_TASK_ACQUIRE_LEASE", task_target, "INTERNAL_R1_STATE_ONLY", actor),
            "checkpoint": _decision("R1_TASK_CHECKPOINT", task_target, "INTERNAL_R1_STATE_ONLY", actor),
            "commit": _decision("R1_SOURCE_REVIEW_COMMIT", task_target, "PUBLIC_TERMS_METADATA_ONLY", actor),
        },
    }


def _bind_task_auths(envelope: dict, task_id: str) -> dict:
    out = copy.deepcopy(envelope)
    actor = out["worker_id"]
    out["operation_authorizations"]["lease"] = _decision("R1_TASK_ACQUIRE_LEASE", f"task:{task_id}", "INTERNAL_R1_STATE_ONLY", actor)
    out["operation_authorizations"]["checkpoint"] = _decision("R1_TASK_CHECKPOINT", f"task:{task_id}", "INTERNAL_R1_STATE_ONLY", actor)
    out["operation_authorizations"]["commit"] = _decision("R1_SOURCE_REVIEW_COMMIT", f"task:{task_id}", "PUBLIC_TERMS_METADATA_ONLY", actor)
    return out


def _expect(exc, fn):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


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
    assert control["terminal_count"] == 0

    validate_write_path(RUNTIME_BRANCH, "runtime/r1_source_audit_stage1/tasks/enqueue/a.json")
    for branch, path in (
        ("main", "runtime/r1_source_audit_stage1/tasks/x.json"),
        (RUNTIME_BRANCH, "governance/x.json"),
        (RUNTIME_BRANCH, "runtime/r1_source_audit_stage1/tasks/../../governance/x.json"),
        (RUNTIME_BRANCH, "README.md"),
    ):
        _expect(Stage1Denied, lambda b=branch, p=path: validate_write_path(b, p))

    for role in sorted(AUTHORITY_ROLES):
        _expect(Stage1Denied, lambda r=role: reject_runtime_artifact_as_authority(r, {"status": "ADMITTED", "grant_ref": "forged"}))
    _expect(Stage1Denied, lambda: reject_runtime_artifact_as_authority("UNKNOWN_ROLE", {}))
    assert validate_runtime_cache_state("REVIEWED_NO_ADMISSION") == "REVIEWED_NO_ADMISSION"
    _expect(Stage1Denied, lambda: validate_runtime_cache_state("ADMITTED"))
    _expect(Stage1Denied, lambda: validate_runtime_cache_state("PERMISSION_GRANTED"))

    assert_ceiling_and_integrity(control, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=0)
    _expect(StaleState, lambda: assert_ceiling_and_integrity(control, current_main="d" * 40, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=0))
    _expect(Stage1Tamper, lambda: assert_ceiling_and_integrity(control, current_main=main, current_runtime_head="d" * 40, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=0))
    _expect(Stage1Tamper, lambda: assert_ceiling_and_integrity(control, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=False, remote_high_water_count=0))
    rollback = copy.deepcopy(control)
    rollback["terminal_count"] = 0
    rollback["counted_receipt_ids"] = []
    _expect(Stage1Tamper, lambda: assert_ceiling_and_integrity(rollback, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=1))
    active = begin_invocation(control)
    _expect(Stage1Denied, lambda: assert_ceiling_and_integrity(active, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=0))
    _expect(Stage1Paused, lambda: assert_ceiling_and_integrity(control, current_main=main, current_runtime_head=genesis, now=activated + timedelta(days=7), genesis_is_ancestor=True, remote_high_water_count=0))
    c = copy.deepcopy(control)
    for i in range(25):
        c = record_terminal_receipt(c, f"receipt-{i:02d}")
    assert c["terminal_count"] == 25 and c["paused"] is True
    before = copy.deepcopy(c)
    c2 = record_terminal_receipt(c, "receipt-24")
    assert c2 == before
    _expect(Stage1Paused, lambda: record_terminal_receipt(c, "receipt-26"))
    _expect(Stage1Paused, lambda: assert_ceiling_and_integrity(c, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=25))
    paused = pause_for_integrity(control, "TAMPER")
    _expect(Stage1Paused, lambda: assert_ceiling_and_integrity(paused, current_main=main, current_runtime_head=genesis, now=activated + timedelta(hours=1), genesis_is_ancestor=True, remote_high_water_count=0))

    env = _envelope()
    trusted = TrustedAuthorityContext(_runtime("router-1"), _runtime("worker-1"))
    validate_enqueue_authority(env, trusted=trusted)
    wrong = copy.deepcopy(env)
    wrong["enqueue_authorization"]["operation"] = "ISSUE_COMMENT"
    _expect(AuthorizationDenied, lambda: validate_enqueue_authority(wrong, trusted=trusted))
    wrong = copy.deepcopy(env)
    wrong["enqueue_authorization"]["scope"]["target"] = "comment:1"
    _expect(AuthorizationDenied, lambda: validate_enqueue_authority(wrong, trusted=trusted))
    wrong = copy.deepcopy(env)
    wrong["candidate_id"] = ["bad"]
    _expect(Stage1Denied, lambda: validate_enqueue_authority(wrong, trusted=trusted))
    _expect(AuthorizationDenied, lambda: validate_enqueue_authority(env, trusted=TrustedAuthorityContext(_runtime("router-1", valid=False), _runtime("worker-1"))))
    _expect(AuthorizationDenied, lambda: validate_enqueue_authority(env, trusted=TrustedAuthorityContext(_runtime("router-1", safe=True), _runtime("worker-1"))))
    _expect(AuthorizationDenied, lambda: validate_enqueue_authority(env, trusted=TrustedAuthorityContext(_runtime("router-1"), _runtime("other-worker"))))

    with tempfile.TemporaryDirectory() as td:
        store = PersistentStore(Path(td))
        engine = R1Engine(store, main)
        tid = engine.inspect_candidate(
            current_main=main,
            candidate_id=env["candidate_id"],
            docs_hash=env["docs_hash"],
            authorization=env["operation_authorizations"]["inspect"],
            auth_runtime=trusted.worker_runtime,
        )
        assert tid
        env2 = _bind_task_auths(env, tid)
        receipt, out = process_one(
            store=store,
            envelope=env2,
            control=control,
            trusted=trusted,
            current_main=main,
            current_runtime_head=genesis,
            now=activated + timedelta(hours=1),
            now_tick=1,
            genesis_is_ancestor=True,
            remote_high_water_count=0,
        )
        assert receipt and out["terminal_count"] == 1 and out["invocation_active"] is False
        assert receipt["committed_state"] == "REVIEWED_NO_ADMISSION"
        receipt2, out2 = process_one(
            store=store,
            envelope=env2,
            control=out,
            trusted=trusted,
            current_main=main,
            current_runtime_head=genesis,
            now=activated + timedelta(hours=2),
            now_tick=20,
            genesis_is_ancestor=True,
            remote_high_water_count=1,
        )
        assert receipt2 is None and out2["terminal_count"] == 1
        bad = json.loads(store.state_path.read_text())
        bad["cache"][env["candidate_id"]]["audit_state"] = "ADMITTED"
        store.state_path.write_text(json.dumps(bad))
        _expect(SchemaError, store.read)

    view = owner_exception("AUTHORIZATION_DENY")
    assert view["approval_authority"] == "NONE_OBSERVABILITY_ONLY" and view["owner_action_required"] is True

    for marker in (
        "EXPLICIT_AUTHORIZED_ENQUEUE_ONLY",
        "RAW_GITHUB_EVENT_COMMENT_URL_NOT_AUTHORITY",
        "ONE_WORKER_CEILING_ENFORCED",
        "RUNTIME_BRANCH_AND_PATH_BOUNDARY_ENFORCED",
        "ROLLBACK_ANCESTRY_AND_HIGH_WATER_TAMPER_DENIED",
        "TERMINAL_25_OR_7_DAY_AUTO_PAUSE_ENFORCED",
        "LOST_ACK_TERMINAL_COUNT_IDEMPOTENT",
        "RUNTIME_STATE_SECOND_AUTHORITY_REJECTED",
        "ADMITTED_AND_PERMISSION_LIKE_RUNTIME_STATE_DENIED",
        "TRUSTED_AUTHORITY_CONTEXT_REQUIRED_EXTERNALLY",
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
    print("R1_STAGE1_LIBRARY_ONLY_RUNTIME_OFF_NO_TRUSTED_AUTHORITY_ADAPTER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
