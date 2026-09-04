"""Sealed long-running scheduler shell for Runtime Supervisor v1.

The production SupervisorStore kill switch is permanently engaged in this Candidate,
so this service cannot start real work without a future separately reviewed activation
change. Tests may use an external test-store subclass; no activation bypass exists here.
"""
from __future__ import annotations

import time
from typing import Any

from runtime_supervisor import RuntimeGateError, RuntimeSupervisor
from shared_engine_driver import SharedEngineRuntimeDriver


class RuntimeService:
    def __init__(self, supervisor: RuntimeSupervisor, driver: SharedEngineRuntimeDriver, *, idle_seconds: float = 1.0):
        if type(driver) is not SharedEngineRuntimeDriver:
            raise RuntimeGateError("EXACT_SHARED_ENGINE_DRIVER_REQUIRED")
        if isinstance(idle_seconds, bool) or not isinstance(idle_seconds, (int, float)) or not (0 <= float(idle_seconds) <= 60):
            raise RuntimeGateError("IDLE_SECONDS_BOUNDED_0_60_REQUIRED")
        self.supervisor = supervisor
        self.driver = driver
        self.idle_seconds = float(idle_seconds)

    def cycle(self, token: str) -> dict[str, Any]:
        worker = self.supervisor.heartbeat(token)
        claimed = self.driver.claim_and_start_next(worker.worker_id)
        if claimed is None:
            result = {"status": "IDLE", "worker_id": worker.worker_id}
        else:
            result = {
                "status": "CLAIMED_FOR_IMPLEMENT",
                "worker_id": worker.worker_id,
                "task_id": claimed["task_id"],
                "claim_generation": claimed["claim_generation"],
                "state": claimed["state"],
                "domain": claimed["domain"],
                "task_type": claimed["task_type"],
            }
        self.supervisor.store.checkpoint("scheduler:last_cycle", result, instance_id=self.supervisor.instance_id)
        self.supervisor.store.journal(
            self.supervisor.instance_id,
            "SCHEDULER_CYCLE",
            worker_id=worker.worker_id,
            detail={"status": result["status"], "task_id": result.get("task_id")},
        )
        return result

    def run_forever(self, token: str) -> None:
        """Long-running loop. Production Candidate exits fail-closed at heartbeat because kill switch is engaged."""
        while True:
            result = self.cycle(token)
            if result["status"] == "IDLE" and self.idle_seconds:
                time.sleep(self.idle_seconds)

    def run_bounded_for_test(self, token: str, *, cycles: int) -> list[dict[str, Any]]:
        if isinstance(cycles, bool) or not isinstance(cycles, int) or not (1 <= cycles <= 100):
            raise RuntimeGateError("TEST_CYCLES_BOUNDED_1_100_REQUIRED")
        out = []
        for _ in range(cycles):
            out.append(self.cycle(token))
        return out
