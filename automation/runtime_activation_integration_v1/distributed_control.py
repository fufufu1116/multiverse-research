"""Repository-only distributed Runtime control model for MULTIVERSE.

This module is intentionally provider-free.  It models the state semantics that a future
PostgreSQL adapter must implement, while keeping Runtime activation/effects impossible in
this Candidate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

SCHEMA = "MULTIVERSE_DISTRIBUTED_RUNTIME_CONTROL_MODEL_v1"
RUNTIME = "OFF"
PROOF_CEILING = "RUNTIME_ACTIVATION_INTEGRATION_REPOSITORY_PREPARATION_ONLY"
INTEGRATION_STATE = "ACTIVATION_INTEGRATION_PREPARATION_NOT_ACTIVATABLE"


class ControlViolation(RuntimeError):
    """Fail-closed distributed-control violation with a stable machine code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RuntimeIdentity:
    worker_id: str
    instance_id: str


@dataclass(frozen=True)
class LeaseGrant:
    worker_id: str
    instance_id: str
    fence_token: int
    lease_expires_at: float


@dataclass(frozen=True)
class OperationDecision:
    applied: bool
    duplicate: bool
    request_key: str
    payload_sha256: str
    applied_by: str
    fence_token: int


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_key: str
    value: dict[str, Any]
    worker_id: str
    instance_id: str
    fence_token: int


