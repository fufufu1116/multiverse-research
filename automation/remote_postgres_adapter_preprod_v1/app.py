"""Bounded PRE_PRODUCTION remote validation workload for the adopted PostgreSQL adapter.

This module is repository-only preparation until a separate Owner execution authority is
granted. All non-secret authority gates are validated before psycopg is imported or the
DATABASE_URL environment variable is read.
"""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from automation.runtime_postgres_adapter_v1.postgres_adapter import (
    PostgresControlViolation,
    PostgresDistributedControlStore,
    RuntimeIdentity,
)

SCHEMA = "MULTIVERSE_REMOTE_POSTGRES_ADAPTER_PREPROD_EVIDENCE_v1"
TARGET_CLASS = "RENDER_PREPRODUCTION_POSTGRES_ADAPTER_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
EXPECTED_POSTGRES_ID = "dpg-dadou0on74is73b09570-a"
EXPECTED_RUNTIME_ID = "mv-runtime-postgres-adapter-preprod-v1"
EXECUTION_AUTHORITY = "OWNER_AUTHORIZED_REMOTE_POSTGRES_ADAPTER_PREPROD_V1"
PROOF_CEILING = "REMOTE_POSTGRES_ADAPTER_PREPRODUCTION_NO_EFFECT_EVIDENCE_ONLY"
RUNTIME = "OFF"
LEASE_TTL_SECONDS = 2
REQUEST_KEY = "remote-postgres-adapter-noeffect-request-v1"
FINAL_EVIDENCE_CHECKPOINT = "remote:final_evidence"
PAYLOAD = {"kind": "synthetic_no_effect", "version": 1}
CONFLICT_PAYLOAD = {"kind": "synthetic_no_effect", "version": 2}

STATE: dict[str, Any] = {
    "ready": False,
    "database_bound": False,
    "execution_authorized": False,
    "complete": False,
    "last_error": None,
    "evidence": None,
}


