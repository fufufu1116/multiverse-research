#!/usr/bin/env python3
"""Stage-1 production authority source integration adapter v2.

Child of the independently reviewed read-only v1 adapter. This module does not
activate Runtime and does not mint permissions on demand.

v2 closes the real-source content-address self-reference in manifest v1:
the authority manifest no longer embeds the SHA of the commit that contains
it. Instead, the separately verified immutable activation anchor pins current
canonical main plus exact manifest commit/path/blob/SHA-256. All effective
Stage-1 authority state is structurally self-contained in that single manifest
blob, so any policy/grant/revocation/Safe-Mode/bundle change necessarily changes
the blob and therefore must advance canonical main before it can be consumed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from multiverse_r1_stage1_canonical_authority_adapter_v1 import (
    ACCEPTED_AUTHORITY_STATUS,
    AUTHORITY_SCOPE,
    BUNDLE_FIELDS,
    MAX_AUTHORITY_BUNDLES,
    TRUSTED_CLOCK_SOURCE,
    CanonicalAuthorityDecisionAdapter,
    CanonicalAuthorityDenied,
    VerifiedCanonicalAuthorityAnchor,
    _HEX64,
    _decision_digest,
    _nonempty,
    _sha256_json,
)
from multiverse_r1_stage1_runtime_v1 import (
    AUTH_KEYS,
    ENQUEUE_OPERATION,
    ENQUEUE_SCHEMA,
    ENQUEUE_SCOPE,
    ENQUEUE_TARGET,
    STAGE_ID,
)

AUTHORITY_MANIFEST_SCHEMA_V2 = "MULTIVERSE_R1_STAGE1_CANONICAL_AUTHORITY_MANIFEST_v2"
POLICY_GENERATION = "R1_STAGE1_PRODUCTION_AUTHORITY_POLICY_v1"
FRESHNESS_BARRIER_MODE = "SELF_CONTAINED_SINGLE_CANONICAL_MAIN_BLOB"

MANIFEST_V2_FIELDS = {
    "schema_version",
    "status",
    "canonical_authority",
    "authority_scope",
    "policy_generation",
    "policy",
    "policy_digest",
    "revocation_generation",
    "safe_mode_generation",
    "safe_mode_active",
    "valid_grant_refs",
    "trusted_clock_source",
    "freshness_barrier_mode",
    "external_authority_state_refs",
    "bundles",
}

EXPECTED_POLICY = {
    "stage_id": STAGE_ID,
    "authority_scope": AUTHORITY_SCOPE,
    "runtime_branch": ENQUEUE_TARGET,
    "enqueue_operation": ENQUEUE_OPERATION,
    "enqueue_target": ENQUEUE_TARGET,
    "enqueue_data_exposure_scope": ENQUEUE_SCOPE,
    "operation_keys": ["checkpoint", "commit", "failure", "inspect", "lease"],
    "allowed_operations": [
        "R1_SOURCE_CACHE_INSPECT_OR_STAGE",
        "R1_SOURCE_REVIEW_COMMIT",
        "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK",
        "R1_TASK_ACQUIRE_LEASE",
        "R1_TASK_CHECKPOINT",
        "R1_TASK_RECORD_FAILURE",
    ],
    "permission_class": "P1_REVERSIBLE_INTERNAL_WRITE",
    "max_concurrent_workers": 1,
    "max_tasks_per_invocation": 10,
    "retry_budget_per_task": 2,
    "max_terminal_tasks": 25,
    "runtime_window_days": 7,
    "auto_resume_authorized": False,
    "scheduler_authorized": False,
    "always_on_worker_authorized": False,
    "network_or_public_web_authorized": False,
    "source_collection_authorized": False,
    "source_admission_or_promotion_authorized": False,
    "real_or_live_pre_authorized": False,
    "external_contact_authorized": False,
    "runtime_writes_to_canonical_main_or_governance_authorized": False,
    "on_demand_permission_minting_authorized": False,
}
EXPECTED_POLICY_DIGEST = _sha256_json(EXPECTED_POLICY)


def _deny(code: str) -> None:
    raise CanonicalAuthorityDenied(code)


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_policy(value: Any, digest: Any) -> None:
    if not isinstance(value, dict) or value != EXPECTED_POLICY:
        _deny("AUTHORITY_V2_POLICY_SCOPE_DRIFT")
    if digest != EXPECTED_POLICY_DIGEST or digest != _sha256_json(value):
        _deny("AUTHORITY_V2_POLICY_DIGEST_MISMATCH")


def _validate_bundle_structure(
    bundle: Any,
    *,
    policy_generation: str,
    policy_digest: str,
    revocation_generation: int,
    safe_mode_generation: int,
    valid_grants: set[str],
    seen_bundle_ids: set[str],
    seen_envelopes: set[str],
    seen_decisions: set[str],
) -> None:
    if not isinstance(bundle, dict) or set(bundle) != BUNDLE_FIELDS:
        _deny("AUTHORITY_V2_BUNDLE_SCHEMA")
    bid = bundle["bundle_id"]
    if not _nonempty(bid) or bid in seen_bundle_ids:
        _deny("AUTHORITY_V2_BUNDLE_ID_INVALID")
    envelope_digest = bundle["envelope_digest"]
    if not isinstance(envelope_digest, str) or not _HEX64.fullmatch(envelope_digest) or envelope_digest in seen_envelopes:
        _deny("AUTHORITY_V2_ENVELOPE_DIGEST_INVALID")
    seen_bundle_ids.add(bid)
    seen_envelopes.add(envelope_digest)

    for field in ("enqueue_actor_role", "enqueue_actor_instance", "worker_actor_role", "worker_actor_instance"):
        if not _nonempty(bundle[field]):
            _deny("AUTHORITY_V2_ACTOR_IDENTITY_INVALID")

    enqueue = bundle["enqueue_decision"]
    operations = bundle["operation_decisions"]
    if not isinstance(enqueue, dict) or not isinstance(operations, dict) or set(operations) != AUTH_KEYS:
        _deny("AUTHORITY_V2_DECISION_SET_INVALID")
    if bundle["decision_payload_digest"] != _decision_digest(enqueue, operations):
        _deny("AUTHORITY_V2_DECISION_DIGEST_MISMATCH")

    for decision in [enqueue, *operations.values()]:
        if not isinstance(decision, dict):
            _deny("AUTHORITY_V2_DECISION_INVALID")
        did = decision.get("authorization_decision_id")
        if not _nonempty(did) or did in seen_decisions:
            _deny("AUTHORITY_V2_DECISION_ID_NOT_UNIQUE")
        seen_decisions.add(did)
        if decision.get("policy_generation") != policy_generation or decision.get("policy_digest") != policy_digest:
            _deny("AUTHORITY_V2_DECISION_POLICY_IDENTITY_MISMATCH")
        if decision.get("revocation_generation_seen") != revocation_generation:
            _deny("AUTHORITY_V2_DECISION_REVOCATION_GENERATION_MISMATCH")
        if decision.get("safe_mode_generation_seen") != safe_mode_generation:
            _deny("AUTHORITY_V2_DECISION_SAFE_MODE_GENERATION_MISMATCH")
        if decision.get("permission_class_requested") != "P0_READ_PUBLIC_OR_CANONICAL":
            grant = decision.get("grant_ref")
            if not _nonempty(grant) or grant not in valid_grants:
                _deny("AUTHORITY_V2_DECISION_GRANT_NOT_CURRENT")

    if enqueue.get("actor_role") != bundle["enqueue_actor_role"] or enqueue.get("actor_instance") != bundle["enqueue_actor_instance"]:
        _deny("AUTHORITY_V2_ENQUEUE_ACTOR_MISMATCH")
    for decision in operations.values():
        if decision.get("actor_role") != bundle["worker_actor_role"] or decision.get("actor_instance") != bundle["worker_actor_instance"]:
            _deny("AUTHORITY_V2_WORKER_ACTOR_MISMATCH")


def validate_source_manifest_structure(value: Any) -> dict:
    """Validate the self-contained authority source without trusting branch status."""
    if not isinstance(value, dict) or set(value) != MANIFEST_V2_FIELDS:
        _deny("AUTHORITY_V2_MANIFEST_SCHEMA")
    if value["schema_version"] != AUTHORITY_MANIFEST_SCHEMA_V2:
        _deny("AUTHORITY_V2_MANIFEST_IDENTITY")
    if value["status"] != ACCEPTED_AUTHORITY_STATUS or value["canonical_authority"] is not True:
        _deny("AUTHORITY_V2_STATUS_OR_CANONICAL_FLAG_INVALID")
    if value["authority_scope"] != AUTHORITY_SCOPE:
        _deny("AUTHORITY_V2_SCOPE_MISMATCH")
    if value["policy_generation"] != POLICY_GENERATION:
        _deny("AUTHORITY_V2_POLICY_GENERATION_MISMATCH")
    _validate_policy(value["policy"], value["policy_digest"])
    if not _strict_int(value["revocation_generation"]) or value["revocation_generation"] < 1:
        _deny("AUTHORITY_V2_REVOCATION_GENERATION_INVALID")
    if not _strict_int(value["safe_mode_generation"]) or value["safe_mode_generation"] < 1:
        _deny("AUTHORITY_V2_SAFE_MODE_GENERATION_INVALID")
    if not isinstance(value["safe_mode_active"], bool):
        _deny("AUTHORITY_V2_SAFE_MODE_INVALID")
    if value["trusted_clock_source"] != TRUSTED_CLOCK_SOURCE:
        _deny("AUTHORITY_V2_TRUSTED_CLOCK_SOURCE_MISMATCH")
    if value["freshness_barrier_mode"] != FRESHNESS_BARRIER_MODE:
        _deny("AUTHORITY_V2_FRESHNESS_MODE_INVALID")
    if value["external_authority_state_refs"] != []:
        _deny("AUTHORITY_V2_EXTERNAL_AUTHORITY_STATE_PROHIBITED")

    grants = value["valid_grant_refs"]
    if not isinstance(grants, list) or not all(_nonempty(x) for x in grants) or len(grants) != len(set(grants)):
        _deny("AUTHORITY_V2_GRANTS_INVALID")
    bundles = value["bundles"]
    if not isinstance(bundles, list) or not (0 <= len(bundles) <= MAX_AUTHORITY_BUNDLES):
        _deny("AUTHORITY_V2_BUNDLE_COUNT_INVALID")

    # The adopted root is intentionally deny-all. A zero-bundle source must
    # remain Safe Mode ON and carry no current P1 grants.
    if not bundles:
        if value["safe_mode_active"] is not True:
            _deny("AUTHORITY_V2_EMPTY_ROOT_REQUIRES_SAFE_MODE")
        if grants != []:
            _deny("AUTHORITY_V2_EMPTY_ROOT_REQUIRES_ZERO_GRANTS")
        return copy.deepcopy(value)

    seen_bundle_ids: set[str] = set()
    seen_envelopes: set[str] = set()
    seen_decisions: set[str] = set()
    valid_grants = set(grants)
    for bundle in bundles:
        _validate_bundle_structure(
            bundle,
            policy_generation=value["policy_generation"],
            policy_digest=value["policy_digest"],
            revocation_generation=value["revocation_generation"],
            safe_mode_generation=value["safe_mode_generation"],
            valid_grants=valid_grants,
            seen_bundle_ids=seen_bundle_ids,
            seen_envelopes=seen_envelopes,
            seen_decisions=seen_decisions,
        )
    return copy.deepcopy(value)


class ProductionAuthorityDecisionAdapter(CanonicalAuthorityDecisionAdapter):
    """v1 transport/provenance verifier plus structurally self-contained source v2."""

    def _validate_manifest(self, value: Any) -> dict:
        manifest = validate_source_manifest_structure(value)

        # For populated snapshots, reuse the independently audited v1 decision,
        # membership, actor, grant and generation validator. canonical_main is
        # supplied by the separately verified anchor, not self-embedded in the
        # content-addressed manifest.
        if manifest["bundles"]:
            compat = {
                "schema_version": "MULTIVERSE_R1_STAGE1_CANONICAL_AUTHORITY_MANIFEST_v1",
                "status": manifest["status"],
                "canonical_authority": manifest["canonical_authority"],
                "authority_scope": manifest["authority_scope"],
                "canonical_main": self.anchor.canonical_main,
                "policy_generation": manifest["policy_generation"],
                "policy_digest": manifest["policy_digest"],
                "revocation_generation": manifest["revocation_generation"],
                "safe_mode_generation": manifest["safe_mode_generation"],
                "safe_mode_active": manifest["safe_mode_active"],
                "valid_grant_refs": manifest["valid_grant_refs"],
                "trusted_clock_source": manifest["trusted_clock_source"],
                "canonical_main_is_complete_authority_freshness_barrier": True,
                "bundles": manifest["bundles"],
            }
            super()._validate_manifest(compat)
        return manifest


def _task_id(candidate_id: str, docs_hash: str) -> str:
    raw = json.dumps(
        f"source-review:{candidate_id}:{docs_hash}",
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "task-" + hashlib.sha256(raw).hexdigest()[:16]


def _decision(
    *,
    did: str,
    actor: str,
    operation: str,
    target: str,
    scope: str,
    grant: str,
    revocation_generation: int,
    safe_mode_generation: int,
) -> dict:
    return {
        "authorization_decision_id": did,
        "policy_generation": POLICY_GENERATION,
        "policy_digest": EXPECTED_POLICY_DIGEST,
        "actor_role": "EXECUTION",
        "actor_instance": actor,
        "operation": operation,
        "target": target,
        "permission_class_requested": "P1_REVERSIBLE_INTERNAL_WRITE",
        "permission_ceiling": "P1_REVERSIBLE_INTERNAL_WRITE",
        "scope": {
            "operation": operation,
            "target": target,
            "data_exposure_scope": scope,
        },
        "data_exposure_scope": scope,
        "issued_at": "2026-08-22T00:00:00+00:00",
        "expires_at": "2026-08-23T00:00:00+00:00",
        "grant_ref": grant,
        "owner_gate_ref": None,
        "revocation_generation_seen": revocation_generation,
        "safe_mode_generation_seen": safe_mode_generation,
        "decision": "ALLOW",
        "reason_codes": ["SELFTEST_PREISSUED_SOURCE_V2"],
        "evidence_refs": ["selftest://source-v2"],
    }


def _root_manifest() -> dict:
    return {
        "schema_version": AUTHORITY_MANIFEST_SCHEMA_V2,
        "status": ACCEPTED_AUTHORITY_STATUS,
        "canonical_authority": True,
        "authority_scope": AUTHORITY_SCOPE,
        "policy_generation": POLICY_GENERATION,
        "policy": copy.deepcopy(EXPECTED_POLICY),
        "policy_digest": EXPECTED_POLICY_DIGEST,
        "revocation_generation": 1,
        "safe_mode_generation": 1,
        "safe_mode_active": True,
        "valid_grant_refs": [],
        "trusted_clock_source": TRUSTED_CLOCK_SOURCE,
        "freshness_barrier_mode": FRESHNESS_BARRIER_MODE,
        "external_authority_state_refs": [],
        "bundles": [],
    }


def selftest() -> None:
    root = _root_manifest()
    validate_source_manifest_structure(root)
    print("PRODUCTION_AUTHORITY_DENY_ALL_ROOT_VALID")

    bad = copy.deepcopy(root)
    bad["canonical_main"] = "1" * 40
    try:
        validate_source_manifest_structure(bad)
    except CanonicalAuthorityDenied as exc:
        assert str(exc) == "AUTHORITY_V2_MANIFEST_SCHEMA"
    else:
        raise AssertionError("self-referential canonical_main field must be rejected")
    print("PRODUCTION_AUTHORITY_CONTENT_ADDRESS_SELF_REFERENCE_REMOVED")

    bad = copy.deepcopy(root)
    bad["external_authority_state_refs"] = ["governance/other.json"]
    try:
        validate_source_manifest_structure(bad)
    except CanonicalAuthorityDenied as exc:
        assert str(exc) == "AUTHORITY_V2_EXTERNAL_AUTHORITY_STATE_PROHIBITED"
    else:
        raise AssertionError("external authority state must fail closed")
    print("PRODUCTION_AUTHORITY_EXTERNAL_STATE_REJECTED")

    bad = copy.deepcopy(root)
    bad["safe_mode_active"] = False
    try:
        validate_source_manifest_structure(bad)
    except CanonicalAuthorityDenied as exc:
        assert str(exc) == "AUTHORITY_V2_EMPTY_ROOT_REQUIRES_SAFE_MODE"
    else:
        raise AssertionError("empty root must remain Safe Mode ON")
    print("PRODUCTION_AUTHORITY_EMPTY_ROOT_SAFE_MODE_ENFORCED")

    bad = copy.deepcopy(root)
    bad["valid_grant_refs"] = ["grant-forbidden-with-empty-root"]
    try:
        validate_source_manifest_structure(bad)
    except CanonicalAuthorityDenied as exc:
        assert str(exc) == "AUTHORITY_V2_EMPTY_ROOT_REQUIRES_ZERO_GRANTS"
    else:
        raise AssertionError("empty root must carry zero grants")
    print("PRODUCTION_AUTHORITY_EMPTY_ROOT_ZERO_GRANTS_ENFORCED")

    bad = copy.deepcopy(root)
    bad["policy"]["max_terminal_tasks"] = 26
    try:
        validate_source_manifest_structure(bad)
    except CanonicalAuthorityDenied as exc:
        assert str(exc) == "AUTHORITY_V2_POLICY_SCOPE_DRIFT"
    else:
        raise AssertionError("policy widening must fail closed")
    print("PRODUCTION_AUTHORITY_POLICY_SCOPE_DRIFT_REJECTED")

    # Prove a future populated exact-envelope snapshot remains compatible with
    # the v1 audited bundle validator without embedding its own commit SHA.
    candidate_id = "candidate-selftest-v2"
    docs_hash = hashlib.sha256(b"source-v2-docs").hexdigest()
    worker = "worker-selftest-v2"
    router = "router-selftest-v2"
    grant = "grant-selftest-v2"
    envelope = {
        "schema_version": ENQUEUE_SCHEMA,
        "stage_id": STAGE_ID,
        "candidate_id": candidate_id,
        "docs_hash": docs_hash,
        "worker_id": worker,
        "requested_final_state": "REVIEWED_NO_ADMISSION",
        "verdict_reason": "selftest",
        "evidence_refs": ["selftest://source-v2-evidence"],
    }
    task = _task_id(candidate_id, docs_hash)
    enqueue = _decision(
        did="auth-v2-enqueue",
        actor=router,
        operation=ENQUEUE_OPERATION,
        target=ENQUEUE_TARGET,
        scope=ENQUEUE_SCOPE,
        grant=grant,
        revocation_generation=2,
        safe_mode_generation=2,
    )
    specs = {
        "inspect": ("R1_SOURCE_CACHE_INSPECT_OR_STAGE", f"source-candidate:{candidate_id}", "PUBLIC_TERMS_METADATA_ONLY"),
        "lease": ("R1_TASK_ACQUIRE_LEASE", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "checkpoint": ("R1_TASK_CHECKPOINT", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "failure": ("R1_TASK_RECORD_FAILURE", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "commit": ("R1_SOURCE_REVIEW_COMMIT", f"task:{task}", "PUBLIC_TERMS_METADATA_ONLY"),
    }
    operations = {
        key: _decision(
            did=f"auth-v2-{key}",
            actor=worker,
            operation=operation,
            target=target,
            scope=scope,
            grant=grant,
            revocation_generation=2,
            safe_mode_generation=2,
        )
        for key, (operation, target, scope) in specs.items()
    }
    bundle = {
        "bundle_id": "bundle-selftest-v2",
        "envelope_digest": _sha256_json(envelope),
        "enqueue_actor_role": "EXECUTION",
        "enqueue_actor_instance": router,
        "worker_actor_role": "EXECUTION",
        "worker_actor_instance": worker,
        "enqueue_decision": enqueue,
        "operation_decisions": operations,
        "decision_payload_digest": _decision_digest(enqueue, operations),
    }
    populated = _root_manifest()
    populated["revocation_generation"] = 2
    populated["safe_mode_generation"] = 2
    populated["safe_mode_active"] = False
    populated["valid_grant_refs"] = [grant]
    populated["bundles"] = [bundle]
    validate_source_manifest_structure(populated)

    anchor = VerifiedCanonicalAuthorityAnchor(
        activation_receipt_ref="selftest://activation-v2",
        activation_receipt_sha256=hashlib.sha256(b"activation-v2").hexdigest(),
        canonical_main="1" * 40,
        authority_manifest_commit="1" * 40,
        authority_manifest_path="governance/selftest-v2.json",
        authority_manifest_blob_sha="2" * 40,
        authority_manifest_sha256=hashlib.sha256(b"manifest-v2").hexdigest(),
        authority_manifest_status=ACCEPTED_AUTHORITY_STATUS,
        authority_scope=AUTHORITY_SCOPE,
        policy_generation=POLICY_GENERATION,
        policy_digest=EXPECTED_POLICY_DIGEST,
        revocation_generation=2,
        safe_mode_generation=2,
        trusted_clock_source=TRUSTED_CLOCK_SOURCE,
        canonical_main_is_complete_authority_freshness_barrier=True,
        verified_from_immutable_activation_receipt=True,
    )
    adapter = object.__new__(ProductionAuthorityDecisionAdapter)
    adapter.anchor = anchor
    adapter._validate_manifest(populated)
    print("PRODUCTION_AUTHORITY_POPULATED_V2_REUSES_AUDITED_V1_GUARD")

    assert EXPECTED_POLICY_DIGEST == "30695c878c200aaa5f592fa13b1e8b119f5f3caa65cefa571daf9b76386c033d"
    print("PRODUCTION_AUTHORITY_STRUCTURAL_FRESHNESS_BARRIER_PASS")
    print("PRODUCTION_AUTHORITY_ROOT_ALLOW_BUNDLES=0")
    print("PRODUCTION_AUTHORITY_ROOT_SAFE_MODE=true")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    print("PRODUCTION_AUTHORITY_SOURCE_V2_SELFTEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--validate-source")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    if args.validate_source:
        value = json.loads(Path(args.validate_source).read_text())
        validate_source_manifest_structure(value)
        print("PRODUCTION_AUTHORITY_SOURCE_FILE_VALID")
        return 0
    parser.error("use --selftest or --validate-source")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
