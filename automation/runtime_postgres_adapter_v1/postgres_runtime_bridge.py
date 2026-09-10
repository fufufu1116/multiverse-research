"""Fail-closed repository bridge for the concrete PostgreSQL control-store adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .postgres_adapter import (
        ACTIVATION_READY,
        IMPLEMENTATION_STATE,
        KILL_SWITCH_DEFAULT_ENGAGED,
        PROOF_CEILING,
        PROVIDER_EFFECT_ADAPTER_ENABLED,
        RUNTIME,
        RUNTIME_ACTIVATION_BRIDGE_ENABLED,
        PostgresDistributedControlStore,
        PostgresLeaseGrant,
        RuntimeIdentity,
    )
except ImportError:
    from postgres_adapter import (
        ACTIVATION_READY,
        IMPLEMENTATION_STATE,
        KILL_SWITCH_DEFAULT_ENGAGED,
        PROOF_CEILING,
        PROVIDER_EFFECT_ADAPTER_ENABLED,
        RUNTIME,
        RUNTIME_ACTIVATION_BRIDGE_ENABLED,
        PostgresDistributedControlStore,
        PostgresLeaseGrant,
        RuntimeIdentity,
    )


@dataclass(frozen=True)
class PreparedPostgresSession:
    identity: RuntimeIdentity
    lease: PostgresLeaseGrant


class PreparedPostgresRuntimeBridge:
    """Can prepare inert distributed state but contains no activation/effect enablement."""

    def __init__(self, store: PostgresDistributedControlStore):
        if type(store) is not PostgresDistributedControlStore:
            raise TypeError("EXACT_POSTGRES_STORE_REQUIRED")
        self.store = store

    def prepare_session(
        self,
        worker_id: str,
        instance_id: str,
        *,
        ttl_seconds: int = 30,
    ) -> PreparedPostgresSession:
        identity = RuntimeIdentity(worker_id=worker_id, instance_id=instance_id)
        lease = self.store.acquire_lease(identity, ttl_seconds=ttl_seconds)
        return PreparedPostgresSession(identity=identity, lease=lease)

    def renew_session(
        self,
        session: PreparedPostgresSession,
        *,
        ttl_seconds: int = 30,
    ) -> PreparedPostgresSession:
        renewed = self.store.renew_lease(
            session.identity,
            session.lease,
            ttl_seconds=ttl_seconds,
        )
        return PreparedPostgresSession(identity=session.identity, lease=renewed)

    def checkpoint(
        self,
        session: PreparedPostgresSession,
        checkpoint_key: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        record = self.store.checkpoint(
            session.identity,
            session.lease,
            checkpoint_key,
            value,
        )
        return {
            "checkpoint_key": record.checkpoint_key,
            "value": record.value,
            "worker_id": record.worker_id,
            "instance_id": record.instance_id,
            "fence_token": record.fence_token,
        }

    def reserve_inert_operation(
        self,
        session: PreparedPostgresSession,
        request_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        digest = self.store.payload_digest(payload)
        decision = self.store.reserve_operation(
            session.identity,
            session.lease,
            request_key,
            digest,
        )
        return {
            "applied": decision.applied,
            "duplicate": decision.duplicate,
            "request_key": decision.request_key,
            "payload_sha256": decision.payload_sha256,
            "applied_by": decision.applied_by,
            "fence_token": decision.fence_token,
            "external_effect_executed": False,
        }

    def readiness(
        self,
        session: PreparedPostgresSession | None = None,
    ) -> dict[str, Any]:
        raw = (
            self.store.readiness()
            if session is None
            else self.store.readiness(session.identity, session.lease)
        )
        assert raw["runtime"] == RUNTIME
        assert raw["proof_ceiling"] == PROOF_CEILING
        assert raw["implementation_state"] == IMPLEMENTATION_STATE
        assert KILL_SWITCH_DEFAULT_ENGAGED is True
        assert PROVIDER_EFFECT_ADAPTER_ENABLED is False
        assert RUNTIME_ACTIVATION_BRIDGE_ENABLED is False
        assert ACTIVATION_READY is False
        assert raw["ready"] is False
        return raw
