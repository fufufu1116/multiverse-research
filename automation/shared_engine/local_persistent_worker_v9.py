"""Candidate-only local persistent worker over the reviewed Shared Engine v8.

This module is a bounded process-loop proof, not a deployed daemon. Shared Engine
SQLite task state and events remain the sole workflow authority. The worker cannot
create tasks, widen policy, contact providers/network, read credentials, spend, or
activate Runtime.

The worker deliberately does not accept or retain a caller-supplied/full Shared Engine
object. It stores only the exact reviewed binding plus local receipt DB locations and
constructs the exact reviewed execution engine transiently for execution-only actions.
This removes both arbitrary engine injection and retained transitive submit/create-task
capability from the worker object.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import sqlite3
import threading
import time
import uuid

import config
import db
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from exact_v7_shared_engine import ExactV7SharedEngine
from integration_bridge import BridgeError, IntegrationBinding


MAX_POLL_SECONDS = 5.0
MIN_POLL_SECONDS = 0.01
MAX_RUN_CYCLES = 1000
FIX_STATES = frozenset({"LAB_FIX_REQUIRED", "AUDIT_FIX_REQUIRED"})
ACTIVE_STATES = frozenset(db.RECOVERABLE_ACTIVE_STATES)


@dataclass(frozen=True)
class WorkerConfig:
    lease_seconds: float = 120.0
    heartbeat_seconds: float = 20.0
    poll_seconds: float = 0.25

    def validate(self) -> "WorkerConfig":
        lease = float(self.lease_seconds)
        heartbeat = float(self.heartbeat_seconds)
        poll = float(self.poll_seconds)
        if not (0 < lease <= config.LEASE_MAX_SECONDS):
            raise ValueError("V9_LEASE_BOUND")
        if not (0 < heartbeat < lease / 2):
            raise ValueError("V9_HEARTBEAT_BOUND")
        if not (MIN_POLL_SECONDS <= poll <= MAX_POLL_SECONDS):
            raise ValueError("V9_POLL_BOUND")
        return self


class LocalPersistentWorker:
    """Consumes already-enqueued tasks through a sealed exact-v7 execution boundary."""

    def __init__(
        self,
        binding: IntegrationBinding,
        bridge_receipt_db: str,
        provider_receipt_db: str,
        worker_config: WorkerConfig | None = None,
        *,
        _execute_delay: float = 0.0,
    ):
        if type(binding) is not IntegrationBinding:
            raise TypeError("V9_EXACT_BINDING_TYPE_REQUIRED")
        binding.validate()
        if binding.canonical_main != CANONICAL_MAIN or binding.provider_adapter_head != V7_HEAD:
            raise ValueError("V9_EXACT_PR91_PR88_BINDING_REQUIRED")
        for label, path in (("bridge", bridge_receipt_db), ("provider", provider_receipt_db)):
            if not isinstance(path, str) or not path:
                raise ValueError(f"V9_{label.upper()}_DB_PATH_REQUIRED")
        self.binding = binding
        self._bridge_receipt_db = bridge_receipt_db
        self._provider_receipt_db = provider_receipt_db
        self.config = (worker_config or WorkerConfig()).validate()
        if not isinstance(_execute_delay, (int, float)) or isinstance(_execute_delay, bool) or _execute_delay < 0:
            raise ValueError("V9_TEST_DELAY_BOUND")
        self._execute_delay = float(_execute_delay)
        self._stop = threading.Event()
        # Local process identity only. It is not authenticated external identity and is
        # intentionally not accepted from task payload or a public worker_id argument.
        self.worker_id = f"lpw9-{os.getpid()}-{uuid.uuid4().hex[:16]}"
        db._validated_worker_id(self.worker_id)

    def _open_exact_engine(self) -> ExactV7SharedEngine:
        """Construct only the exact reviewed PR91->PR88 engine, transiently.

        The full engine (which also owns submit/create authority for construction code)
        is never accepted from a caller and is never retained on the worker object.
        """
        engine = ExactV7SharedEngine(self.binding, self._bridge_receipt_db, self._provider_receipt_db)
        if type(engine) is not ExactV7SharedEngine:
            engine.close()
            raise TypeError("V9_EXACT_ENGINE_REQUIRED")
        return engine

    def stop(self) -> None:
        """Request bounded shutdown. Active authority is never force-released."""
        self._stop.set()

    def _semantic_generation(self, task_id: str) -> int:
        """Derive retry generation from authoritative durable transition events.

        Lease reclaim changes fencing generation but not this role-attempt identity, so a
        crash after provider receipt can replay the same durable provider operation.
        """
        conn = sqlite3.connect(config.DB_PATH, timeout=10)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND after_state IN ('LAB_FIX_REQUIRED','AUDIT_FIX_REQUIRED')",
                (task_id,),
            ).fetchone()
            return int(row[0])
        finally:
            conn.close()

    def _validate_persisted_task(self, task_id: str):
        engine = self._open_exact_engine()
        try:
            return engine._validate_persisted_task(task_id)
        finally:
            engine.close()

    def _reclaim_expired(self, task_id: str) -> int:
        engine = self._open_exact_engine()
        try:
            return engine.reclaim_expired(task_id, self.worker_id, lease_seconds=self.config.lease_seconds)
        finally:
            engine.close()

    def _renew(self, task_id: str, generation: int) -> float:
        engine = self._open_exact_engine()
        try:
            return engine.renew(
                task_id,
                self.worker_id,
                generation,
                lease_seconds=self.config.lease_seconds,
            )
        finally:
            engine.close()

    def _claim_or_reclaim(self):
        task_id = db.claim_next_task(self.worker_id, lease_seconds=self.config.lease_seconds)
        if task_id is not None:
            task = self._validate_persisted_task(task_id)
            generation = int(task["claim_generation"])
            db.transition(
                task_id,
                "IN_IMPLEMENT",
                actor="local_persistent_worker_v9",
                event_type="START_ALREADY_ENQUEUED",
                fencing=(self.worker_id, generation),
            )
            return task_id, generation

        now = time.time()
        candidates = [
            task for task in db.list_tasks()
            if task["state"] in ACTIVE_STATES
            and task["claimed_by"] is not None
            and task["lease_until"] is not None
            and float(task["lease_until"]) < now
        ]
        candidates.sort(key=lambda task: (-int(task["priority"]), float(task["created_at"]), task["id"]))
        for task in candidates:
            try:
                self._validate_persisted_task(task["id"])
                generation = self._reclaim_expired(task["id"])
                return task["id"], generation
            except (db.LostLeaseError, db.InvalidTransitionError):
                continue
        return None

    def _result_for(self, task_id: str, role: str) -> dict:
        head = self.binding.candidate_head
        evidence = f"local-v9:{task_id}:{role.lower()}:{self._semantic_generation(task_id)}"
        if role == "IMPLEMENT":
            return {
                "status": "READY",
                "candidate_head": head,
                "diff_lines": 0,
                "cost_microusd": 0,
                "evidence_ref": evidence,
            }
        return {"verdict": "PASS", "reviewed_head": head, "evidence_ref": evidence}

    def _role_for_state(self, state: str) -> str | None:
        return {"IN_IMPLEMENT": "IMPLEMENT", "IN_LAB": "LAB", "IN_AUDIT": "AUDIT"}.get(state)

    def _heartbeat_loop(self, task_id: str, generation: int, done: threading.Event) -> None:
        while not done.wait(self.config.heartbeat_seconds):
            try:
                self._renew(task_id, generation)
            except (db.LostLeaseError, db.InvalidTransitionError, KeyError):
                return

    def _execute_role(self, task_id: str, generation: int, role: str) -> str:
        semantic_generation = self._semantic_generation(task_id)
        operation_key = f"lpw9:{task_id}:{role.lower()}:{semantic_generation}"
        heartbeat_done = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(task_id, generation, heartbeat_done),
            name=f"lpw9-heartbeat-{task_id}",
            daemon=True,
        )
        heartbeat.start()
        try:
            if self._execute_delay:
                time.sleep(self._execute_delay)
            engine = self._open_exact_engine()
            try:
                return engine.execute_role(
                    task_id,
                    role,
                    semantic_generation,
                    operation_key,
                    self.worker_id,
                    generation,
                    self._result_for(task_id, role),
                )
            finally:
                engine.close()
        finally:
            heartbeat_done.set()
            heartbeat.join(timeout=max(1.0, self.config.heartbeat_seconds * 2))

    def _drive_claimed(self, task_id: str, generation: int) -> str:
        while True:
            task = db.get_task(task_id)
            if task is None:
                raise KeyError(task_id)
            state = task["state"]
            if state in {"DONE", "FAILED_CLOSED", "OWNER_GATE", "ROLLED_BACK"}:
                return state
            if self._stop.is_set():
                return state
            if state == "BLOCKED_TECHNICAL":
                db.transition(
                    task_id,
                    "PENDING",
                    actor="local_persistent_worker_v9",
                    event_type="REQUEUE_RECOVERED_BLOCK",
                    release=True,
                    fencing=(self.worker_id, generation),
                )
                return "PENDING"
            if state in FIX_STATES:
                db.transition(
                    task_id,
                    "IN_IMPLEMENT",
                    actor="local_persistent_worker_v9",
                    event_type="BOUNDED_FIX_RETRY",
                    fencing=(self.worker_id, generation),
                )
                continue
            role = self._role_for_state(state)
            if role is None:
                raise BridgeError(f"V9_UNSUPPORTED_STATE:{state}")
            state = self._execute_role(task_id, generation, role)

    def step(self):
        """Claim/reclaim one durable task and drive it until a safe boundary."""
        if self._stop.is_set():
            return None
        claimed = self._claim_or_reclaim()
        if claimed is None:
            return None
        task_id, generation = claimed
        return task_id, self._drive_claimed(task_id, generation)

    def run(self, *, max_cycles: int = 100) -> int:
        if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not (1 <= max_cycles <= MAX_RUN_CYCLES):
            raise ValueError("V9_RUN_CYCLE_BOUND")
        completed = 0
        for _ in range(max_cycles):
            if self._stop.is_set():
                break
            result = self.step()
            if result is None:
                time.sleep(self.config.poll_seconds)
            else:
                completed += 1
        return completed
