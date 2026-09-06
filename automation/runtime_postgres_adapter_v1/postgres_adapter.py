"""Concrete repository-only PostgreSQL Runtime control-store adapter.

The adapter never parses a DSN, opens a socket, imports a PostgreSQL driver, or creates a
connection by itself.  A caller must inject a connection factory.  Each adapter operation
obtains one connection, performs an explicit transaction using parameterized SQL, and then
closes it.  Candidate tests use deterministic fake DB-API connections only.

Remote execution is outside this Candidate's authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

RUNTIME = "OFF"
PROOF_CEILING = "RUNTIME_POSTGRES_ADAPTER_REPOSITORY_IMPLEMENTATION_ONLY"
IMPLEMENTATION_STATE = "POSTGRES_ADAPTER_IMPLEMENTED_NOT_REMOTE_VALIDATED"
KILL_SWITCH_DEFAULT_ENGAGED = True
PROVIDER_EFFECT_ADAPTER_ENABLED = False
RUNTIME_ACTIVATION_BRIDGE_ENABLED = False
ACTIVATION_READY = False
NO_CONNECTION_STRING_HANDLING = True
NO_NETWORK_DIALING_IN_CANDIDATE = True


class PostgresControlViolation(RuntimeError):
    """Fail-closed PostgreSQL control-store violation with a stable machine code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RuntimeIdentity:
    worker_id: str
    instance_id: str


@dataclass(frozen=True)
class PostgresLeaseGrant:
    runtime_id: str
    worker_id: str
    instance_id: str
    fence_token: int
    lease_expires_at: datetime


@dataclass(frozen=True)
class PostgresCheckpointRecord:
    runtime_id: str
    checkpoint_key: str
    value: dict[str, Any]
    worker_id: str
    instance_id: str
    fence_token: int


@dataclass(frozen=True)
class PostgresOperationDecision:
    applied: bool
    duplicate: bool
    runtime_id: str
    request_key: str
    payload_sha256: str
    applied_by: str
    fence_token: int


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...
    def fetchone(self) -> Any: ...
    def close(self) -> Any: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...
    def close(self) -> Any: ...


