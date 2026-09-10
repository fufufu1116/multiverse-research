"""Sealed Runtime v1 driver for the canonical Shared Engine task authority.

No provider/network execution exists here. The driver only performs bounded queue
selection, exact claim/start, lease renewal, and expired-lease reclaim through the
already-adopted Shared Engine DB/fencing primitives.
"""
from __future__ import annotations

from typing import Any

import db
from domain_registry import DomainPolicyError, validate_domain_task


class RuntimeDriverError(RuntimeError):
    pass


class SharedEngineRuntimeDriver:
    """Single-process queue/fencing adapter with no review/provider authority."""

    def _validated_task(self, task_id: str) -> dict[str, Any]:
        task = db.get_task(task_id)
        if task is None:
            raise RuntimeDriverError("UNKNOWN_TASK")
        validate_domain_task(task["domain"], task["task_type"])
        return task

    def claim_and_start_next(self, worker_id: str) -> dict[str, Any] | None:
        # Select from a read snapshot, then use exact claim_task so a race cannot
        # collateral-claim a different queue item. Invalid persisted tasks are skipped
        # without mutation and remain visible for explicit remediation.
        tasks = sorted(
            db.list_tasks(),
            key=lambda t: (-int(t["priority"]), float(t["created_at"]), t["id"]),
        )
        for task in tasks:
            if task["state"] != "PENDING":
                continue
            try:
                validate_domain_task(task["domain"], task["task_type"])
            except DomainPolicyError:
                continue
            try:
                generation = db.claim_task(task["id"], worker_id)
            except (db.LostLeaseError, db.InvalidTransitionError):
                continue
            db.transition(
                task["id"],
                "IN_IMPLEMENT",
                actor="runtime_v1_driver",
                event_type="RUNTIME_START",
                detail={"runtime_mode": "SEALED_DRY_RUN"},
                fencing=(worker_id, generation),
            )
            started = self._validated_task(task["id"])
            return {
                "task_id": task["id"],
                "claim_generation": generation,
                "state": started["state"],
                "domain": started["domain"],
                "task_type": started["task_type"],
            }
        return None

    def renew(self, task_id: str, worker_id: str, generation: int, *, lease_seconds: int | float | None = None) -> float:
        self._validated_task(task_id)
        return db.renew_lease(task_id, worker_id, generation, lease_seconds=lease_seconds)

    def reclaim_expired(self, task_id: str, worker_id: str, *, lease_seconds: int | float | None = None) -> int:
        self._validated_task(task_id)
        return db.reclaim_expired_task(task_id, worker_id, lease_seconds=lease_seconds)

    def read_task(self, task_id: str) -> dict[str, Any]:
        return self._validated_task(task_id)
