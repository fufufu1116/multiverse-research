from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


TOPOLOGY_CLASS = "RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
PROOF_CEILING = "MULTI_HOST_PREPRODUCTION_SYNTHETIC_NO_EFFECT_PREPARATION_ONLY"
RUNTIME = "OFF"

WORKERS = ("worker-a", "worker-b")

AUTHORITY = {
    "remote_resource_creation": False,
    "remote_network_execution": False,
    "render_control_plane_execution": False,
    "additional_spend": False,
    "production_credentials": False,
    "production_deployment": False,
    "protected_keirin_data": False,
    "live_business_effect": False,
    "workflow_dispatch_rerun": False,
    "main_mutation": False,
    "ruleset_mutation": False,
    "merge_adoption": False,
    "runtime_activation": False,
}

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContractViolation(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LeaseReceipt:
    owner: str
    fence_token: int
    acquired_at: int
    lease_expires_at: int


@dataclass(frozen=True)
class MutationReceipt:
    owner: str
    fence_token: int
    request_key: str
    payload_sha256: str
    applied: bool
    duplicate: bool
    simulated_effect_count: int


def _require_exact_str(value: Any, code: str) -> str:
    if type(value) is not str:
        raise ContractViolation(code)
    return value


def _require_exact_int(value: Any, code: str) -> int:
    if type(value) is not int:
        raise ContractViolation(code)
    return value


def _require_worker(worker: Any) -> str:
    worker = _require_exact_str(worker, "WORKER_ID_TYPE")
    if worker not in WORKERS:
        raise ContractViolation("WORKER_ID_UNKNOWN")
    return worker


def _require_now(now: Any) -> int:
    now = _require_exact_int(now, "LOGICAL_TIME_TYPE")
    if now < 0:
        raise ContractViolation("LOGICAL_TIME_NEGATIVE")
    return now


def _require_ttl(ttl: Any) -> int:
    ttl = _require_exact_int(ttl, "LEASE_TTL_TYPE")
    if ttl <= 0:
        raise ContractViolation("LEASE_TTL_NONPOSITIVE")
    return ttl


def _require_fence_token(token: Any) -> int:
    token = _require_exact_int(token, "FENCE_TOKEN_TYPE")
    if token <= 0:
        raise ContractViolation("FENCE_TOKEN_NONPOSITIVE")
    return token


def _require_request_key(value: Any) -> str:
    value = _require_exact_str(value, "REQUEST_KEY_TYPE")
    if not value:
        raise ContractViolation("REQUEST_KEY_EMPTY")
    return value


def _require_digest(value: Any) -> str:
    value = _require_exact_str(value, "PAYLOAD_DIGEST_TYPE")
    if not _HEX64.fullmatch(value):
        raise ContractViolation("PAYLOAD_DIGEST_INVALID")
    return value


class SyntheticSharedState:
    """Deterministic repository-only model.

    This is intentionally not a networked lock implementation and does not
    claim real PostgreSQL or Render distributed behavior.
    """

    SNAPSHOT_SCHEMA = "MULTIVERSE_MULTI_HOST_SYNTHETIC_STATE_v1"

    def __init__(self) -> None:
        self.owner: str | None = None
        self.fence_token = 0
        self.lease_expires_at: int | None = None
        self.operations: dict[str, str] = {}
        self.simulated_effect_count = 0
        self.events: list[dict[str, Any]] = []

    def _record(self, event: str, **fields: Any) -> None:
        self.events.append({"event": event, **fields})

    def acquire(self, worker: Any, now: Any, ttl: Any) -> LeaseReceipt:
        worker = _require_worker(worker)
        now = _require_now(now)
        ttl = _require_ttl(ttl)

        if (
            self.owner is not None
            and self.lease_expires_at is not None
            and now < self.lease_expires_at
        ):
            self._record(
                "lease_acquire_rejected",
                requester=worker,
                current_owner=self.owner,
                fence_token=self.fence_token,
                now=now,
                lease_expires_at=self.lease_expires_at,
                reason="LEASE_HELD",
            )
            raise ContractViolation("LEASE_HELD")

        previous_owner = self.owner
        previous_token = self.fence_token

        self.fence_token += 1
        self.owner = worker
        self.lease_expires_at = now + ttl

        self._record(
            "lease_acquired",
            owner=worker,
            previous_owner=previous_owner,
            previous_fence_token=previous_token,
            fence_token=self.fence_token,
            now=now,
            lease_expires_at=self.lease_expires_at,
        )

        return LeaseReceipt(
            owner=worker,
            fence_token=self.fence_token,
            acquired_at=now,
            lease_expires_at=self.lease_expires_at,
        )

    def renew(
        self,
        worker: Any,
        token: Any,
        now: Any,
        ttl: Any,
    ) -> LeaseReceipt:
        worker = _require_worker(worker)
        token = _require_fence_token(token)
        now = _require_now(now)
        ttl = _require_ttl(ttl)

        if self.owner != worker:
            raise ContractViolation("STALE_OWNER")

        if self.fence_token != token:
            raise ContractViolation("STALE_FENCE_TOKEN")

        if self.lease_expires_at is None or now >= self.lease_expires_at:
            raise ContractViolation("LEASE_EXPIRED")

        self.lease_expires_at = now + ttl
        self._record(
            "lease_renewed",
            owner=worker,
            fence_token=token,
            now=now,
            lease_expires_at=self.lease_expires_at,
        )

        return LeaseReceipt(
            owner=worker,
            fence_token=token,
            acquired_at=now,
            lease_expires_at=self.lease_expires_at,
        )

    def mutate(
        self,
        worker: Any,
        token: Any,
        now: Any,
        request_key: Any,
        payload_sha256: Any,
    ) -> MutationReceipt:
        worker = _require_worker(worker)
        token = _require_fence_token(token)
        now = _require_now(now)
        request_key = _require_request_key(request_key)
        payload_sha256 = _require_digest(payload_sha256)

        if self.owner != worker:
            self._record(
                "mutation_rejected",
                requester=worker,
                supplied_fence_token=token,
                current_owner=self.owner,
                current_fence_token=self.fence_token,
                reason="STALE_OWNER",
            )
            raise ContractViolation("STALE_OWNER")

        if self.fence_token != token:
            self._record(
                "mutation_rejected",
                requester=worker,
                supplied_fence_token=token,
                current_owner=self.owner,
                current_fence_token=self.fence_token,
                reason="STALE_FENCE_TOKEN",
            )
            raise ContractViolation("STALE_FENCE_TOKEN")

        if self.lease_expires_at is None or now >= self.lease_expires_at:
            self._record(
                "mutation_rejected",
                requester=worker,
                supplied_fence_token=token,
                current_owner=self.owner,
                current_fence_token=self.fence_token,
                reason="LEASE_EXPIRED",
            )
            raise ContractViolation("LEASE_EXPIRED")

        existing = self.operations.get(request_key)

        if existing is not None:
            if existing != payload_sha256:
                self._record(
                    "mutation_rejected",
                    requester=worker,
                    fence_token=token,
                    request_key=request_key,
                    reason="IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
                )
                raise ContractViolation("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")

            self._record(
                "mutation_duplicate",
                owner=worker,
                fence_token=token,
                request_key=request_key,
                payload_sha256=payload_sha256,
                simulated_effect_count=self.simulated_effect_count,
            )
            return MutationReceipt(
                owner=worker,
                fence_token=token,
                request_key=request_key,
                payload_sha256=payload_sha256,
                applied=False,
                duplicate=True,
                simulated_effect_count=self.simulated_effect_count,
            )

        self.operations[request_key] = payload_sha256
        self.simulated_effect_count += 1

        self._record(
            "mutation_applied",
            owner=worker,
            fence_token=token,
            request_key=request_key,
            payload_sha256=payload_sha256,
            simulated_effect_count=self.simulated_effect_count,
        )

        return MutationReceipt(
            owner=worker,
            fence_token=token,
            request_key=request_key,
            payload_sha256=payload_sha256,
            applied=True,
            duplicate=False,
            simulated_effect_count=self.simulated_effect_count,
        )

    def snapshot_bytes(self) -> bytes:
        payload = {
            "schema": self.SNAPSHOT_SCHEMA,
            "owner": self.owner,
            "fence_token": self.fence_token,
            "lease_expires_at": self.lease_expires_at,
            "operations": dict(sorted(self.operations.items())),
            "simulated_effect_count": self.simulated_effect_count,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    @classmethod
    def restore(cls, snapshot: Any) -> "SyntheticSharedState":
        if type(snapshot) is not bytes:
            raise ContractViolation("SNAPSHOT_TYPE")

        try:
            payload = json.loads(snapshot.decode())
        except Exception as exc:
            raise ContractViolation("SNAPSHOT_JSON_INVALID") from exc

        if type(payload) is not dict:
            raise ContractViolation("SNAPSHOT_SHAPE")

        if set(payload) != {
            "schema",
            "owner",
            "fence_token",
            "lease_expires_at",
            "operations",
            "simulated_effect_count",
        }:
            raise ContractViolation("SNAPSHOT_KEYS")

        if payload["schema"] != cls.SNAPSHOT_SCHEMA:
            raise ContractViolation("SNAPSHOT_SCHEMA")

        owner = payload["owner"]
        if owner is not None:
            _require_worker(owner)

        fence_token = _require_exact_int(
            payload["fence_token"],
            "SNAPSHOT_FENCE_TOKEN_TYPE",
        )
        if fence_token < 0:
            raise ContractViolation("SNAPSHOT_FENCE_TOKEN_NEGATIVE")

        lease_expires_at = payload["lease_expires_at"]
        if lease_expires_at is not None:
            lease_expires_at = _require_exact_int(
                lease_expires_at,
                "SNAPSHOT_LEASE_EXPIRY_TYPE",
            )
            if lease_expires_at < 0:
                raise ContractViolation("SNAPSHOT_LEASE_EXPIRY_NEGATIVE")

        operations = payload["operations"]
        if type(operations) is not dict:
            raise ContractViolation("SNAPSHOT_OPERATIONS_TYPE")

        checked_operations: dict[str, str] = {}
        for key, digest in operations.items():
            checked_operations[
                _require_request_key(key)
            ] = _require_digest(digest)

        simulated_effect_count = _require_exact_int(
            payload["simulated_effect_count"],
            "SNAPSHOT_EFFECT_COUNT_TYPE",
        )
        if simulated_effect_count < 0:
            raise ContractViolation("SNAPSHOT_EFFECT_COUNT_NEGATIVE")

        if simulated_effect_count != len(checked_operations):
            raise ContractViolation("SNAPSHOT_EFFECT_COUNT_MISMATCH")

        state = cls()
        state.owner = owner
        state.fence_token = fence_token
        state.lease_expires_at = lease_expires_at
        state.operations = checked_operations
        state.simulated_effect_count = simulated_effect_count
        state._record(
            "snapshot_restored",
            owner=owner,
            fence_token=fence_token,
            lease_expires_at=lease_expires_at,
            operation_count=len(checked_operations),
        )
        return state


def payload_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractViolation("PAYLOAD_TYPE")
    return hashlib.sha256(payload).hexdigest()


def _expect_violation(
    findings: list[str],
    expected: str,
    fn,
) -> bool:
    try:
        fn()
    except ContractViolation as exc:
        if exc.code == expected:
            return True
        findings.append(
            f"EXPECTED_{expected}_GOT_{exc.code}"
        )
        return False
    findings.append(
        f"EXPECTED_{expected}_BUT_OPERATION_SUCCEEDED"
    )
    return False


def build_preparation_contract() -> dict[str, Any]:
    return {
        "schema": "MULTIVERSE_MULTI_HOST_PREPRODUCTION_PREPARATION_CONTRACT_v1",
        "topology_class": TOPOLOGY_CLASS,
        "environment_class": ENVIRONMENT_CLASS,
        "provider_family": "RENDER",
        "planned_topology": {
            "worker_count": 2,
            "workers": [
                {
                    "worker_id": "worker-a",
                    "service_identity": "UNPROVISIONED_WORKER_A",
                    "provisioned": False,
                },
                {
                    "worker_id": "worker-b",
                    "service_identity": "UNPROVISIONED_WORKER_B",
                    "provisioned": False,
                },
            ],
            "shared_state": {
                "kind": "POSTGRESQL",
                "identity": "UNPROVISIONED_SHARED_POSTGRES",
                "provisioned": False,
            },
            "actual_remote_execution_performed": False,
        },
        "lease_contract": {
            "single_owner_before_expiry": True,
            "successor_allowed_at_or_after_expiry": True,
            "fence_token_must_strictly_increase_on_acquire": True,
            "renewal_preserves_fence_token": True,
            "stale_owner_write_rejected": True,
            "stale_fence_write_rejected": True,
            "split_brain_write_rejected": True,
        },
        "idempotency_contract": {
            "scope": "SHARED_ACROSS_WORKERS",
            "same_key_same_payload_is_duplicate": True,
            "same_key_different_payload_is_rejected": True,
            "duplicate_external_effect": False,
        },
        "future_remote_evidence_requirements": {
            "separate_worker_provider_identities": True,
            "shared_state_provider_identity": True,
            "concurrent_acquire_attempt_receipts": True,
            "fencing_token_monotonicity_receipts": True,
            "stale_owner_rejection_receipts": True,
            "stale_fence_rejection_receipts": True,
            "successor_owner_failover_receipts": True,
            "cross_worker_idempotency_receipts": True,
            "restart_plus_failover_receipts": True,
            "split_brain_rejection_receipts": True,
            "provider_logs_for_both_workers": True,
            "provider_cpu_memory_for_both_workers": True,
            "database_transaction_or_lock_evidence": True,
            "no_http_slo_claim_without_http_metrics": True,
        },
        "authority": dict(AUTHORITY),
        "runtime": RUNTIME,
        "proof_ceiling": PROOF_CEILING,
    }


def run_synthetic_failover_drill() -> dict[str, Any]:
    findings: list[str] = []
    state = SyntheticSharedState()

    payload = b"MULTIVERSE_MULTI_HOST_NO_EFFECT_PAYLOAD_v1"
    digest = payload_sha256(payload)
    conflict_digest = payload_sha256(
        b"MULTIVERSE_MULTI_HOST_DIFFERENT_PAYLOAD_v1"
    )
    request_key = "shared-idempotency-key-v1"

    lease_a = state.acquire(
        "worker-a",
        now=0,
        ttl=5,
    )

    first_write = state.mutate(
        "worker-a",
        lease_a.fence_token,
        now=1,
        request_key=request_key,
        payload_sha256=digest,
    )

    concurrent_acquire_rejected = _expect_violation(
        findings,
        "LEASE_HELD",
        lambda: state.acquire(
            "worker-b",
            now=2,
            ttl=5,
        ),
    )

    lease_b = state.acquire(
        "worker-b",
        now=5,
        ttl=5,
    )

    stale_owner_rejected = _expect_violation(
        findings,
        "STALE_OWNER",
        lambda: state.mutate(
            "worker-a",
            lease_a.fence_token,
            now=6,
            request_key="stale-owner-write",
            payload_sha256=digest,
        ),
    )

    stale_fence_rejected = _expect_violation(
        findings,
        "STALE_FENCE_TOKEN",
        lambda: state.mutate(
            "worker-b",
            lease_a.fence_token,
            now=6,
            request_key="stale-fence-write",
            payload_sha256=digest,
        ),
    )

    duplicate = state.mutate(
        "worker-b",
        lease_b.fence_token,
        now=6,
        request_key=request_key,
        payload_sha256=digest,
    )

    conflicting_payload_rejected = _expect_violation(
        findings,
        "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
        lambda: state.mutate(
            "worker-b",
            lease_b.fence_token,
            now=6,
            request_key=request_key,
            payload_sha256=conflict_digest,
        ),
    )

    split_brain_acquire_rejected = _expect_violation(
        findings,
        "LEASE_HELD",
        lambda: state.acquire(
            "worker-a",
            now=7,
            ttl=5,
        ),
    )

    snapshot = state.snapshot_bytes()
    snapshot_sha256 = hashlib.sha256(snapshot).hexdigest()

    restored = SyntheticSharedState.restore(
        snapshot
    )
    restored_snapshot = restored.snapshot_bytes()
    restored_sha256 = hashlib.sha256(
        restored_snapshot
    ).hexdigest()

    lease_a_successor = restored.acquire(
        "worker-a",
        now=10,
        ttl=5,
    )

    stale_successor_rejected = _expect_violation(
        findings,
        "STALE_OWNER",
        lambda: restored.mutate(
            "worker-b",
            lease_b.fence_token,
            now=11,
            request_key="post-second-failover-stale-write",
            payload_sha256=digest,
        ),
    )

    fencing_monotonic = (
        lease_a.fence_token
        < lease_b.fence_token
        < lease_a_successor.fence_token
    )

    cross_worker_idempotency_pass = (
        first_write.applied is True
        and duplicate.applied is False
        and duplicate.duplicate is True
        and duplicate.simulated_effect_count == 1
    )

    snapshot_restore_match = (
        snapshot_sha256 == restored_sha256
    )

    split_brain_rejected = (
        concurrent_acquire_rejected
        and split_brain_acquire_rejected
        and stale_owner_rejected
        and stale_fence_rejected
        and stale_successor_rejected
    )

    return {
        "schema": "MULTIVERSE_MULTI_HOST_SYNTHETIC_FAILOVER_RECEIPT_v1",
        "topology_class": TOPOLOGY_CLASS,
        "environment_class": ENVIRONMENT_CLASS,
        "execution_scope": "REPOSITORY_SYNTHETIC_ONLY",
        "actual_remote_execution_performed": False,
        "remote_resources_created": False,
        "worker_a_initial_fence_token": lease_a.fence_token,
        "worker_b_successor_fence_token": lease_b.fence_token,
        "worker_a_second_successor_fence_token":
            lease_a_successor.fence_token,
        "fencing_monotonic": fencing_monotonic,
        "concurrent_acquire_rejected": concurrent_acquire_rejected,
        "stale_owner_rejected": stale_owner_rejected,
        "stale_fence_rejected": stale_fence_rejected,
        "split_brain_rejected": split_brain_rejected,
        "cross_worker_idempotency_pass":
            cross_worker_idempotency_pass,
        "conflicting_payload_rejected":
            conflicting_payload_rejected,
        "duplicate_external_effect": False,
        "simulated_effect_count_before_second_failover":
            state.simulated_effect_count,
        "snapshot_sha256": snapshot_sha256,
        "restored_snapshot_sha256": restored_sha256,
        "snapshot_restore_match": snapshot_restore_match,
        "findings": findings,
        "authority": dict(AUTHORITY),
        "runtime": RUNTIME,
        "proof_ceiling": PROOF_CEILING,
    }
