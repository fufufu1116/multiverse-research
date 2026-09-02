#!/usr/bin/env python3
"""MULTIVERSE session-independent Orchestrator MVP candidate.

Candidate-only, single-process SQLite state machine. This module does not activate
production Runtime, call external providers, spend money, access secrets/protected
material, or mutate Stable/main. Role execution is adapter-driven; the built-in
ScriptedRoleWorker exists only for deterministic self-test/evidence generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

SCHEMA_VERSION = "MULTIVERSE_ORCHESTRATOR_MVP_v1"
DB_SCHEMA_VERSION = 1
DEFAULT_SEMANTIC_RETRY_BUDGET = 2  # initial attempt + 2 retries = 3 total attempts
DEFAULT_TRANSIENT_RETRY_BUDGET = 3
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 300  # aligns with existing Stage-1 5-minute lease
DEFAULT_DIFF_BUDGET_LINES = 500  # candidate-local MVP limit; not a global governance value
DEFAULT_EXECUTION_BUDGET_SECONDS = 300

STATES = (
    "PENDING",
    "IN_IMPLEMENT",
    "MECH_GATE_FAIL",
    "IN_LAB",
    "LAB_FIX_REQUIRED",
    "IN_AUDIT",
    "AUDIT_FIX_REQUIRED",
    "OWNER_GATE",
    "DONE",
    "ROLLED_BACK",
)
TERMINAL_STATES = {"OWNER_GATE", "DONE", "ROLLED_BACK"}
SAFE_FLAGS = (
    "candidate_only",
    "stable_production_effect",
    "secret_credential",
    "external_effect",
    "money_spend",
    "protected_data",
    "irreversible_operation",
    "authority_expansion",
    "unknown_risk",
)


class OrchestratorError(RuntimeError):
    pass


class TransientFailure(OrchestratorError):
    pass


class InjectedCrash(RuntimeError):
    pass


class RoleWorker(Protocol):
    def run(self, *, role: str, task: dict[str, Any], attempt: int) -> dict[str, Any]: ...


@dataclass(frozen=True)
class MechanicalResult:
    ok: bool
    code: str
    detail: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(stage: str, code: str, detail: str) -> str:
    payload = canonical_json({"stage": stage, "code": code, "detail": detail})
    return hashlib.sha256(payload.encode()).hexdigest()


def now_ts() -> float:
    return time.time()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise OrchestratorError(code)


def validate_safety(safety: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(safety, dict) or set(safety) != set(SAFE_FLAGS):
        return False, "SAFETY_SCHEMA_UNKNOWN"
    if safety["candidate_only"] is not True:
        return False, "NOT_CANDIDATE_ONLY"
    for key in (
        "stable_production_effect",
        "secret_credential",
        "external_effect",
        "money_spend",
        "protected_data",
        "irreversible_operation",
        "authority_expansion",
        "unknown_risk",
    ):
        if safety.get(key) is not False:
            return False, f"SAFETY_FAIL_CLOSED:{key}"
    return True, "SAFE_CANDIDATE_ONLY"


def validate_task_spec(spec: dict[str, Any]) -> None:
    required = {
        "schema_version", "task_id", "domain", "objective", "canonical_repo",
        "canonical_main", "candidate_branch", "candidate_head", "safety", "budgets",
    }
    require(isinstance(spec, dict) and set(spec) == required, "TASK_SCHEMA")
    require(spec["schema_version"] == SCHEMA_VERSION, "TASK_SCHEMA_VERSION")
    for key in (
        "task_id", "domain", "objective", "canonical_repo", "canonical_main",
        "candidate_branch", "candidate_head",
    ):
        require(isinstance(spec[key], str) and spec[key], f"TASK_{key.upper()}")
    require(
        len(spec["canonical_main"]) == 40
        and all(c in "0123456789abcdef" for c in spec["canonical_main"]),
        "CANONICAL_MAIN_SHA",
    )
    require(
        len(spec["candidate_head"]) == 40
        and all(c in "0123456789abcdef" for c in spec["candidate_head"]),
        "CANDIDATE_HEAD_SHA",
    )
    b = spec["budgets"]
    required_b = {
        "semantic_retry_budget", "transient_retry_budget", "diff_budget_lines",
        "execution_budget_seconds", "heartbeat_timeout_seconds", "cost_budget_microusd",
    }
    require(isinstance(b, dict) and set(b) == required_b, "BUDGET_SCHEMA")
    for key in required_b:
        require(
            isinstance(b[key], int) and not isinstance(b[key], bool) and b[key] >= 0,
            f"BUDGET_{key.upper()}",
        )
    require(
        b["semantic_retry_budget"] <= DEFAULT_SEMANTIC_RETRY_BUDGET,
        "SEMANTIC_RETRY_WIDENING_DENIED",
    )
    require(
        b["heartbeat_timeout_seconds"] <= DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
        "HEARTBEAT_TIMEOUT_WIDENING_DENIED",
    )
    require(b["cost_budget_microusd"] == 0, "MVP_SPEND_DENIED")


def default_budgets() -> dict[str, int]:
    return {
        "semantic_retry_budget": DEFAULT_SEMANTIC_RETRY_BUDGET,
        "transient_retry_budget": DEFAULT_TRANSIENT_RETRY_BUDGET,
        "diff_budget_lines": DEFAULT_DIFF_BUDGET_LINES,
        "execution_budget_seconds": DEFAULT_EXECUTION_BUDGET_SECONDS,
        "heartbeat_timeout_seconds": DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
        "cost_budget_microusd": 0,
    }


class OrchestratorStore:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._init()

    def close(self) -> None:
        self.conn.close()

    def _init(self) -> None:
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    spec_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    semantic_retry_count INTEGER NOT NULL DEFAULT 0,
                    transient_retry_count INTEGER NOT NULL DEFAULT 0,
                    last_failure_fp TEXT,
                    repeated_failure_count INTEGER NOT NULL DEFAULT 0,
                    active_step TEXT,
                    active_claim TEXT,
                    heartbeat_at REAL,
                    last_checkpoint TEXT,
                    result_json TEXT,
                    owner_gate_reason TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    state_before TEXT NOT NULL,
                    state_after TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )
            row = self.conn.execute("SELECT v FROM meta WHERE k='db_schema_version'").fetchone()
            if row is None:
                self.conn.execute(
                    "INSERT INTO meta(k,v) VALUES('db_schema_version',?)",
                    (str(DB_SCHEMA_VERSION),),
                )
            elif row[0] != str(DB_SCHEMA_VERSION):
                raise OrchestratorError("DB_SCHEMA_VERSION_MISMATCH")

    def create_task(self, spec: dict[str, Any]) -> None:
        validate_task_spec(spec)
        ts = now_ts()
        with self.conn:
            self.conn.execute(
                "INSERT INTO tasks(task_id,spec_json,state,created_at,updated_at) VALUES(?,?,?,?,?)",
                (spec["task_id"], canonical_json(spec), "PENDING", ts, ts),
            )
            self._event(
                spec["task_id"], "TASK_CREATED", "PENDING", "PENDING",
                {"domain": spec["domain"]}, ts,
            )

    def get(self, task_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise OrchestratorError("TASK_NOT_FOUND")
        out = dict(row)
        out["spec"] = json.loads(out.pop("spec_json"))
        out["result"] = json.loads(out["result_json"]) if out["result_json"] else None
        return out

    def _event(
        self,
        task_id: str,
        typ: str,
        before: str,
        after: str,
        payload: dict[str, Any],
        ts: float | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO events(task_id,event_type,state_before,state_after,payload_json,created_at) VALUES(?,?,?,?,?,?)",
            (task_id, typ, before, after, canonical_json(payload), now_ts() if ts is None else ts),
        )

    def transition(
        self,
        task_id: str,
        new_state: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        **updates: Any,
    ) -> None:
        require(new_state in STATES, "STATE_UNKNOWN")
        with self.conn:
            row = self.conn.execute("SELECT state FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise OrchestratorError("TASK_NOT_FOUND")
            before = row[0]
            sets = ["state=?", "updated_at=?"]
            vals: list[Any] = [new_state, now_ts()]
            allowed = {
                "semantic_retry_count", "transient_retry_count", "last_failure_fp",
                "repeated_failure_count", "active_step", "active_claim", "heartbeat_at",
                "last_checkpoint", "result_json", "owner_gate_reason",
            }
            for key, value in updates.items():
                require(key in allowed, f"UPDATE_FIELD:{key}")
                sets.append(f"{key}=?")
                vals.append(value)
            vals.append(task_id)
            self.conn.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE task_id=?",
                vals,
            )
            self._event(task_id, event_type, before, new_state, payload or {})

    def start_step(self, task_id: str, step: str) -> str:
        claim = uuid.uuid4().hex
        ts = now_ts()
        with self.conn:
            row = self.conn.execute(
                "SELECT state,active_claim FROM tasks WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise OrchestratorError("TASK_NOT_FOUND")
            require(row[1] is None, "ACTIVE_CLAIM_EXISTS")
            self.conn.execute(
                "UPDATE tasks SET active_step=?,active_claim=?,heartbeat_at=?,last_checkpoint=?,updated_at=? WHERE task_id=?",
                (step, claim, ts, f"STEP_START:{step}", ts, task_id),
            )
            self._event(
                task_id, "STEP_STARTED", row[0], row[0],
                {"step": step, "claim": claim}, ts,
            )
        return claim

    def finish_step(self, task_id: str, claim: str, checkpoint: str) -> None:
        ts = now_ts()
        with self.conn:
            row = self.conn.execute(
                "SELECT state,active_claim,active_step FROM tasks WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise OrchestratorError("TASK_NOT_FOUND")
            require(row[1] == claim, "STALE_STEP_CLAIM")
            self.conn.execute(
                "UPDATE tasks SET active_step=NULL,active_claim=NULL,heartbeat_at=?,last_checkpoint=?,updated_at=? WHERE task_id=?",
                (ts, checkpoint, ts, task_id),
            )
            self._event(
                task_id, "STEP_FINISHED", row[0], row[0],
                {"step": row[2], "checkpoint": checkpoint}, ts,
            )

    def recover_stale(self, *, at: float | None = None) -> list[str]:
        at = now_ts() if at is None else at
        recovered: list[str] = []
        rows = self.conn.execute(
            "SELECT task_id,state,active_claim,heartbeat_at,spec_json FROM tasks WHERE active_claim IS NOT NULL"
        ).fetchall()
        for row in rows:
            spec = json.loads(row["spec_json"])
            timeout = spec["budgets"]["heartbeat_timeout_seconds"]
            hb = row["heartbeat_at"]
            if hb is not None and at - hb >= timeout:
                with self.conn:
                    self.conn.execute(
                        "UPDATE tasks SET active_step=NULL,active_claim=NULL,last_checkpoint=?,updated_at=? WHERE task_id=?",
                        ("RECOVERED_STALE_STEP_REPLAY_SAFE", at, row["task_id"]),
                    )
                    self._event(
                        row["task_id"], "STALE_STEP_RECOVERED", row["state"], row["state"],
                        {"semantic_retry_consumed": False}, at,
                    )
                recovered.append(row["task_id"])
        return recovered

    def events(self, task_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE task_id=? ORDER BY id",
            (task_id,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            out.append(item)
        return out


class ScriptedRoleWorker:
    """Deterministic fixture worker. Never performs network/external/secret/spend actions."""

    def __init__(self, script: dict[str, list[dict[str, Any]]]) -> None:
        self.script = {key: list(value) for key, value in script.items()}
        self.calls: dict[str, int] = {}

    def run(self, *, role: str, task: dict[str, Any], attempt: int) -> dict[str, Any]:
        del task, attempt
        index = self.calls.get(role, 0)
        self.calls[role] = index + 1
        seq = self.script.get(role, [])
        if index >= len(seq):
            raise OrchestratorError(f"SCRIPT_EXHAUSTED:{role}")
        item = dict(seq[index])
        if item.get("raise") == "TRANSIENT":
            raise TransientFailure(item.get("detail", "TRANSIENT"))
        return item


def mechanical_gate(spec: dict[str, Any], implement_result: dict[str, Any]) -> MechanicalResult:
    safe, code = validate_safety(spec["safety"])
    if not safe:
        return MechanicalResult(False, code, "deterministic safety boundary")
    required = {"status", "diff_lines", "cost_microusd", "evidence_ref"}
    if not isinstance(implement_result, dict) or not required.issubset(implement_result):
        return MechanicalResult(
            False, "IMPLEMENT_RESULT_SCHEMA", "missing required implementation evidence"
        )
    if implement_result["status"] != "READY":
        return MechanicalResult(False, "IMPLEMENT_NOT_READY", str(implement_result.get("status")))
    budgets = spec["budgets"]
    if not isinstance(implement_result["diff_lines"], int) or implement_result["diff_lines"] < 0:
        return MechanicalResult(False, "DIFF_LINES_INVALID", "")
    if implement_result["diff_lines"] > budgets["diff_budget_lines"]:
        return MechanicalResult(
            False, "DIFF_BUDGET_EXCEEDED", str(implement_result["diff_lines"])
        )
    if not isinstance(implement_result["cost_microusd"], int) or implement_result["cost_microusd"] < 0:
        return MechanicalResult(False, "COST_INVALID", "")
    if implement_result["cost_microusd"] > budgets["cost_budget_microusd"]:
        return MechanicalResult(
            False, "COST_BUDGET_EXCEEDED", str(implement_result["cost_microusd"])
        )
    if not isinstance(implement_result["evidence_ref"], str) or not implement_result["evidence_ref"]:
        return MechanicalResult(False, "EVIDENCE_REF_MISSING", "")
    return MechanicalResult(True, "MECH_PASS", implement_result["evidence_ref"])


class Orchestrator:
    def __init__(self, store: OrchestratorStore, worker: RoleWorker) -> None:
        self.store = store
        self.worker = worker

    def _call_worker(
        self,
        task_id: str,
        role: str,
        attempt: int,
    ) -> tuple[dict[str, Any], float]:
        started = time.monotonic()
        out = self.worker.run(role=role, task=self.store.get(task_id), attempt=attempt)
        return out, time.monotonic() - started

    def rollback(self, task_id: str, reason: str) -> str:
        require(isinstance(reason, str) and bool(reason), "ROLLBACK_REASON")
        task = self.store.get(task_id)
        require(task["state"] not in TERMINAL_STATES, f"ROLLBACK_TERMINAL:{task['state']}")
        result = {
            "status": "ROLLED_BACK",
            "task_id": task_id,
            "domain": task["spec"]["domain"],
            "reason": reason,
            "production_or_stable_mutation": False,
        }
        self.store.transition(
            task_id,
            "ROLLED_BACK",
            "CANDIDATE_ROLLBACK",
            result,
            result_json=canonical_json(result),
            active_step=None,
            active_claim=None,
            last_checkpoint="ROLLED_BACK",
        )
        return "ROLLED_BACK"

    def _owner_gate(
        self,
        task_id: str,
        reason: str,
        detail: str,
        history: list[str] | None = None,
    ) -> None:
        summary = {
            "attempted": "automatic candidate task progression",
            "succeeded": self.store.get(task_id)["last_checkpoint"] or "NONE",
            "failed": detail or reason,
            "auto_fix_history": history or [],
            "why_cannot_continue": reason,
            "owner_decision_one_point": (
                "continue only if this boundary should be explicitly widened or task should stop"
            ),
        }
        self.store.transition(
            task_id,
            "OWNER_GATE",
            "OWNER_GATE_REQUIRED",
            {"reason": reason},
            owner_gate_reason=reason,
            result_json=canonical_json(summary),
            active_step=None,
            active_claim=None,
        )

    def _semantic_fail(
        self,
        task_id: str,
        stage: str,
        code: str,
        detail: str,
        fail_state: str,
    ) -> None:
        task = self.store.get(task_id)
        fp = fingerprint(stage, code, detail)
        repeated = (
            task["repeated_failure_count"] + 1
            if task["last_failure_fp"] == fp
            else 1
        )
        retries = task["semantic_retry_count"] + 1
        if repeated >= 2:
            self._owner_gate(
                task_id,
                "REPEATED_FAILURE_FINGERPRINT",
                f"{stage}:{code}:{detail}",
                [fp],
            )
            return
        if retries > task["spec"]["budgets"]["semantic_retry_budget"]:
            self._owner_gate(
                task_id,
                "SEMANTIC_RETRY_BUDGET_EXHAUSTED",
                f"{stage}:{code}:{detail}",
                [fp],
            )
            return
        self.store.transition(
            task_id,
            fail_state,
            f"{stage}_FIX_REQUIRED",
            {"code": code, "detail": detail, "fingerprint": fp},
            semantic_retry_count=retries,
            last_failure_fp=fp,
            repeated_failure_count=repeated,
            active_step=None,
            active_claim=None,
            last_checkpoint=f"{stage}_FAIL:{code}",
        )

    def _transient_fail(self, task_id: str, stage: str, detail: str) -> None:
        task = self.store.get(task_id)
        count = task["transient_retry_count"] + 1
        if count > task["spec"]["budgets"]["transient_retry_budget"]:
            self._owner_gate(
                task_id,
                "TRANSIENT_RETRY_BUDGET_EXHAUSTED",
                f"{stage}:{detail}",
            )
            return
        self.store.transition(
            task_id,
            task["state"],
            "TRANSIENT_FAILURE_CHECKPOINTED",
            {"stage": stage, "detail": detail, "semantic_retry_consumed": False},
            transient_retry_count=count,
            active_step=None,
            active_claim=None,
            last_checkpoint=f"TRANSIENT:{stage}",
        )

    def step(self, task_id: str, *, crash_after_start: str | None = None) -> str:
        task = self.store.get(task_id)
        state = task["state"]
        spec = task["spec"]
        if state in TERMINAL_STATES:
            return state
        safe, reason = validate_safety(spec["safety"])
        if not safe:
            self._owner_gate(task_id, reason, "deterministic safety gate denied")
            return "OWNER_GATE"

        if state in {"PENDING", "MECH_GATE_FAIL", "LAB_FIX_REQUIRED", "AUDIT_FIX_REQUIRED"}:
            self.store.transition(task_id, "IN_IMPLEMENT", "ENTER_IMPLEMENT", {"from": state})
            state = "IN_IMPLEMENT"
            task = self.store.get(task_id)

        if state == "IN_IMPLEMENT":
            claim = self.store.start_step(task_id, "IMPLEMENT")
            if crash_after_start == "IMPLEMENT":
                raise InjectedCrash("IMPLEMENT")
            try:
                out, elapsed = self._call_worker(
                    task_id, "IMPLEMENT", task["semantic_retry_count"] + 1
                )
            except TransientFailure as exc:
                self._transient_fail(task_id, "IMPLEMENT", str(exc))
                return self.store.get(task_id)["state"]
            self.store.finish_step(task_id, claim, "IMPLEMENT_RESULT_CAPTURED")
            if elapsed > spec["budgets"]["execution_budget_seconds"]:
                self._semantic_fail(
                    task_id,
                    "MECH",
                    "EXECUTION_TIME_BUDGET_EXCEEDED",
                    f"elapsed={elapsed:.6f}",
                    "MECH_GATE_FAIL",
                )
                return self.store.get(task_id)["state"]
            mech = mechanical_gate(spec, out)
            if not mech.ok:
                self._semantic_fail(
                    task_id, "MECH", mech.code, mech.detail, "MECH_GATE_FAIL"
                )
                return self.store.get(task_id)["state"]
            self.store.transition(
                task_id,
                "IN_LAB",
                "MECHANICAL_GATE_PASS",
                {"evidence_ref": mech.detail},
                last_checkpoint="MECHANICAL_GATE_PASS",
            )
            return "IN_LAB"

        if state == "IN_LAB":
            claim = self.store.start_step(task_id, "LAB")
            if crash_after_start == "LAB":
                raise InjectedCrash("LAB")
            try:
                out, elapsed = self._call_worker(
                    task_id, "LAB", task["semantic_retry_count"] + 1
                )
            except TransientFailure as exc:
                self._transient_fail(task_id, "LAB", str(exc))
                return self.store.get(task_id)["state"]
            self.store.finish_step(task_id, claim, "LAB_RESULT_CAPTURED")
            if elapsed > spec["budgets"]["execution_budget_seconds"]:
                self._semantic_fail(
                    task_id,
                    "LAB",
                    "EXECUTION_TIME_BUDGET_EXCEEDED",
                    f"elapsed={elapsed:.6f}",
                    "LAB_FIX_REQUIRED",
                )
                return self.store.get(task_id)["state"]
            verdict = out.get("verdict")
            if verdict == "PASS":
                self.store.transition(
                    task_id,
                    "IN_AUDIT",
                    "LAB_PASS",
                    {"evidence_ref": out.get("evidence_ref")},
                    last_checkpoint="LAB_PASS",
                    repeated_failure_count=0,
                    last_failure_fp=None,
                )
                return "IN_AUDIT"
            if verdict == "FIX_REQUIRED":
                self._semantic_fail(
                    task_id,
                    "LAB",
                    str(out.get("code", "FIX_REQUIRED")),
                    str(out.get("detail", "")),
                    "LAB_FIX_REQUIRED",
                )
                return self.store.get(task_id)["state"]
            self._owner_gate(
                task_id, "LAB_UNPARSABLE_OR_MATERIAL_BLOCK", canonical_json(out)
            )
            return "OWNER_GATE"

        if state == "IN_AUDIT":
            claim = self.store.start_step(task_id, "AUDIT")
            if crash_after_start == "AUDIT":
                raise InjectedCrash("AUDIT")
            try:
                out, elapsed = self._call_worker(
                    task_id, "AUDIT", task["semantic_retry_count"] + 1
                )
            except TransientFailure as exc:
                self._transient_fail(task_id, "AUDIT", str(exc))
                return self.store.get(task_id)["state"]
            self.store.finish_step(task_id, claim, "AUDIT_RESULT_CAPTURED")
            if elapsed > spec["budgets"]["execution_budget_seconds"]:
                self._semantic_fail(
                    task_id,
                    "AUDIT",
                    "EXECUTION_TIME_BUDGET_EXCEEDED",
                    f"elapsed={elapsed:.6f}",
                    "AUDIT_FIX_REQUIRED",
                )
                return self.store.get(task_id)["state"]
            verdict = out.get("verdict")
            if verdict == "PASS":
                result = {
                    "status": "DONE",
                    "task_id": task_id,
                    "domain": spec["domain"],
                    "owner_copy_paste_count": 0,
                    "owner_continue_prompt_count": 0,
                    "owner_keep_alive_count": 0,
                    "semantic_retries": self.store.get(task_id)["semantic_retry_count"],
                    "transient_retries": self.store.get(task_id)["transient_retry_count"],
                    "audit_evidence_ref": out.get("evidence_ref"),
                }
                self.store.transition(
                    task_id,
                    "DONE",
                    "AUDITOR_PASS_DONE",
                    result,
                    result_json=canonical_json(result),
                    last_checkpoint="DONE",
                    repeated_failure_count=0,
                    last_failure_fp=None,
                )
                return "DONE"
            if verdict == "FIX_REQUIRED":
                self._semantic_fail(
                    task_id,
                    "AUDIT",
                    str(out.get("code", "FIX_REQUIRED")),
                    str(out.get("detail", "")),
                    "AUDIT_FIX_REQUIRED",
                )
                return self.store.get(task_id)["state"]
            self._owner_gate(
                task_id, "AUDIT_UNPARSABLE_OR_MATERIAL_BLOCK", canonical_json(out)
            )
            return "OWNER_GATE"

        raise OrchestratorError(f"UNHANDLED_STATE:{state}")

    def run_until_terminal(self, task_id: str, *, max_steps: int = 50) -> str:
        for _ in range(max_steps):
            state = self.store.get(task_id)["state"]
            if state in TERMINAL_STATES:
                return state
            self.step(task_id)
        self._owner_gate(task_id, "ORCHESTRATOR_STEP_CEILING", f"max_steps={max_steps}")
        return self.store.get(task_id)["state"]


def demo_spec(task_id: str = "demo-task-1") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "domain": "DEMO_DOMAIN_NEUTRAL",
        "objective": "prove bounded automatic implement-review-fix-review completion",
        "canonical_repo": "fufufu1116/multiverse-research",
        "canonical_main": "5c1403c1f5aabb80d29e8c868440aede8888ce61",
        "candidate_branch": "agent/automation-orchestrator-mvp-20260902-v1",
        "candidate_head": "6c71b952173ab21bf1f23825e0abff84ce4b78c4",
        "safety": {
            "candidate_only": True,
            "stable_production_effect": False,
            "secret_credential": False,
            "external_effect": False,
            "money_spend": False,
            "protected_data": False,
            "irreversible_operation": False,
            "authority_expansion": False,
            "unknown_risk": False,
        },
        "budgets": default_budgets(),
    }


def run_demo(db_path: pathlib.Path) -> dict[str, Any]:
    spec = demo_spec()
    worker = ScriptedRoleWorker(
        {
            "IMPLEMENT": [
                {
                    "status": "READY",
                    "diff_lines": 20,
                    "cost_microusd": 0,
                    "evidence_ref": "demo-impl-v1",
                },
                {
                    "status": "READY",
                    "diff_lines": 22,
                    "cost_microusd": 0,
                    "evidence_ref": "demo-impl-v2",
                },
            ],
            "LAB": [
                {
                    "verdict": "FIX_REQUIRED",
                    "code": "DEMO_FIX",
                    "detail": "first pass catches deterministic issue",
                    "evidence_ref": "demo-lab-fix",
                },
                {"verdict": "PASS", "evidence_ref": "demo-lab-pass"},
            ],
            "AUDIT": [{"verdict": "PASS", "evidence_ref": "demo-audit-pass"}],
        }
    )
    store = OrchestratorStore(db_path)
    try:
        store.create_task(spec)
        final = Orchestrator(store, worker).run_until_terminal(spec["task_id"])
        return {
            "final_state": final,
            "task": store.get(spec["task_id"]),
            "events": store.events(spec["task_id"]),
        }
    finally:
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-db")
    args = parser.parse_args()
    if args.demo_db:
        result = run_demo(pathlib.Path(args.demo_db))
        print(canonical_json(result))
        return 0 if result["final_state"] == "DONE" else 92
    parser.error("use --demo-db")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