class MemoryDistributedControlStore:
    """Deterministic reference model for PostgreSQL-like serialized control semantics.

    The injected clock represents database time.  This class performs no I/O and exists
    only to make fencing/idempotency/restart invariants executable in repository tests.
    """

    def __init__(self, *, clock: Callable[[], float]):
        self._clock = clock
        self._owner: RuntimeIdentity | None = None
        self._fence_token = 0
        self._lease_expires_at: float | None = None
        self._operations: dict[str, OperationDecision] = {}
        self._checkpoints: dict[str, CheckpointRecord] = {}
        self._events: list[dict[str, Any]] = []

    @staticmethod
    def _validate_identity(identity: RuntimeIdentity) -> None:
        if not isinstance(identity, RuntimeIdentity):
            raise ControlViolation("IDENTITY_REQUIRED")
        if not identity.worker_id or len(identity.worker_id) > 128:
            raise ControlViolation("WORKER_ID_INVALID")
        if not identity.instance_id or len(identity.instance_id) > 256:
            raise ControlViolation("INSTANCE_ID_INVALID")

    def _event(self, event: str, **detail: Any) -> None:
        self._events.append({"event": event, "db_time": float(self._clock()), **detail})

    def acquire_lease(self, identity: RuntimeIdentity, *, ttl_seconds: int) -> LeaseGrant:
        self._validate_identity(identity)
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not (1 <= ttl_seconds <= 300):
            raise ControlViolation("LEASE_TTL_BOUNDED_1_300_REQUIRED")
        now = float(self._clock())
        if self._owner is not None and self._lease_expires_at is not None and now < self._lease_expires_at:
            self._event(
                "LEASE_REJECTED",
                reason="LEASE_HELD",
                requested_worker=identity.worker_id,
                current_worker=self._owner.worker_id,
                current_fence_token=self._fence_token,
            )
            raise ControlViolation("LEASE_HELD")
        self._fence_token += 1
        self._owner = identity
        self._lease_expires_at = now + ttl_seconds
        grant = LeaseGrant(identity.worker_id, identity.instance_id, self._fence_token, self._lease_expires_at)
        self._event("LEASE_ACQUIRED", worker_id=identity.worker_id, instance_id=identity.instance_id, fence_token=self._fence_token)
        return grant

    def renew_lease(self, identity: RuntimeIdentity, grant: LeaseGrant, *, ttl_seconds: int) -> LeaseGrant:
        self._assert_current(identity, grant)
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not (1 <= ttl_seconds <= 300):
            raise ControlViolation("LEASE_TTL_BOUNDED_1_300_REQUIRED")
        self._lease_expires_at = float(self._clock()) + ttl_seconds
        renewed = LeaseGrant(identity.worker_id, identity.instance_id, grant.fence_token, self._lease_expires_at)
        self._event("LEASE_RENEWED", worker_id=identity.worker_id, fence_token=grant.fence_token)
        return renewed

    def _assert_current(self, identity: RuntimeIdentity, grant: LeaseGrant) -> None:
        self._validate_identity(identity)
        now = float(self._clock())
        if self._owner is None or self._owner.worker_id != identity.worker_id or self._owner.instance_id != identity.instance_id:
            raise ControlViolation("STALE_OWNER")
        if grant.worker_id != identity.worker_id or grant.instance_id != identity.instance_id:
            raise ControlViolation("GRANT_IDENTITY_MISMATCH")
        if grant.fence_token != self._fence_token:
            raise ControlViolation("STALE_FENCE_TOKEN")
        if self._lease_expires_at is None or now >= self._lease_expires_at:
            raise ControlViolation("LEASE_EXPIRED")
        if grant.lease_expires_at != self._lease_expires_at:
            raise ControlViolation("GRANT_EXPIRY_MISMATCH")

    def assert_current(self, identity: RuntimeIdentity, grant: LeaseGrant) -> None:
        self._assert_current(identity, grant)

    def checkpoint(self, identity: RuntimeIdentity, grant: LeaseGrant, checkpoint_key: str, value: dict[str, Any]) -> CheckpointRecord:
        self._assert_current(identity, grant)
        if not isinstance(checkpoint_key, str) or not checkpoint_key or len(checkpoint_key) > 128:
            raise ControlViolation("CHECKPOINT_KEY_INVALID")
        if not isinstance(value, dict):
            raise ControlViolation("CHECKPOINT_VALUE_OBJECT_REQUIRED")
        inert = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))
        record = CheckpointRecord(checkpoint_key, inert, identity.worker_id, identity.instance_id, grant.fence_token)
        self._checkpoints[checkpoint_key] = record
        self._event("CHECKPOINT_WRITTEN", worker_id=identity.worker_id, checkpoint_key=checkpoint_key, fence_token=grant.fence_token)
        return record

    def get_checkpoint(self, checkpoint_key: str) -> CheckpointRecord | None:
        return self._checkpoints.get(checkpoint_key)

    @staticmethod
    def payload_digest(payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ControlViolation("OPERATION_PAYLOAD_OBJECT_REQUIRED")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def reserve_operation(
        self,
        identity: RuntimeIdentity,
        grant: LeaseGrant,
        request_key: str,
        payload_sha256: str,
    ) -> OperationDecision:
        self._assert_current(identity, grant)
        if not isinstance(request_key, str) or not request_key or len(request_key) > 160:
            raise ControlViolation("REQUEST_KEY_INVALID")
        if not isinstance(payload_sha256, str) or len(payload_sha256) != 64 or any(c not in "0123456789abcdef" for c in payload_sha256):
            raise ControlViolation("PAYLOAD_SHA256_INVALID")
        existing = self._operations.get(request_key)
        if existing is not None:
            if existing.payload_sha256 != payload_sha256:
                self._event("OPERATION_REJECTED", reason="IDEMPOTENCY_KEY_PAYLOAD_CONFLICT", request_key=request_key)
                raise ControlViolation("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")
            duplicate = OperationDecision(
                applied=False,
                duplicate=True,
                request_key=request_key,
                payload_sha256=payload_sha256,
                applied_by=existing.applied_by,
                fence_token=existing.fence_token,
            )
            self._event("OPERATION_DUPLICATE", request_key=request_key, worker_id=identity.worker_id, fence_token=grant.fence_token)
            return duplicate
        decision = OperationDecision(
            applied=True,
            duplicate=False,
            request_key=request_key,
            payload_sha256=payload_sha256,
            applied_by=identity.worker_id,
            fence_token=grant.fence_token,
        )
        self._operations[request_key] = decision
        self._event("OPERATION_RESERVED", request_key=request_key, worker_id=identity.worker_id, fence_token=grant.fence_token)
        return decision

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "runtime": RUNTIME,
            "proof_ceiling": PROOF_CEILING,
            "integration_state": INTEGRATION_STATE,
            "owner": None if self._owner is None else self._owner.worker_id,
            "instance_id": None if self._owner is None else self._owner.instance_id,
            "fence_token": self._fence_token,
            "lease_expires_at": self._lease_expires_at,
            "operation_count": len(self._operations),
            "checkpoint_count": len(self._checkpoints),
            "events": list(self._events),
        }
