"""Fail-closed bridge contract between Runtime lifecycle and distributed control state.

This Candidate deliberately has no method for enabling Runtime, provider effects, or the
activation bridge.  The model can prepare/bind inert distributed state while readiness
remains false.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .distributed_control import (
        INTEGRATION_STATE,
        PROOF_CEILING,
        RUNTIME,
        ControlViolation,
        LeaseGrant,
        MemoryDistributedControlStore,
        RuntimeIdentity,
    )
except ImportError:  # direct script/test execution
    from distributed_control import (
        INTEGRATION_STATE,
        PROOF_CEILING,
        RUNTIME,
        ControlViolation,
        LeaseGrant,
        MemoryDistributedControlStore,
        RuntimeIdentity,
    )

KILL_SWITCH_DEFAULT_ENGAGED = True
PROVIDER_EFFECT_ADAPTER_ENABLED = False
RUNTIME_ACTIVATION_BRIDGE_ENABLED = False
ACTIVATION_READY = False
RUNTIME_SUPERVISOR_SOURCE_MODE = "SEALED_DRY_RUN"
RUNTIME_CONTROL_AUTHORITY = "DISTRIBUTED_CONTROL_MODEL_PREPARATION_ONLY"


@dataclass(frozen=True)
class PreparedSession:
    identity: RuntimeIdentity
    lease: LeaseGrant


class PreparedRuntimeActivationBridge:
    """Repository-only bridge model; it cannot activate Runtime or emit external effects."""

    def __init__(self, store: MemoryDistributedControlStore):
        if type(store) is not MemoryDistributedControlStore:
            raise ControlViolation("EXACT_REFERENCE_STORE_REQUIRED_IN_PREPARATION")
        self.store = store

    def prepare_session(self, worker_id: str, instance_id: str, *, ttl_seconds: int = 30) -> PreparedSession:
        identity = RuntimeIdentity(worker_id=worker_id, instance_id=instance_id)
        lease = self.store.acquire_lease(identity, ttl_seconds=ttl_seconds)
        return PreparedSession(identity=identity, lease=lease)

    def renew_session(self, session: PreparedSession, *, ttl_seconds: int = 30) -> PreparedSession:
        renewed = self.store.renew_lease(session.identity, session.lease, ttl_seconds=ttl_seconds)
        return PreparedSession(identity=session.identity, lease=renewed)

    def checkpoint(self, session: PreparedSession, checkpoint_key: str, value: dict[str, Any]) -> dict[str, Any]:
        record = self.store.checkpoint(session.identity, session.lease, checkpoint_key, value)
        return {
            "checkpoint_key": record.checkpoint_key,
            "value": record.value,
            "worker_id": record.worker_id,
            "instance_id": record.instance_id,
            "fence_token": record.fence_token,
        }

    def reserve_inert_operation(self, session: PreparedSession, request_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        digest = self.store.payload_digest(payload)
        decision = self.store.reserve_operation(session.identity, session.lease, request_key, digest)
        return {
            "applied": decision.applied,
            "duplicate": decision.duplicate,
            "request_key": decision.request_key,
            "payload_sha256": decision.payload_sha256,
            "applied_by": decision.applied_by,
            "fence_token": decision.fence_token,
            "external_effect_executed": False,
        }

    def readiness(self, session: PreparedSession | None) -> dict[str, Any]:
        current_lease = False
        if session is not None:
            try:
                self.store.assert_current(session.identity, session.lease)
                current_lease = True
            except ControlViolation:
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
            "integration_state": INTEGRATION_STATE,
            "current_lease": current_lease,
            "kill_switch_engaged": KILL_SWITCH_DEFAULT_ENGAGED,
            "provider_effect_adapter_enabled": PROVIDER_EFFECT_ADAPTER_ENABLED,
            "runtime_activation_bridge_enabled": RUNTIME_ACTIVATION_BRIDGE_ENABLED,
            "activation_ready": ACTIVATION_READY,
            "ready": ready,
        }
