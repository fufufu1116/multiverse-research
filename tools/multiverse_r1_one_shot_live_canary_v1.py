#!/usr/bin/env python3
"""Owner-gated one-shot R1 live canary. Dormant unless an exact trigger is supplied."""
import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from multiverse_r1_auth_v1 import AuthorizationRuntime
from multiverse_r1_engine_v1 import R1Engine
from multiverse_r1_state_v1 import PersistentStore

GATE_PATH = "governance/MULTIVERSE_R1_OWNER_GATE_ONE_SHOT_LIVE_CANARY_20260821_v1.json"
AUTH_PATH = "governance/MULTIVERSE_R1_LIVE_CANARY_AUTHORIZATION_FIXTURE_20260821_v1.json"
CONTRACT_PATH = "governance/MULTIVERSE_R1_ONE_SHOT_LIVE_CANARY_CONTRACT_20260821_v1.json"
TRIGGER_RECORD = "MULTIVERSE_R1_LIVE_CANARY_TRIGGER_ONCE_20260821_v1"
TRIGGER_NONCE = "R1-LIVE-CANARY-20260821-ONE-SHOT-v1"
DOC_MATERIAL = "MULTIVERSE_R1_LIVE_CANARY_SYNTHETIC_LOCAL_INPUT_v1"


def _load(path):
    return json.loads(Path(path).read_text())


def _require(condition, code):
    if not condition:
        raise RuntimeError(code)


def _runtime(fixture, actor, now):
    identity = fixture["runtime_identity"]
    return AuthorizationRuntime(
        policy_generation=identity["policy_generation"],
        policy_digest=identity["policy_digest"],
        revocation_generation=identity["revocation_generation"],
        safe_mode_generation=identity["safe_mode_generation"],
        now=now,
        actor_role="EXECUTION",
        actor_instance=actor,
        valid_grant_refs=frozenset(identity["valid_grant_refs"]),
        expected_owner_gate_ref=None,
        safe_mode_active=False,
    )


def _validate_envelope(trigger, canonical_main):
    gate = _load(trigger["owner_gate_receipt"])
    contract = _load(trigger["contract"])
    fixture = _load(trigger["authorization_fixture"])

    _require(trigger["record"] == TRIGGER_RECORD, "TRIGGER_RECORD_MISMATCH")
    _require(trigger["status"] == "ARMED_FOR_SINGLE_OWNER_GATED_CANARY_EXECUTION", "TRIGGER_NOT_ARMED")
    _require(trigger["single_use_nonce"] == TRIGGER_NONCE, "TRIGGER_NONCE_MISMATCH")
    _require(trigger["max_executions"] == 1, "TRIGGER_EXECUTION_COUNT_NOT_ONE")
    _require(trigger["expected_canonical_main"] == canonical_main, "TRIGGER_CANONICAL_MAIN_MISMATCH")
    _require(len(canonical_main) == 40 and all(c in "0123456789abcdef" for c in canonical_main.lower()), "CANONICAL_MAIN_INVALID")

    _require(gate["record"] == "MULTIVERSE_R1_OWNER_GATE_ONE_SHOT_LIVE_CANARY_20260821_v1", "OWNER_GATE_RECORD_MISMATCH")
    _require(gate["status"] == "OWNER_APPROVED_SCOPE_SPECIFIC_ONE_SHOT_LIVE_CANARY_ONLY", "OWNER_GATE_STATUS_MISMATCH")
    _require(gate["execution_limits"]["max_live_canary_executions"] == 1, "OWNER_GATE_COUNT_MISMATCH")
    _require(gate["execution_limits"]["automatic_retry_authorized"] is False, "OWNER_GATE_RETRY_MUST_BE_FALSE")
    _require(gate["execution_limits"]["application_network_access_authorized"] is False, "OWNER_GATE_NETWORK_MUST_BE_FALSE")
    _require(gate["execution_limits"]["full_runtime_activation_authorized"] is False, "OWNER_GATE_FULL_RUNTIME_MUST_BE_FALSE")

    _require(contract["status"] in {"DORMANT_LIVE_CANARY_FRAMEWORK_CANDIDATE_PENDING_INDEPENDENT_REVIEW", "CANONICAL_DORMANT_ONE_SHOT_LIVE_CANARY_FRAMEWORK"}, "CONTRACT_STATUS_INVALID")
    _require(contract["one_shot_trigger"]["max_execution_count"] == 1, "CONTRACT_COUNT_MISMATCH")
    _require(contract["one_shot_trigger"]["automatic_retry"] is False, "CONTRACT_RETRY_MUST_BE_FALSE")
    _require(contract["runtime_authorization"]["owner_gate_reused_as_operation_grant"] is False, "OWNER_GATE_OPERATION_REUSE_FORBIDDEN")
    _require(contract["workload"]["network_source_collection"] is False, "CONTRACT_NETWORK_MUST_BE_FALSE")
    _require(contract["workload"]["persistent_business_state"] is False, "CONTRACT_PERSISTENT_BUSINESS_STATE_MUST_BE_FALSE")

    _require(fixture["status"] == "CANARY_FIXTURE_ONLY_NOT_PRODUCTION_AUTHORITY", "AUTH_FIXTURE_STATUS_INVALID")
    for decision in fixture["decisions"].values():
        _require(decision["owner_gate_ref"] is None, "OWNER_GATE_MUST_NOT_BE_OPERATION_GRANT")
        _require(decision["permission_class_requested"] in {"P0_READ_PUBLIC_OR_CANONICAL", "P1_REVERSIBLE_INTERNAL_WRITE"}, "CANARY_PERMISSION_CLASS_TOO_HIGH")
    return gate, contract, fixture


