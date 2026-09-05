from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import psycopg


TARGET_CLASS = "RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
PROOF_CEILING = "REMOTE_MULTI_HOST_PREPRODUCTION_RENDER_NO_EFFECT_EVIDENCE_ONLY"
RUNTIME = "OFF"

WORKERS = ("worker-a", "worker-b")
EXPECTED_POSTGRES_ID = "dpg-dadou0on74is73b09570-a"
DRILL_ID = "remote-multihost-render-v1-20260906"
LEASE_TTL_SECONDS = 30
WAIT_TIMEOUT_SECONDS = 240

PAYLOAD = b"MULTIVERSE_REMOTE_MULTIHOST_NO_EFFECT_PAYLOAD_v1"
CONFLICT_PAYLOAD = b"MULTIVERSE_REMOTE_MULTIHOST_DIFFERENT_PAYLOAD_v1"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()
CONFLICT_SHA256 = hashlib.sha256(CONFLICT_PAYLOAD).hexdigest()
REQUEST_KEY = "remote-multihost-idempotency-key-v1"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
WORKER_ID = os.environ.get("MULTIVERSE_WORKER_ID", "")
RENDER_SERVICE_ID = os.environ.get("MULTIVERSE_RENDER_SERVICE_ID", "")
RENDER_INSTANCE_ID = (
    os.environ.get("RENDER_INSTANCE_ID")
    or os.environ.get("HOSTNAME")
    or "UNKNOWN_INSTANCE"
)

STATE: dict[str, Any] = {
    "ready": False,
    "database_bound": False,
    "execution_authorized": False,
    "worker_id": WORKER_ID,
    "render_service_id": RENDER_SERVICE_ID,
    "render_instance_id": RENDER_INSTANCE_ID,
    "boot_count": None,
    "last_error": None,
}