ConnectionFactory = Callable[[], ConnectionLike]


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS mv_runtime_control_v1 (
    runtime_id text PRIMARY KEY,
    owner_worker_id text,
    owner_instance_id text,
    fence_token bigint NOT NULL DEFAULT 0,
    lease_expires_at timestamptz,
    kill_switch_engaged boolean NOT NULL DEFAULT true,
    activation_bridge_enabled boolean NOT NULL DEFAULT false,
    provider_effect_adapter_enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS mv_runtime_checkpoints_v1 (
    runtime_id text NOT NULL,
    checkpoint_key text NOT NULL,
    value_json jsonb NOT NULL,
    worker_id text NOT NULL,
    instance_id text NOT NULL,
    fence_token bigint NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (runtime_id, checkpoint_key)
);
CREATE TABLE IF NOT EXISTS mv_runtime_operations_v1 (
    runtime_id text NOT NULL,
    request_key text NOT NULL,
    payload_sha256 text NOT NULL,
    applied_by text NOT NULL,
    fence_token bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (runtime_id, request_key)
);
""".strip()

ENSURE_CONTROL_SQL = """
INSERT INTO mv_runtime_control_v1 (runtime_id)
VALUES (%s)
ON CONFLICT (runtime_id) DO NOTHING
""".strip()

CONTROL_FOR_UPDATE_SQL = """
SELECT owner_worker_id, owner_instance_id, fence_token, lease_expires_at,
       kill_switch_engaged, activation_bridge_enabled, provider_effect_adapter_enabled,
       clock_timestamp()
FROM mv_runtime_control_v1
WHERE runtime_id = %s
FOR UPDATE
""".strip()

ACQUIRE_LEASE_SQL = """
UPDATE mv_runtime_control_v1
SET owner_worker_id = %s,
    owner_instance_id = %s,
    fence_token = fence_token + 1,
    lease_expires_at = clock_timestamp() + (%s * interval '1 second')
WHERE runtime_id = %s
RETURNING fence_token, lease_expires_at
""".strip()

RENEW_LEASE_SQL = """
UPDATE mv_runtime_control_v1
SET lease_expires_at = clock_timestamp() + (%s * interval '1 second')
WHERE runtime_id = %s
RETURNING lease_expires_at
""".strip()

CHECKPOINT_UPSERT_SQL = """
INSERT INTO mv_runtime_checkpoints_v1
    (runtime_id, checkpoint_key, value_json, worker_id, instance_id, fence_token)
VALUES (%s, %s, %s::jsonb, %s, %s, %s)
ON CONFLICT (runtime_id, checkpoint_key) DO UPDATE
SET value_json = EXCLUDED.value_json,
    worker_id = EXCLUDED.worker_id,
    instance_id = EXCLUDED.instance_id,
    fence_token = EXCLUDED.fence_token,
    updated_at = clock_timestamp()
""".strip()

CHECKPOINT_READ_SQL = """
SELECT value_json, worker_id, instance_id, fence_token
FROM mv_runtime_checkpoints_v1
WHERE runtime_id = %s AND checkpoint_key = %s
""".strip()

OPERATION_INSERT_SQL = """
INSERT INTO mv_runtime_operations_v1
    (runtime_id, request_key, payload_sha256, applied_by, fence_token)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (runtime_id, request_key) DO NOTHING
RETURNING payload_sha256, applied_by, fence_token
""".strip()

OPERATION_READ_SQL = """
SELECT payload_sha256, applied_by, fence_token
FROM mv_runtime_operations_v1
WHERE runtime_id = %s AND request_key = %s
""".strip()


class PostgresDistributedControlStore:
    """Concrete SQL adapter over an injected DB-API-like connection factory."""

    def __init__(self, *, runtime_id: str, connection_factory: ConnectionFactory):
        self._validate_runtime_id(runtime_id)
        if not callable(connection_factory):
            raise PostgresControlViolation("CONNECTION_FACTORY_REQUIRED")
        self.runtime_id = runtime_id
        self._connection_factory = connection_factory

    @staticmethod
    def _validate_runtime_id(runtime_id: str) -> None:
        if type(runtime_id) is not str or not runtime_id or len(runtime_id) > 128:
            raise PostgresControlViolation("RUNTIME_ID_INVALID")

    @staticmethod
    def _validate_identity(identity: RuntimeIdentity) -> None:
        if type(identity) is not RuntimeIdentity:
            raise PostgresControlViolation("IDENTITY_REQUIRED")
        if type(identity.worker_id) is not str or not identity.worker_id or len(identity.worker_id) > 128:
            raise PostgresControlViolation("WORKER_ID_INVALID")
        if type(identity.instance_id) is not str or not identity.instance_id or len(identity.instance_id) > 256:
            raise PostgresControlViolation("INSTANCE_ID_INVALID")

    @staticmethod
    def _validate_ttl(ttl_seconds: int) -> None:
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 300:
            raise PostgresControlViolation("LEASE_TTL_BOUNDED_1_300_REQUIRED")

    @staticmethod
    def _validate_checkpoint_key(checkpoint_key: str) -> None:
        if type(checkpoint_key) is not str or not checkpoint_key or len(checkpoint_key) > 128:
            raise PostgresControlViolation("CHECKPOINT_KEY_INVALID")

    @staticmethod
    def _validate_request_key(request_key: str) -> None:
        if type(request_key) is not str or not request_key or len(request_key) > 160:
            raise PostgresControlViolation("REQUEST_KEY_INVALID")

    @staticmethod
    def _validate_digest(payload_sha256: str) -> None:
        if (
            type(payload_sha256) is not str
            or len(payload_sha256) != 64
            or any(c not in "0123456789abcdef" for c in payload_sha256)
        ):
            raise PostgresControlViolation("PAYLOAD_SHA256_INVALID")

    @staticmethod
    def payload_digest(payload: dict[str, Any]) -> str:
        if type(payload) is not dict:
            raise PostgresControlViolation("OPERATION_PAYLOAD_OBJECT_REQUIRED")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _transaction(self, fn: Callable[[CursorLike], Any]) -> Any:
        conn = self._connection_factory()
        if conn is None:
            raise PostgresControlViolation("CONNECTION_FACTORY_RETURNED_NONE")
        cursor = None
        try:
            cursor = conn.cursor()
            result = fn(cursor)
            conn.commit()
            return result
        except PostgresControlViolation:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise PostgresControlViolation("POSTGRES_ADAPTER_ERROR") from exc
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    def initialize_schema(self) -> None:
        """Execute only the fixed schema SQL on an injected connection."""
        def op(cursor: CursorLike) -> None:
            cursor.execute(SCHEMA_SQL, ())
        self._transaction(op)

    def _ensure_and_lock_control(self, cursor: CursorLike) -> tuple[Any, ...]:
        cursor.execute(ENSURE_CONTROL_SQL, (self.runtime_id,))
        cursor.execute(CONTROL_FOR_UPDATE_SQL, (self.runtime_id,))
        row = cursor.fetchone()
        if row is None or len(row) != 8:
            raise PostgresControlViolation("CONTROL_ROW_MISSING")
        return tuple(row)

    @staticmethod
    def _require_default_deny_flags(row: tuple[Any, ...]) -> None:
        kill_switch, activation_bridge, provider_effect = row[4], row[5], row[6]
        if kill_switch is not True:
            raise PostgresControlViolation("KILL_SWITCH_NOT_ENGAGED")
        if activation_bridge is not False:
            raise PostgresControlViolation("ACTIVATION_BRIDGE_NOT_DISABLED")
        if provider_effect is not False:
            raise PostgresControlViolation("PROVIDER_EFFECT_ADAPTER_NOT_DISABLED")

    def acquire_lease(self, identity: RuntimeIdentity, *, ttl_seconds: int) -> PostgresLeaseGrant:
        self._validate_identity(identity)
        self._validate_ttl(ttl_seconds)

        def op(cursor: CursorLike) -> PostgresLeaseGrant:
            row = self._ensure_and_lock_control(cursor)
            self._require_default_deny_flags(row)
            owner_worker, owner_instance, fence, lease_expires_at, _, _, _, db_now = row
            if lease_expires_at is not None and db_now < lease_expires_at:
                raise PostgresControlViolation("LEASE_HELD")
            cursor.execute(
                ACQUIRE_LEASE_SQL,
                (identity.worker_id, identity.instance_id, ttl_seconds, self.runtime_id),
            )
            updated = cursor.fetchone()
            if updated is None or len(updated) != 2:
                raise PostgresControlViolation("LEASE_UPDATE_FAILED")
            new_fence, new_expiry = updated
            if type(new_fence) is not int or new_fence != fence + 1:
                raise PostgresControlViolation("FENCE_NOT_MONOTONIC")
            return PostgresLeaseGrant(
                runtime_id=self.runtime_id,
                worker_id=identity.worker_id,
                instance_id=identity.instance_id,
                fence_token=new_fence,
                lease_expires_at=new_expiry,
            )

        return self._transaction(op)

    def _assert_current_locked(
        self,
        cursor: CursorLike,
        identity: RuntimeIdentity,
        grant: PostgresLeaseGrant,
    ) -> tuple[Any, ...]:
        self._validate_identity(identity)
        if type(grant) is not PostgresLeaseGrant:
            raise PostgresControlViolation("LEASE_GRANT_REQUIRED")
        if grant.runtime_id != self.runtime_id:
            raise PostgresControlViolation("GRANT_RUNTIME_MISMATCH")
        if grant.worker_id != identity.worker_id or grant.instance_id != identity.instance_id:
            raise PostgresControlViolation("GRANT_IDENTITY_MISMATCH")

        row = self._ensure_and_lock_control(cursor)
        self._require_default_deny_flags(row)
        owner_worker, owner_instance, fence, lease_expires_at, _, _, _, db_now = row

        if owner_worker != identity.worker_id or owner_instance != identity.instance_id:
            raise PostgresControlViolation("STALE_OWNER")
        if grant.fence_token != fence:
            raise PostgresControlViolation("STALE_FENCE_TOKEN")
        if lease_expires_at is None or db_now >= lease_expires_at:
            raise PostgresControlViolation("LEASE_EXPIRED")
        if grant.lease_expires_at != lease_expires_at:
            raise PostgresControlViolation("GRANT_EXPIRY_MISMATCH")
        return row

    def assert_current(self, identity: RuntimeIdentity, grant: PostgresLeaseGrant) -> None:
        def op(cursor: CursorLike) -> None:
            self._assert_current_locked(cursor, identity, grant)
        self._transaction(op)

    def renew_lease(
        self,
        identity: RuntimeIdentity,
        grant: PostgresLeaseGrant,
        *,
        ttl_seconds: int,
    ) -> PostgresLeaseGrant:
        self._validate_ttl(ttl_seconds)

        def op(cursor: CursorLike) -> PostgresLeaseGrant:
            self._assert_current_locked(cursor, identity, grant)
            cursor.execute(RENEW_LEASE_SQL, (ttl_seconds, self.runtime_id))
            updated = cursor.fetchone()
            if updated is None or len(updated) != 1:
                raise PostgresControlViolation("LEASE_RENEW_FAILED")
            return PostgresLeaseGrant(
                runtime_id=self.runtime_id,
                worker_id=identity.worker_id,
                instance_id=identity.instance_id,
                fence_token=grant.fence_token,
                lease_expires_at=updated[0],
            )

        return self._transaction(op)

    def checkpoint(
        self,
        identity: RuntimeIdentity,
        grant: PostgresLeaseGrant,
        checkpoint_key: str,
        value: dict[str, Any],
    ) -> PostgresCheckpointRecord:
        self._validate_checkpoint_key(checkpoint_key)
        if type(value) is not dict:
            raise PostgresControlViolation("CHECKPOINT_VALUE_OBJECT_REQUIRED")
        value_json = json.dumps(value, sort_keys=True, separators=(",", ":"))

        def op(cursor: CursorLike) -> PostgresCheckpointRecord:
            self._assert_current_locked(cursor, identity, grant)
            cursor.execute(
                CHECKPOINT_UPSERT_SQL,
                (
                    self.runtime_id,
                    checkpoint_key,
                    value_json,
                    identity.worker_id,
                    identity.instance_id,
                    grant.fence_token,
                ),
            )
            return PostgresCheckpointRecord(
                runtime_id=self.runtime_id,
                checkpoint_key=checkpoint_key,
                value=json.loads(value_json),
                worker_id=identity.worker_id,
                instance_id=identity.instance_id,
                fence_token=grant.fence_token,
            )

        return self._transaction(op)

    def get_checkpoint(self, checkpoint_key: str) -> PostgresCheckpointRecord | None:
        self._validate_checkpoint_key(checkpoint_key)

        def op(cursor: CursorLike) -> PostgresCheckpointRecord | None:
            cursor.execute(CHECKPOINT_READ_SQL, (self.runtime_id, checkpoint_key))
            row = cursor.fetchone()
            if row is None:
                return None
            if len(row) != 4:
                raise PostgresControlViolation("CHECKPOINT_ROW_INVALID")
            value_json, worker_id, instance_id, fence_token = row
            if type(value_json) is str:
                value = json.loads(value_json)
            elif type(value_json) is dict:
                value = json.loads(json.dumps(value_json, sort_keys=True, separators=(",", ":")))
            else:
                raise PostgresControlViolation("CHECKPOINT_VALUE_INVALID")
            return PostgresCheckpointRecord(
                runtime_id=self.runtime_id,
                checkpoint_key=checkpoint_key,
                value=value,
                worker_id=worker_id,
                instance_id=instance_id,
                fence_token=fence_token,
            )

        return self._transaction(op)

    def reserve_operation(
        self,
        identity: RuntimeIdentity,
        grant: PostgresLeaseGrant,
        request_key: str,
        payload_sha256: str,
    ) -> PostgresOperationDecision:
        self._validate_request_key(request_key)
        self._validate_digest(payload_sha256)

        def op(cursor: CursorLike) -> PostgresOperationDecision:
            self._assert_current_locked(cursor, identity, grant)
            cursor.execute(
                OPERATION_INSERT_SQL,
                (
                    self.runtime_id,
                    request_key,
                    payload_sha256,
                    identity.worker_id,
                    grant.fence_token,
                ),
            )
            inserted = cursor.fetchone()
            if inserted is not None:
                if len(inserted) != 3:
                    raise PostgresControlViolation("OPERATION_INSERT_RESULT_INVALID")
                return PostgresOperationDecision(
                    applied=True,
                    duplicate=False,
                    runtime_id=self.runtime_id,
                    request_key=request_key,
                    payload_sha256=payload_sha256,
                    applied_by=inserted[1],
                    fence_token=inserted[2],
                )

            cursor.execute(OPERATION_READ_SQL, (self.runtime_id, request_key))
            existing = cursor.fetchone()
            if existing is None or len(existing) != 3:
                raise PostgresControlViolation("OPERATION_CONFLICT_ROW_MISSING")
            existing_digest, applied_by, fence_token = existing
            if existing_digest != payload_sha256:
                raise PostgresControlViolation("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")
            return PostgresOperationDecision(
                applied=False,
                duplicate=True,
                runtime_id=self.runtime_id,
                request_key=request_key,
                payload_sha256=payload_sha256,
                applied_by=applied_by,
                fence_token=fence_token,
            )

        return self._transaction(op)

    def readiness(self, identity: RuntimeIdentity | None = None, grant: PostgresLeaseGrant | None = None) -> dict[str, Any]:
        current_lease = False
        if identity is not None and grant is not None:
            try:
                self.assert_current(identity, grant)
                current_lease = True
            except PostgresControlViolation:
                current_lease = False
        ready = bool(
            current_lease
            and not KILL_SWITCH_DEFAULT_ENGAGED
            and PROVIDER_EFFECT_ADAPTER_ENABLED
            and RUNTIME_ACTIVATION_BRIDGE_ENABLED
            and ACTIVATION_READY
        )
        return {
            "runtime": RUNTIME,
            "proof_ceiling": PROOF_CEILING,
            "implementation_state": IMPLEMENTATION_STATE,
            "current_lease": current_lease,
            "kill_switch_engaged": KILL_SWITCH_DEFAULT_ENGAGED,
            "provider_effect_adapter_enabled": PROVIDER_EFFECT_ADAPTER_ENABLED,
            "runtime_activation_bridge_enabled": RUNTIME_ACTIVATION_BRIDGE_ENABLED,
            "activation_ready": ACTIVATION_READY,
            "ready": ready,
        }