def execute_one_shot(trigger, canonical_main, now):
    _, _, fixture = _validate_envelope(trigger, canonical_main)
    meta = fixture["fixture"]
    docs_hash = hashlib.sha256(DOC_MATERIAL.encode()).hexdigest()
    _require(docs_hash == meta["docs_hash"], "CANARY_DOC_HASH_MISMATCH")

    router = "r1-live-canary-router"
    worker = "r1-live-canary-worker"
    reader = "r1-live-canary-reader"
    decisions = fixture["decisions"]

    with tempfile.TemporaryDirectory(prefix="multiverse-r1-live-canary-") as td:
        store = PersistentStore(Path(td))
        engine = R1Engine(store, canonical_main)

        task_id = engine.inspect_candidate(
            current_main=canonical_main,
            candidate_id=meta["candidate_id"],
            docs_hash=docs_hash,
            authorization=decisions["inspect"],
            auth_runtime=_runtime(fixture, router, now),
        )
        _require(task_id == meta["expected_task_id"], "CANARY_TASK_ID_MISMATCH")

        lease_epoch = engine.acquire_lease(
            current_main=canonical_main,
            task_id=task_id,
            worker_id=worker,
            now_tick=1,
            lease_ticks=20,
            authorization=decisions["acquire_lease"],
            auth_runtime=_runtime(fixture, worker, now),
        )
        engine.checkpoint(
            current_main=canonical_main,
            task_id=task_id,
            worker_id=worker,
            lease_epoch=lease_epoch,
            now_tick=2,
            checkpoint_ref="live-canary-checkpoint-v1",
            authorization=decisions["checkpoint"],
            auth_runtime=_runtime(fixture, worker, now),
        )
        receipt = engine.commit_review(
            current_main=canonical_main,
            task_id=task_id,
            worker_id=worker,
            lease_epoch=lease_epoch,
            now_tick=3,
            committed_state="REVIEWED_NO_ADMISSION",
            verdict_reason="ONE_SHOT_SYNTHETIC_LOCAL_CANARY_ONLY",
            evidence_refs=["SYNTHETIC_LOCAL_CANARY_FIXTURE_ONLY"],
            authorization=decisions["commit"],
            auth_runtime=_runtime(fixture, worker, now),
        )
        read_back = engine.read_receipt(
            idempotency_key=meta["idempotency_key"],
            authorization=decisions["read_receipt"],
            auth_runtime=_runtime(fixture, reader, now),
        )
        _require(read_back == receipt, "CANARY_RECEIPT_READBACK_MISMATCH")
        _require(receipt["canonical_main"] == canonical_main, "CANARY_RECEIPT_CANONICAL_MAIN_MISMATCH")
        _require(receipt["operation_owner_gate_ref"] is None, "OWNER_GATE_REUSED_AS_OPERATION_GRANT")

        state = store.read()
        _require(len(state["receipts_by_idempotency"]) == 1, "CANARY_RECEIPT_COUNT_NOT_ONE")
        _require(state["tasks"][task_id]["dead_letter_reason"] is None, "CANARY_UNEXPECTED_DEAD_LETTER")
        _require(state["cache"][meta["candidate_id"]]["audit_state"] == "REVIEWED_NO_ADMISSION", "CANARY_FINAL_STATE_MISMATCH")

        return {
            "task_id": task_id,
            "receipt_id": receipt["receipt_id"],
            "canonical_main": canonical_main,
            "lease_epoch": lease_epoch,
            "state_generation": state["generation"],
        }


def _selftest():
    trigger = {
        "record": TRIGGER_RECORD,
        "status": "ARMED_FOR_SINGLE_OWNER_GATED_CANARY_EXECUTION",
        "single_use_nonce": TRIGGER_NONCE,
        "max_executions": 1,
        "expected_canonical_main": "f" * 40,
        "owner_gate_receipt": GATE_PATH,
        "authorization_fixture": AUTH_PATH,
        "contract": CONTRACT_PATH,
    }
    result = execute_one_shot(trigger, "f" * 40, datetime.fromisoformat("2026-08-21T06:30:00+00:00"))
    _require(result["canonical_main"] == "f" * 40, "SELFTEST_CANONICAL_MISMATCH")
    print("OWNER_GATE_OPERATION_GRANT_REUSE=false")
    print("CANARY_SOURCE_COLLECTION_PERFORMED=false")
    print("CANARY_EXTERNAL_CONTACT_PERFORMED=false")
    print("CANARY_REPOSITORY_BUSINESS_WRITE_PERFORMED=false")
    print("CANARY_FULL_RUNTIME_ACTIVATION_PERFORMED=false")
    print("MULTIVERSE_R1_ONE_SHOT_LIVE_CANARY_FRAMEWORK_SELFTEST_PASS")
    return 0


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--selftest", action="store_true")
    group.add_argument("--run-once", action="store_true")
    parser.add_argument("--trigger")
    parser.add_argument("--canonical-main")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()
    if args.run_once:
        _require(bool(args.trigger), "TRIGGER_PATH_REQUIRED")
        _require(bool(args.canonical_main), "CANONICAL_MAIN_REQUIRED")
        trigger = _load(args.trigger)
        result = execute_one_shot(trigger, args.canonical_main, datetime.now(timezone.utc))
        print(json.dumps(result, sort_keys=True))
        print("R1_LIVE_CANARY_ONE_SHOT_PASS")
        print("CANARY_SOURCE_COLLECTION_PERFORMED=false")
        print("CANARY_EXTERNAL_CONTACT_PERFORMED=false")
        print("CANARY_REPOSITORY_BUSINESS_WRITE_PERFORMED=false")
        print("CANARY_FULL_RUNTIME_ACTIVATION_PERFORMED=false")
        return 0

    print("R1_LIVE_CANARY_FRAMEWORK_DORMANT_NO_TRIGGER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