class DrillViolation(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require_env(name: str, expected: str) -> None:
    actual = os.environ.get(name)
    if actual != expected:
        raise RuntimeError(f"ENV_BINDING_MISMATCH:{name}")


def validate_environment() -> None:
    if WORKER_ID not in WORKERS:
        raise RuntimeError("WORKER_ID_INVALID")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL_MISSING")

    if not RENDER_SERVICE_ID:
        raise RuntimeError("RENDER_SERVICE_ID_MISSING")

    _require_env("MULTIVERSE_ENVIRONMENT_CLASS", ENVIRONMENT_CLASS)
    _require_env("MULTIVERSE_TARGET_CLASS", TARGET_CLASS)
    _require_env("MULTIVERSE_MULTIHOST_EXECUTION_AUTHORIZED", "true")
    _require_env("MULTIVERSE_RUNTIME", "OFF")
    _require_env("MULTIVERSE_LIVE_BUSINESS_EFFECT", "false")
    _require_env("MULTIVERSE_PROTECTED_KEIRIN_DATA", "false")
    _require_env("MULTIVERSE_PRODUCTION_CREDENTIALS", "false")
    _require_env("MULTIVERSE_INCREMENTAL_SPEND_USD", "0")
    _require_env("MULTIVERSE_POSTGRES_ID", EXPECTED_POSTGRES_ID)
    _require_env("MULTIVERSE_DRILL_ID", DRILL_ID)


def db_connect():
    return psycopg.connect(DATABASE_URL, autocommit=False)


def _insert_event(cur, worker_id: str, event: str, **details: Any) -> None:
    cur.execute(
        """
        INSERT INTO mv_mh1_events
            (drill_id, worker_id, event, details)
        VALUES
            (%s, %s, %s, %s::jsonb)
        """,
        (DRILL_ID, worker_id, event, json.dumps(details, sort_keys=True)),
    )


def ensure_schema() -> None:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mv_mh1_control (
                    drill_id text PRIMARY KEY,
                    owner text,
                    fence_token bigint NOT NULL DEFAULT 0,
                    lease_expires_at timestamptz
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mv_mh1_operations (
                    drill_id text NOT NULL,
                    request_key text NOT NULL,
                    payload_sha256 text NOT NULL,
                    applied_by text NOT NULL,
                    fence_token bigint NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
                    PRIMARY KEY (drill_id, request_key)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mv_mh1_events (
                    id bigserial PRIMARY KEY,
                    drill_id text NOT NULL,
                    worker_id text NOT NULL,
                    event text NOT NULL,
                    details jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mv_mh1_workers (
                    drill_id text NOT NULL,
                    worker_id text NOT NULL,
                    boot_count bigint NOT NULL,
                    last_instance_id text NOT NULL,
                    last_service_id text NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
                    PRIMARY KEY (drill_id, worker_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mv_mh1_phase (
                    drill_id text PRIMARY KEY,
                    phase text NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
                )
                """
            )
            cur.execute(
                """
                INSERT INTO mv_mh1_control
                    (drill_id, owner, fence_token, lease_expires_at)
                VALUES
                    (%s, NULL, 0, NULL)
                ON CONFLICT (drill_id) DO NOTHING
                """,
                (DRILL_ID,),
            )
            cur.execute(
                """
                INSERT INTO mv_mh1_phase (drill_id, phase)
                VALUES (%s, 'INIT')
                ON CONFLICT (drill_id) DO NOTHING
                """,
                (DRILL_ID,),
            )
        conn.commit()


def register_boot() -> int:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mv_mh1_workers
                    (
                        drill_id,
                        worker_id,
                        boot_count,
                        last_instance_id,
                        last_service_id
                    )
                VALUES
                    (%s, %s, 1, %s, %s)
                ON CONFLICT (drill_id, worker_id)
                DO UPDATE SET
                    boot_count = mv_mh1_workers.boot_count + 1,
                    last_instance_id = EXCLUDED.last_instance_id,
                    last_service_id = EXCLUDED.last_service_id,
                    updated_at = clock_timestamp()
                RETURNING boot_count
                """,
                (
                    DRILL_ID,
                    WORKER_ID,
                    RENDER_INSTANCE_ID,
                    RENDER_SERVICE_ID,
                ),
            )
            boot_count = int(cur.fetchone()[0])
            _insert_event(
                cur,
                WORKER_ID,
                "worker_boot",
                boot_count=boot_count,
                instance_id=RENDER_INSTANCE_ID,
                service_id=RENDER_SERVICE_ID,
            )
        conn.commit()
    return boot_count


def get_phase() -> str:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT phase FROM mv_mh1_phase WHERE drill_id = %s",
                (DRILL_ID,),
            )
            row = cur.fetchone()
            return row[0] if row else "MISSING"


def set_phase(phase: str) -> None:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mv_mh1_phase
                SET phase = %s, updated_at = clock_timestamp()
                WHERE drill_id = %s
                """,
                (phase, DRILL_ID),
            )
            _insert_event(cur, WORKER_ID, "phase_set", phase=phase)
        conn.commit()


def worker_booted(worker_id: str) -> bool:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT boot_count
                FROM mv_mh1_workers
                WHERE drill_id = %s AND worker_id = %s
                """,
                (DRILL_ID, worker_id),
            )
            return cur.fetchone() is not None


def wait_until(predicate, label: str, timeout: int = WAIT_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(1)
    raise RuntimeError(f"WAIT_TIMEOUT:{label}")


def get_control() -> dict[str, Any]:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    owner,
                    fence_token,
                    lease_expires_at,
                    clock_timestamp()
                FROM mv_mh1_control
                WHERE drill_id = %s
                """,
                (DRILL_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("CONTROL_ROW_MISSING")
            return {
                "owner": row[0],
                "fence_token": int(row[1]),
                "lease_expires_at": row[2],
                "db_now": row[3],
            }


def acquire_lease(worker_id: str, ttl_seconds: int = LEASE_TTL_SECONDS) -> dict[str, Any]:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    owner,
                    fence_token,
                    lease_expires_at,
                    clock_timestamp()
                FROM mv_mh1_control
                WHERE drill_id = %s
                FOR UPDATE
                """,
                (DRILL_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("CONTROL_ROW_MISSING")

            owner, fence_token, lease_expires_at, db_now = row
            fence_token = int(fence_token)

            if (
                owner is not None
                and lease_expires_at is not None
                and db_now < lease_expires_at
            ):
                _insert_event(
                    cur,
                    worker_id,
                    "lease_rejected",
                    reason="LEASE_HELD",
                    current_owner=owner,
                    current_fence_token=fence_token,
                    lease_expires_at=lease_expires_at.isoformat(),
                    db_now=db_now.isoformat(),
                )
                conn.commit()
                raise DrillViolation("LEASE_HELD")

            new_token = fence_token + 1
            new_expiry = db_now + timedelta(seconds=ttl_seconds)

            cur.execute(
                """
                UPDATE mv_mh1_control
                SET
                    owner = %s,
                    fence_token = %s,
                    lease_expires_at = %s
                WHERE drill_id = %s
                """,
                (worker_id, new_token, new_expiry, DRILL_ID),
            )
            _insert_event(
                cur,
                worker_id,
                "lease_acquired",
                previous_owner=owner,
                previous_fence_token=fence_token,
                fence_token=new_token,
                lease_expires_at=new_expiry.isoformat(),
                db_now=db_now.isoformat(),
            )
        conn.commit()

    return {
        "owner": worker_id,
        "fence_token": new_token,
        "lease_expires_at": new_expiry,
    }


def mutate(
    worker_id: str,
    fence_token: int,
    request_key: str,
    payload_sha256: str,
) -> dict[str, Any]:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    owner,
                    fence_token,
                    lease_expires_at,
                    clock_timestamp()
                FROM mv_mh1_control
                WHERE drill_id = %s
                FOR UPDATE
                """,
                (DRILL_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("CONTROL_ROW_MISSING")

            owner, current_token, lease_expires_at, db_now = row
            current_token = int(current_token)

            if owner != worker_id:
                _insert_event(
                    cur,
                    worker_id,
                    "mutation_rejected",
                    reason="STALE_OWNER",
                    supplied_fence_token=fence_token,
                    current_owner=owner,
                    current_fence_token=current_token,
                )
                conn.commit()
                raise DrillViolation("STALE_OWNER")

            if current_token != fence_token:
                _insert_event(
                    cur,
                    worker_id,
                    "mutation_rejected",
                    reason="STALE_FENCE_TOKEN",
                    supplied_fence_token=fence_token,
                    current_owner=owner,
                    current_fence_token=current_token,
                )
                conn.commit()
                raise DrillViolation("STALE_FENCE_TOKEN")

            if lease_expires_at is None or db_now >= lease_expires_at:
                _insert_event(
                    cur,
                    worker_id,
                    "mutation_rejected",
                    reason="LEASE_EXPIRED",
                    supplied_fence_token=fence_token,
                    lease_expires_at=(
                        lease_expires_at.isoformat()
                        if lease_expires_at is not None
                        else None
                    ),
                    db_now=db_now.isoformat(),
                )
                conn.commit()
                raise DrillViolation("LEASE_EXPIRED")

            cur.execute(
                """
                SELECT payload_sha256
                FROM mv_mh1_operations
                WHERE drill_id = %s AND request_key = %s
                """,
                (DRILL_ID, request_key),
            )
            existing = cur.fetchone()

            if existing is not None:
                if existing[0] != payload_sha256:
                    _insert_event(
                        cur,
                        worker_id,
                        "mutation_rejected",
                        reason="IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
                        request_key=request_key,
                        supplied_payload_sha256=payload_sha256,
                        existing_payload_sha256=existing[0],
                    )
                    conn.commit()
                    raise DrillViolation("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")

                cur.execute(
                    """
                    SELECT count(*)
                    FROM mv_mh1_operations
                    WHERE drill_id = %s
                    """,
                    (DRILL_ID,),
                )
                count = int(cur.fetchone()[0])
                _insert_event(
                    cur,
                    worker_id,
                    "mutation_duplicate",
                    request_key=request_key,
                    payload_sha256=payload_sha256,
                    fence_token=fence_token,
                    simulated_effect_count=count,
                )
                conn.commit()
                return {
                    "applied": False,
                    "duplicate": True,
                    "simulated_effect_count": count,
                }

            cur.execute(
                """
                INSERT INTO mv_mh1_operations
                    (
                        drill_id,
                        request_key,
                        payload_sha256,
                        applied_by,
                        fence_token
                    )
                VALUES
                    (%s, %s, %s, %s, %s)
                """,
                (
                    DRILL_ID,
                    request_key,
                    payload_sha256,
                    worker_id,
                    fence_token,
                ),
            )
            cur.execute(
                """
                SELECT count(*)
                FROM mv_mh1_operations
                WHERE drill_id = %s
                """,
                (DRILL_ID,),
            )
            count = int(cur.fetchone()[0])
            _insert_event(
                cur,
                worker_id,
                "mutation_applied",
                request_key=request_key,
                payload_sha256=payload_sha256,
                fence_token=fence_token,
                simulated_effect_count=count,
            )
        conn.commit()

    return {
        "applied": True,
        "duplicate": False,
        "simulated_effect_count": count,
    }


def expect_violation(expected: str, fn) -> None:
    try:
        fn()
    except DrillViolation as exc:
        if exc.code != expected:
            raise RuntimeError(
                f"EXPECTED_{expected}_GOT_{exc.code}"
            ) from exc
        return
    raise RuntimeError(f"EXPECTED_{expected}_BUT_SUCCEEDED")


def wait_for_lease_expiry() -> None:
    def expired() -> bool:
        control = get_control()
        expiry = control["lease_expires_at"]
        return expiry is None or control["db_now"] >= expiry

    wait_until(expired, "lease_expiry")


def worker_a_first_boot() -> None:
    wait_until(lambda: worker_booted("worker-b"), "worker_b_booted")

    if get_phase() != "INIT":
        return

    lease_a = acquire_lease("worker-a")
    if lease_a["fence_token"] != 1:
        raise RuntimeError("EXPECTED_FENCE_TOKEN_1")

    first = mutate(
        "worker-a",
        1,
        REQUEST_KEY,
        PAYLOAD_SHA256,
    )
    if (
        first["applied"] is not True
        or first["duplicate"] is not False
        or first["simulated_effect_count"] != 1
    ):
        raise RuntimeError("FIRST_MUTATION_BINDING_FAILED")

    set_phase("A_ACQUIRED")

    wait_until(
        lambda: get_phase() == "B_ACQUIRED",
        "phase_B_ACQUIRED",
    )

    expect_violation(
        "STALE_OWNER",
        lambda: mutate(
            "worker-a",
            1,
            "stale-owner-write-v1",
            PAYLOAD_SHA256,
        ),
    )

    expect_violation(
        "LEASE_HELD",
        lambda: acquire_lease("worker-a"),
    )

    set_phase("A_STALE_CHECKS_DONE")


def worker_b_first_boot() -> None:
    wait_until(
        lambda: get_phase() == "A_ACQUIRED",
        "phase_A_ACQUIRED",
    )

    expect_violation(
        "LEASE_HELD",
        lambda: acquire_lease("worker-b"),
    )

    wait_for_lease_expiry()

    lease_b = acquire_lease("worker-b")
    if lease_b["fence_token"] != 2:
        raise RuntimeError("EXPECTED_FENCE_TOKEN_2")

    expect_violation(
        "STALE_FENCE_TOKEN",
        lambda: mutate(
            "worker-b",
            1,
            "stale-fence-write-v1",
            PAYLOAD_SHA256,
        ),
    )

    duplicate = mutate(
        "worker-b",
        2,
        REQUEST_KEY,
        PAYLOAD_SHA256,
    )
    if (
        duplicate["applied"] is not False
        or duplicate["duplicate"] is not True
        or duplicate["simulated_effect_count"] != 1
    ):
        raise RuntimeError("CROSS_WORKER_IDEMPOTENCY_FAILED")

    expect_violation(
        "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
        lambda: mutate(
            "worker-b",
            2,
            REQUEST_KEY,
            CONFLICT_SHA256,
        ),
    )

    set_phase("B_ACQUIRED")

    wait_until(
        lambda: get_phase() == "A_STALE_CHECKS_DONE",
        "phase_A_STALE_CHECKS_DONE",
    )

    set_phase("B_DONE")


def worker_a_restart(boot_count: int) -> None:
    wait_until(
        lambda: get_phase() == "B_DONE",
        "phase_B_DONE",
    )

    wait_for_lease_expiry()

    lease_a = acquire_lease("worker-a")
    if lease_a["fence_token"] != 3:
        raise RuntimeError("EXPECTED_FENCE_TOKEN_3")

    duplicate = mutate(
        "worker-a",
        3,
        REQUEST_KEY,
        PAYLOAD_SHA256,
    )
    if (
        duplicate["applied"] is not False
        or duplicate["duplicate"] is not True
        or duplicate["simulated_effect_count"] != 1
    ):
        raise RuntimeError("RESTART_IDEMPOTENCY_FAILED")

    with db_connect() as conn:
        with conn.cursor() as cur:
            _insert_event(
                cur,
                "worker-a",
                "restart_failover_complete",
                boot_count=boot_count,
                fence_token=3,
                simulated_effect_count=1,
            )
        conn.commit()

    set_phase("COMPLETE")


def run_drill() -> None:
    try:
        boot_count = int(STATE["boot_count"])

        if WORKER_ID == "worker-a":
            if boot_count == 1:
                worker_a_first_boot()
            else:
                worker_a_restart(boot_count)
        elif WORKER_ID == "worker-b":
            if boot_count == 1:
                worker_b_first_boot()

    except Exception as exc:
        STATE["last_error"] = f"{type(exc).__name__}:{exc}"
        try:
            with db_connect() as conn:
                with conn.cursor() as cur:
                    _insert_event(
                        cur,
                        WORKER_ID,
                        "fatal_error",
                        error=STATE["last_error"],
                    )
                conn.commit()
        except Exception:
            pass


def evidence_snapshot() -> dict[str, Any]:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT phase, updated_at
                FROM mv_mh1_phase
                WHERE drill_id = %s
                """,
                (DRILL_ID,),
            )
            phase_row = cur.fetchone()

            cur.execute(
                """
                SELECT
                    owner,
                    fence_token,
                    lease_expires_at,
                    clock_timestamp()
                FROM mv_mh1_control
                WHERE drill_id = %s
                """,
                (DRILL_ID,),
            )
            control_row = cur.fetchone()

            cur.execute(
                """
                SELECT
                    worker_id,
                    boot_count,
                    last_instance_id,
                    last_service_id,
                    updated_at
                FROM mv_mh1_workers
                WHERE drill_id = %s
                ORDER BY worker_id
                """,
                (DRILL_ID,),
            )
            workers = cur.fetchall()

            cur.execute(
                """
                SELECT
                    request_key,
                    payload_sha256,
                    applied_by,
                    fence_token,
                    created_at
                FROM mv_mh1_operations
                WHERE drill_id = %s
                ORDER BY request_key
                """,
                (DRILL_ID,),
            )
            operations = cur.fetchall()

            cur.execute(
                """
                SELECT
                    id,
                    worker_id,
                    event,
                    details,
                    created_at
                FROM mv_mh1_events
                WHERE drill_id = %s
                ORDER BY id
                """,
                (DRILL_ID,),
            )
            events = cur.fetchall()

    return {
        "schema": "MULTIVERSE_REMOTE_MULTIHOST_RENDER_EVIDENCE_v1",
        "target_class": TARGET_CLASS,
        "environment_class": ENVIRONMENT_CLASS,
        "drill_id": DRILL_ID,
        "database_bound": True,
        "postgres_id": EXPECTED_POSTGRES_ID,
        "phase": (
            phase_row[0]
            if phase_row
            else "MISSING"
        ),
        "phase_updated_at": (
            phase_row[1].isoformat()
            if phase_row
            else None
        ),
        "control": (
            {
                "owner": control_row[0],
                "fence_token": int(control_row[1]),
                "lease_expires_at": (
                    control_row[2].isoformat()
                    if control_row[2] is not None
                    else None
                ),
                "db_now": control_row[3].isoformat(),
            }
            if control_row
            else None
        ),
        "workers": [
            {
                "worker_id": row[0],
                "boot_count": int(row[1]),
                "last_instance_id": row[2],
                "last_service_id": row[3],
                "updated_at": row[4].isoformat(),
            }
            for row in workers
        ],
        "operations": [
            {
                "request_key": row[0],
                "payload_sha256": row[1],
                "applied_by": row[2],
                "fence_token": int(row[3]),
                "created_at": row[4].isoformat(),
            }
            for row in operations
        ],
        "operation_count": len(operations),
        "events": [
            {
                "id": int(row[0]),
                "worker_id": row[1],
                "event": row[2],
                "details": row[3],
                "created_at": row[4].isoformat(),
            }
            for row in events
        ],
        "authority": {
            "production_credentials": False,
            "production_deployment": False,
            "protected_keirin_data": False,
            "live_business_effect": False,
            "additional_spend_above_usd_0": False,
            "runtime_activation": False,
        },
        "runtime": RUNTIME,
        "proof_ceiling": PROOF_CEILING,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "MULTIVERSE-RemoteMultiHost-NoEffect/1"

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(
            payload,
            sort_keys=True,
            default=str,
        ).encode()
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
                    "worker_id": WORKER_ID,
                    "runtime": RUNTIME,
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
                    "worker_id": WORKER_ID,
                    "service_id": RENDER_SERVICE_ID,
                    "instance_id": RENDER_INSTANCE_ID,
                    "boot_count": STATE["boot_count"],
                    "last_error": STATE["last_error"],
                    "runtime": RUNTIME,
                },
            )
            return

        if self.path == "/evidence":
            try:
                payload = evidence_snapshot()
                payload["serving_worker_id"] = WORKER_ID
                payload["serving_service_id"] = RENDER_SERVICE_ID
                payload["serving_instance_id"] = RENDER_INSTANCE_ID
                self._send_json(200, payload)
            except Exception as exc:
                self._send_json(
                    503,
                    {
                        "error": f"{type(exc).__name__}:{exc}",
                        "runtime": RUNTIME,
                    },
                )
            return

        self._send_json(404, {"error": "not_found", "runtime": RUNTIME})

    def _deny_state_change(self) -> None:
        self._send_json(
            403,
            {
                "error": "state_changes_disabled_over_http",
                "runtime": RUNTIME,
            },
        )

    def do_POST(self) -> None:
        self._deny_state_change()

    def do_PUT(self) -> None:
        self._deny_state_change()

    def do_PATCH(self) -> None:
        self._deny_state_change()

    def do_DELETE(self) -> None:
        self._deny_state_change()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            json.dumps(
                {
                    "component": "http",
                    "worker_id": WORKER_ID,
                    "message": fmt % args,
                },
                sort_keys=True,
            ),
            flush=True,
        )


def main() -> None:
    validate_environment()
    STATE["execution_authorized"] = True

    ensure_schema()
    STATE["database_bound"] = True

    boot_count = register_boot()
    STATE["boot_count"] = boot_count
    STATE["ready"] = True

    thread = threading.Thread(
        target=run_drill,
        name=f"multihost-drill-{WORKER_ID}",
        daemon=True,
    )
    thread.start()

    port = int(os.environ.get("PORT", "10000"))
    print(
        json.dumps(
            {
                "event": "service_ready",
                "worker_id": WORKER_ID,
                "service_id": RENDER_SERVICE_ID,
                "instance_id": RENDER_INSTANCE_ID,
                "boot_count": boot_count,
                "database_bound": True,
                "execution_authorized": True,
                "runtime": RUNTIME,
                "target_class": TARGET_CLASS,
                "proof_ceiling": PROOF_CEILING,
            },
            sort_keys=True,
        ),
        flush=True,
    )

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