class RemoteExecutionViolation(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _required(name: str, env: Any) -> str:
    value = env.get(name)
    if value is None or value == "":
        raise RemoteExecutionViolation(f"MISSING_{name}")
    return value


def validate_nonsecret_environment(env: dict[str, str] | None = None) -> dict[str, str]:
    # Do not copy the whole process environment: only named non-secret gates are read here.
    source = os.environ if env is None else env

    exact = {
        "MULTIVERSE_TARGET_CLASS": TARGET_CLASS,
        "MULTIVERSE_ENVIRONMENT_CLASS": ENVIRONMENT_CLASS,
        "MULTIVERSE_REMOTE_POSTGRES_EXECUTION_AUTHORITY": EXECUTION_AUTHORITY,
        "MULTIVERSE_RUNTIME": RUNTIME,
        "MULTIVERSE_LIVE_BUSINESS_EFFECT": "false",
        "MULTIVERSE_PROTECTED_KEIRIN_DATA": "false",
        "MULTIVERSE_PRODUCTION_CREDENTIALS": "false",
        "MULTIVERSE_INCREMENTAL_SPEND_USD": "0",
        "MULTIVERSE_EXPECTED_POSTGRES_ID": EXPECTED_POSTGRES_ID,
        "MULTIVERSE_RUNTIME_ID": EXPECTED_RUNTIME_ID,
    }

    for key, expected in exact.items():
        actual = _required(key, source)
        if actual != expected:
            raise RemoteExecutionViolation(f"{key}_MISMATCH")

    return exact


def build_connection_factory() -> Callable[[], Any]:
    # main() validates all non-secret authority gates before this function is reachable.
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RemoteExecutionViolation("DATABASE_URL_MISSING")

    import psycopg

    def connect() -> Any:
        return psycopg.connect(database_url)

    return connect


def expect_control_violation(code: str, fn: Callable[[], Any]) -> None:
    try:
        fn()
    except PostgresControlViolation as exc:
        if exc.code != code:
            raise RemoteExecutionViolation(
                f"EXPECTED_{code}_GOT_{exc.code}"
            ) from exc
        return
    raise RemoteExecutionViolation(f"EXPECTED_{code}_BUT_SUCCEEDED")


def run_bounded_drill(
    store: PostgresDistributedControlStore,
    *,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    store.initialize_schema()

    # If a completed bounded drill already exists, a provider restart must not replay writes.
    recovered = store.get_checkpoint(FINAL_EVIDENCE_CHECKPOINT)
    if recovered is not None and recovered.value.get("complete") is True:
        evidence = dict(recovered.value)
        evidence["recovered_after_restart"] = True
        return evidence

    identity_a = RuntimeIdentity("remote-worker-a", "remote-instance-a")
    identity_b = RuntimeIdentity("remote-worker-b", "remote-instance-b")

    lease_a = store.acquire_lease(
        identity_a,
        ttl_seconds=LEASE_TTL_SECONDS,
    )

    checkpoint_a = store.checkpoint(
        identity_a,
        lease_a,
        "remote:last_cycle",
        {"cursor": 1, "source": "synthetic"},
    )

    digest = store.payload_digest(PAYLOAD)
    conflict_digest = store.payload_digest(CONFLICT_PAYLOAD)

    first = store.reserve_operation(
        identity_a,
        lease_a,
        REQUEST_KEY,
        digest,
    )
    if not first.applied or first.duplicate:
        raise RemoteExecutionViolation("FIRST_OPERATION_NOT_APPLIED")

    duplicate_a = store.reserve_operation(
        identity_a,
        lease_a,
        REQUEST_KEY,
        digest,
    )
    if duplicate_a.applied or not duplicate_a.duplicate:
        raise RemoteExecutionViolation("SAME_OWNER_DUPLICATE_NOT_SUPPRESSED")

    expect_control_violation(
        "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
        lambda: store.reserve_operation(
            identity_a,
            lease_a,
            REQUEST_KEY,
            conflict_digest,
        ),
    )

    readiness_a = store.readiness(identity_a, lease_a)
    if readiness_a["ready"] is not False:
        raise RemoteExecutionViolation("READINESS_A_UNEXPECTEDLY_TRUE")

    sleeper(LEASE_TTL_SECONDS + 1)

    lease_b = store.acquire_lease(
        identity_b,
        ttl_seconds=LEASE_TTL_SECONDS,
    )

    if lease_b.fence_token <= lease_a.fence_token:
        raise RemoteExecutionViolation("FENCE_DID_NOT_INCREASE")

    expect_control_violation(
        "STALE_OWNER",
        lambda: store.assert_current(identity_a, lease_a),
    )

    prior_checkpoint = store.get_checkpoint("remote:last_cycle")
    if prior_checkpoint is None or prior_checkpoint.value.get("cursor") != 1:
        raise RemoteExecutionViolation("CHECKPOINT_NOT_DURABLE")

    checkpoint_b = store.checkpoint(
        identity_b,
        lease_b,
        "remote:last_cycle",
        {"cursor": 2, "resumed_from": 1, "source": "synthetic"},
    )

    duplicate_b = store.reserve_operation(
        identity_b,
        lease_b,
        REQUEST_KEY,
        digest,
    )
    if duplicate_b.applied or not duplicate_b.duplicate:
        raise RemoteExecutionViolation("CROSS_OWNER_DUPLICATE_NOT_SUPPRESSED")

    readiness_b = store.readiness(identity_b, lease_b)
    if readiness_b["ready"] is not False:
        raise RemoteExecutionViolation("READINESS_B_UNEXPECTEDLY_TRUE")

    evidence = {
        "schema": SCHEMA,
        "target_class": TARGET_CLASS,
        "environment_class": ENVIRONMENT_CLASS,
        "postgres_id": EXPECTED_POSTGRES_ID,
        "runtime_id": EXPECTED_RUNTIME_ID,
        "database_bound": True,
        "execution_authorized": True,
        "complete": True,
        "recovered_after_restart": False,
        "lease": {
            "worker_a_fence": lease_a.fence_token,
            "worker_b_fence": lease_b.fence_token,
            "fence_increased": lease_b.fence_token > lease_a.fence_token,
            "stale_owner_rejected": True,
        },
        "checkpoint": {
            "first_fence": checkpoint_a.fence_token,
            "second_fence": checkpoint_b.fence_token,
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
            "activation_ready": False,
            "kill_switch_engaged": True,
            "provider_effect_adapter_enabled": False,
            "runtime_activation_bridge_enabled": False,
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
        "proof_ceiling": PROOF_CEILING,
        "runtime": RUNTIME,
    }

    # Durable evidence makes provider restarts non-replaying and recoverable.
    store.checkpoint(
        identity_b,
        lease_b,
        FINAL_EVIDENCE_CHECKPOINT,
        evidence,
    )

    return evidence


def execute_remote_validation() -> None:
    try:
        validate_nonsecret_environment()
        STATE["execution_authorized"] = True

        factory = build_connection_factory()
        store = PostgresDistributedControlStore(
            runtime_id=EXPECTED_RUNTIME_ID,
            connection_factory=factory,
        )

        evidence = run_bounded_drill(store)
        STATE["database_bound"] = True
        STATE["evidence"] = evidence
        STATE["complete"] = bool(evidence.get("complete"))
        STATE["ready"] = True

    except Exception as exc:
        STATE["last_error"] = f"{type(exc).__name__}:{exc}"
        STATE["ready"] = False


class Handler(BaseHTTPRequestHandler):
    server_version = "MULTIVERSE-RemotePostgresAdapter-NoEffect/1"

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "runtime": RUNTIME,
                    "target_class": TARGET_CLASS,
                },
            )
            return

        if self.path == "/ready":
            self._send_json(
                200 if STATE["ready"] else 503,
                {
                    "ready": STATE["ready"],
                    "database_bound": STATE["database_bound"],
                    "execution_authorized": STATE["execution_authorized"],
                    "complete": STATE["complete"],
                    "last_error": STATE["last_error"],
                    "runtime": RUNTIME,
                },
            )
            return

        if self.path == "/evidence":
            if STATE["evidence"] is None:
                self._send_json(
                    503,
                    {
                        "error": STATE["last_error"] or "evidence_not_ready",
                        "runtime": RUNTIME,
                    },
                )
            else:
                self._send_json(200, dict(STATE["evidence"]))
            return

        self._send_json(404, {"error": "not_found", "runtime": RUNTIME})

    def _deny(self) -> None:
        self._send_json(
            403,
            {
                "error": "state_changes_disabled_over_http",
                "runtime": RUNTIME,
            },
        )

    def do_POST(self) -> None:
        self._deny()

    def do_PUT(self) -> None:
        self._deny()

    def do_PATCH(self) -> None:
        self._deny()

    def do_DELETE(self) -> None:
        self._deny()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            json.dumps(
                {
                    "component": "http",
                    "message": fmt % args,
                    "runtime": RUNTIME,
                },
                sort_keys=True,
            ),
            flush=True,
        )


def main() -> None:
    # Crucial ordering: authority validation happens before DATABASE_URL read / psycopg import.
    validate_nonsecret_environment()

    thread = threading.Thread(
        target=execute_remote_validation,
        name="remote-postgres-adapter-validation",
        daemon=True,
    )
    thread.start()

    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
