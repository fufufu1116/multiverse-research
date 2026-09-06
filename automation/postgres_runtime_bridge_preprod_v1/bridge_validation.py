"""Repository-prepared no-effect validation for PreparedPostgresRuntimeBridge."""
from __future__ import annotations

import time
from typing import Any, Callable

from automation.runtime_postgres_adapter_v1.postgres_adapter import (
    PostgresControlViolation,
    PostgresDistributedControlStore,
)
from automation.runtime_postgres_adapter_v1.postgres_runtime_bridge import (
    PreparedPostgresRuntimeBridge,
)

SCHEMA = "MULTIVERSE_POSTGRES_RUNTIME_BRIDGE_PREPROD_EVIDENCE_v1"
PROOF_CEILING = "POSTGRES_RUNTIME_BRIDGE_PREPRODUCTION_VALIDATION_PREPARATION_ONLY"
EXECUTION_STATE = "BRIDGE_REMOTE_VALIDATION_NOT_AUTHORIZED"
REMOTE_PROOF_CEILING = "POSTGRES_RUNTIME_BRIDGE_PREPRODUCTION_NO_EFFECT_EVIDENCE_ONLY"
RUNTIME = "OFF"
RUNTIME_ID = "mv-runtime-postgres-bridge-preprod-v1"
WORKER_A_TTL_SECONDS = 3
WORKER_B_TTL_SECONDS = 30
REQUEST_KEY = "postgres-runtime-bridge-noeffect-request-v1"
FINAL_EVIDENCE_CHECKPOINT = "bridge:final_evidence"
PAYLOAD = {"kind": "synthetic_bridge_no_effect", "version": 1}
CONFLICT_PAYLOAD = {"kind": "synthetic_bridge_no_effect", "version": 2}


def _expect_violation(code: str, fn: Callable[[], Any]) -> None:
    try:
        fn()
    except PostgresControlViolation as exc:
        if exc.code != code:
            raise RuntimeError(f"EXPECTED_{code}_GOT_{exc.code}") from exc
        return
    raise RuntimeError(f"EXPECTED_{code}_BUT_SUCCEEDED")


def run_bridge_validation(
    store: PostgresDistributedControlStore,
    *,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    recovered = store.get_checkpoint(FINAL_EVIDENCE_CHECKPOINT)
    if recovered is not None and recovered.value.get("complete") is True:
        evidence = dict(recovered.value)
        evidence["recovered_after_restart"] = True
        return evidence

    bridge = PreparedPostgresRuntimeBridge(store)

    session_a = bridge.prepare_session(
        "bridge-worker-a",
        "bridge-instance-a",
        ttl_seconds=WORKER_A_TTL_SECONDS,
    )
    checkpoint_a = bridge.checkpoint(
        session_a,
        "bridge:last_cycle",
        {"cursor": 1, "source": "synthetic_bridge"},
    )

    first = bridge.reserve_inert_operation(session_a, REQUEST_KEY, PAYLOAD)
    if not first["applied"] or first["duplicate"]:
        raise RuntimeError("FIRST_BRIDGE_OPERATION_NOT_APPLIED")
    if first["external_effect_executed"] is not False:
        raise RuntimeError("EXTERNAL_EFFECT_FLAG_NOT_FALSE")

    duplicate_a = bridge.reserve_inert_operation(session_a, REQUEST_KEY, PAYLOAD)
    if duplicate_a["applied"] or not duplicate_a["duplicate"]:
        raise RuntimeError("SAME_OWNER_BRIDGE_DUPLICATE_NOT_SUPPRESSED")

    _expect_violation(
        "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
        lambda: bridge.reserve_inert_operation(session_a, REQUEST_KEY, CONFLICT_PAYLOAD),
    )

    readiness_a = bridge.readiness(session_a)
    if readiness_a["ready"] is not False:
        raise RuntimeError("BRIDGE_READINESS_A_UNEXPECTEDLY_TRUE")

    sleeper(WORKER_A_TTL_SECONDS + 1)

    session_b = bridge.prepare_session(
        "bridge-worker-b",
        "bridge-instance-b",
        ttl_seconds=WORKER_B_TTL_SECONDS,
    )
    if session_b.lease.fence_token <= session_a.lease.fence_token:
        raise RuntimeError("BRIDGE_FENCE_DID_NOT_INCREASE")

    _expect_violation(
        "STALE_OWNER",
        lambda: bridge.renew_session(session_a, ttl_seconds=10),
    )

    prior = store.get_checkpoint("bridge:last_cycle")
    if prior is None or prior.value.get("cursor") != 1:
        raise RuntimeError("BRIDGE_CHECKPOINT_NOT_DURABLE")

    checkpoint_b = bridge.checkpoint(
        session_b,
        "bridge:last_cycle",
        {"cursor": 2, "resumed_from": 1, "source": "synthetic_bridge"},
    )

    duplicate_b = bridge.reserve_inert_operation(session_b, REQUEST_KEY, PAYLOAD)
    if duplicate_b["applied"] or not duplicate_b["duplicate"]:
        raise RuntimeError("CROSS_OWNER_BRIDGE_DUPLICATE_NOT_SUPPRESSED")

    readiness_b = bridge.readiness(session_b)
    if readiness_b["ready"] is not False:
        raise RuntimeError("BRIDGE_READINESS_B_UNEXPECTEDLY_TRUE")

    for raw in (readiness_a, readiness_b):
        if raw["kill_switch_engaged"] is not True:
            raise RuntimeError("KILL_SWITCH_NOT_ENGAGED")
        if raw["provider_effect_adapter_enabled"] is not False:
            raise RuntimeError("PROVIDER_EFFECT_NOT_DISABLED")
        if raw["runtime_activation_bridge_enabled"] is not False:
            raise RuntimeError("ACTIVATION_BRIDGE_NOT_DISABLED")
        if raw["activation_ready"] is not False:
            raise RuntimeError("ACTIVATION_READY_NOT_FALSE")
        if raw["runtime"] != RUNTIME:
            raise RuntimeError("RUNTIME_NOT_OFF")

    evidence = {
        "schema": SCHEMA,
        "proof_ceiling": REMOTE_PROOF_CEILING,
        "runtime": RUNTIME,
        "runtime_id": RUNTIME_ID,
        "complete": True,
        "recovered_after_restart": False,
        "bridge_class": "PreparedPostgresRuntimeBridge",
        "lease": {
            "worker_a_fence": session_a.lease.fence_token,
            "worker_b_fence": session_b.lease.fence_token,
            "fence_increased": session_b.lease.fence_token > session_a.lease.fence_token,
            "stale_owner_rejected": True,
        },
        "checkpoint": {
            "first_fence": checkpoint_a["fence_token"],
            "second_fence": checkpoint_b["fence_token"],
            "resume_visible": True,
            "final_evidence_checkpoint_written": True,
        },
        "idempotency": {
            "first_applied": True,
            "same_owner_duplicate_suppressed": True,
            "cross_owner_duplicate_suppressed": True,
            "payload_conflict_rejected": True,
            "external_effect_executed": False,
        },
        "readiness": {
            "worker_a_ready": False,
            "worker_b_ready": False,
            "kill_switch_engaged": True,
            "provider_effect_adapter_enabled": False,
            "runtime_activation_bridge_enabled": False,
            "activation_ready": False,
        },
        "authority": {
            "production_credentials": False,
            "protected_keirin_data": False,
            "live_business_effect": False,
            "additional_spend_above_usd_0": False,
            "provider_effect_adapter_enablement": False,
            "runtime_activation_bridge_enablement": False,
            "runtime_activation": False,
        },
    }

    bridge.checkpoint(session_b, FINAL_EVIDENCE_CHECKPOINT, evidence)
    return evidence
