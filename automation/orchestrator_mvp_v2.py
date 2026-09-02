#!/usr/bin/env python3
"""MULTIVERSE session-independent Orchestrator MVP v2 candidate.

Candidate-only orchestration with deterministic safety/budget gates, SQLite state,
bounded retries, process-isolated role execution with hard timeout/heartbeat, and a
stable idempotency operation key that survives crash recovery. This file grants no
production authority and includes no live provider adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import pathlib
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

SCHEMA_VERSION = "MULTIVERSE_ORCHESTRATOR_MVP_v2"
DB_SCHEMA_VERSION = 2
MAX_SEMANTIC_RETRY_BUDGET = 2  # initial attempt + 2 remediation retries
MAX_TRANSIENT_RETRY_BUDGET = 3
MAX_HEARTBEAT_TIMEOUT_SECONDS = 300
MAX_DIFF_BUDGET_LINES = 500
MAX_EXECUTION_BUDGET_SECONDS = 300
MVP_COST_BUDGET_MICROUSD = 0

STATES = (
    "PENDING", "IN_IMPLEMENT", "MECH_GATE_FAIL", "IN_LAB", "LAB_FIX_REQUIRED",
    "IN_AUDIT", "AUDIT_FIX_REQUIRED", "OWNER_GATE", "DONE", "ROLLED_BACK",
)
TERMINAL_STATES = {"OWNER_GATE", "DONE", "ROLLED_BACK"}
SAFE_FLAGS = (
    "candidate_only", "stable_production_effect", "secret_credential",
    "external_effect", "money_spend", "protected_data", "irreversible_operation",
    "authority_expansion", "unknown_risk",
)


class OrchestratorError(RuntimeError): pass
class TransientFailure(OrchestratorError): pass
class InjectedCrash(RuntimeError): pass
class WorkerTimeout(OrchestratorError): pass
class WorkerFailure(OrchestratorError): pass


class RoleWorker(Protocol):
    replay_safe: bool
    def run(
        self, *, role: str, task: dict[str, Any], operation_key: str,
        semantic_attempt: int, transient_attempt: int,
    ) -> dict[str, Any]: ...


class BindingVerifier(Protocol):
    def verify(self, spec: dict[str, Any]) -> tuple[bool, str]: ...


@dataclass(frozen=True)
class StaticBindingVerifier:
    observed_main: str
    observed_candidate_head: str
    def verify(self, spec: dict[str, Any]) -> tuple[bool, str]:
        if spec["canonical_main"] != self.observed_main:
            return False, "CANONICAL_MAIN_BINDING_MISMATCH"
        if spec["candidate_head"] != self.observed_candidate_head:
            return False, "CANDIDATE_HEAD_BINDING_MISMATCH"
        return True, "BINDING_OK"


@dataclass(frozen=True)
class MechanicalResult:
    ok: bool
    code: str
    detail: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(stage: str, code: str, detail: str) -> str:
    return hashlib.sha256(canonical_json({"stage": stage, "code": code, "detail": detail}).encode()).hexdigest()


def now_ts() -> float: return time.time()

def require(cond: bool, code: str) -> None:
    if not cond: raise OrchestratorError(code)


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def validate_safety_shape(safety: Any) -> None:
    require(isinstance(safety, dict) and set(safety) == set(SAFE_FLAGS), "SAFETY_SCHEMA_UNKNOWN")
    for key in SAFE_FLAGS:
        require(isinstance(safety[key], bool), f"SAFETY_BOOL:{key}")


def validate_safety(safety: dict[str, Any]) -> tuple[bool, str]:
    validate_safety_shape(safety)
    if safety["candidate_only"] is not True: return False, "NOT_CANDIDATE_ONLY"
    for key in SAFE_FLAGS[1:]:
        if safety[key] is not False: return False, f"SAFETY_FAIL_CLOSED:{key}"
    return True, "SAFE_CANDIDATE_ONLY"


def default_budgets() -> dict[str, int]:
    return {
        "semantic_retry_budget": MAX_SEMANTIC_RETRY_BUDGET,
        "transient_retry_budget": MAX_TRANSIENT_RETRY_BUDGET,
        "diff_budget_lines": MAX_DIFF_BUDGET_LINES,
        "execution_budget_seconds": MAX_EXECUTION_BUDGET_SECONDS,
        "heartbeat_timeout_seconds": MAX_HEARTBEAT_TIMEOUT_SECONDS,
        "cost_budget_microusd": MVP_COST_BUDGET_MICROUSD,
    }


def validate_task_spec(spec: dict[str, Any]) -> None:
    required = {
        "schema_version", "task_id", "domain", "objective", "canonical_repo",
        "canonical_main", "candidate_branch", "candidate_head", "safety", "budgets",
    }
    require(isinstance(spec, dict) and set(spec) == required, "TASK_SCHEMA")
    require(spec["schema_version"] == SCHEMA_VERSION, "TASK_SCHEMA_VERSION")
    for key in ("task_id", "domain", "objective", "canonical_repo", "candidate_branch"):
        require(isinstance(spec[key], str) and bool(spec[key]), f"TASK_{key.upper()}")
    require(spec["canonical_repo"].count("/") == 1, "CANONICAL_REPO")
    require(_sha40(spec["canonical_main"]), "CANONICAL_MAIN_SHA")
    require(_sha40(spec["candidate_head"]), "CANDIDATE_HEAD_SHA")
    require(spec["candidate_branch"] not in {"main", "master"}, "CANDIDATE_BRANCH_REQUIRED")
    validate_safety_shape(spec["safety"])
    b = spec["budgets"]
    expected = set(default_budgets())
    require(isinstance(b, dict) and set(b) == expected, "BUDGET_SCHEMA")
    for key in expected:
        require(isinstance(b[key], int) and not isinstance(b[key], bool) and b[key] >= 0, f"BUDGET_{key.upper()}")
    require(b["semantic_retry_budget"] <= MAX_SEMANTIC_RETRY_BUDGET, "SEMANTIC_RETRY_WIDENING_DENIED")
    require(b["transient_retry_budget"] <= MAX_TRANSIENT_RETRY_BUDGET, "TRANSIENT_RETRY_WIDENING_DENIED")
    require(b["diff_budget_lines"] <= MAX_DIFF_BUDGET_LINES, "DIFF_BUDGET_WIDENING_DENIED")
    require(b["execution_budget_seconds"] <= MAX_EXECUTION_BUDGET_SECONDS, "EXECUTION_BUDGET_WIDENING_DENIED")
    require(b["heartbeat_timeout_seconds"] <= MAX_HEARTBEAT_TIMEOUT_SECONDS, "HEARTBEAT_TIMEOUT_WIDENING_DENIED")
    require(b["cost_budget_microusd"] == MVP_COST_BUDGET_MICROUSD, "MVP_SPEND_DENIED")


def operation_key(task_id: str, role: str, semantic_retry_count: int) -> str:
    raw = canonical_json({"task_id": task_id, "role": role, "semantic_generation": semantic_retry_count})
    return "op-" + hashlib.sha256(raw.encode()).hexdigest()[:24]


class OrchestratorStore:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._init()

    def close(self) -> None: self.conn.close()

    def _init(self) -> None:
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, spec_json TEXT NOT NULL, state TEXT NOT NULL,
                semantic_retry_count INTEGER NOT NULL DEFAULT 0,
                transient_retry_count INTEGER NOT NULL DEFAULT 0,
                last_failure_fp TEXT, repeated_failure_count INTEGER NOT NULL DEFAULT 0,
                active_role TEXT, active_claim TEXT, active_operation_key TEXT,
                heartbeat_at REAL, last_checkpoint TEXT, result_json TEXT,
                owner_gate_reason TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL
            )""")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                event_type TEXT NOT NULL, state_before TEXT NOT NULL, state_after TEXT NOT NULL,
                payload_json TEXT NOT NULL, created_at REAL NOT NULL
            )""")
            row = self.conn.execute("SELECT v FROM meta WHERE k='db_schema_version'").fetchone()
            if row is None:
                self.conn.execute("INSERT INTO meta(k,v) VALUES('db_schema_version',?)", (str(DB_SCHEMA_VERSION),))
            elif row[0] != str(DB_SCHEMA_VERSION):
                raise OrchestratorError("DB_SCHEMA_VERSION_MISMATCH")

    def _event(self, task_id: str, typ: str, before: str, after: str, payload: dict[str, Any], ts: float | None = None) -> None:
        self.conn.execute(
            "INSERT INTO events(task_id,event_type,state_before,state_after,payload_json,created_at) VALUES(?,?,?,?,?,?)",
            (task_id, typ, before, after, canonical_json(payload), now_ts() if ts is None else ts),
        )

    def create_task(self, spec: dict[str, Any]) -> None:
        validate_task_spec(spec)
        ts = now_ts()
        with self.conn:
            self.conn.execute(
                "INSERT INTO tasks(task_id,spec_json,state,created_at,updated_at) VALUES(?,?,?,?,?)",
                (spec["task_id"], canonical_json(spec), "PENDING", ts, ts),
            )
            self._event(spec["task_id"], "TASK_CREATED", "PENDING", "PENDING", {"domain": spec["domain"]}, ts)

    def get(self, task_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None: raise OrchestratorError("TASK_NOT_FOUND")
        out = dict(row)
        out["spec"] = json.loads(out.pop("spec_json"))
        out["result"] = json.loads(out["result_json"]) if out["result_json"] else None
        return out

    def transition(self, task_id: str, new_state: str, event_type: str, payload: dict[str, Any] | None = None, **updates: Any) -> None:
        require(new_state in STATES, "STATE_UNKNOWN")
        allowed = {
            "semantic_retry_count", "transient_retry_count", "last_failure_fp",
            "repeated_failure_count", "active_role", "active_claim", "active_operation_key",
            "heartbeat_at", "last_checkpoint", "result_json", "owner_gate_reason",
        }
        with self.conn:
            row = self.conn.execute("SELECT state FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None: raise OrchestratorError("TASK_NOT_FOUND")
            before = row[0]
            sets = ["state=?", "updated_at=?"]
            vals: list[Any] = [new_state, now_ts()]
            for key, value in updates.items():
                require(key in allowed, f"UPDATE_FIELD:{key}")
                sets.append(f"{key}=?"); vals.append(value)
            vals.append(task_id)
            self.conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE task_id=?", vals)
            self._event(task_id, event_type, before, new_state, payload or {})

    def start_step(self, task_id: str, role: str, op_key: str) -> str:
        claim = uuid.uuid4().hex; ts = now_ts()
        with self.conn:
            row = self.conn.execute("SELECT state,active_claim FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None: raise OrchestratorError("TASK_NOT_FOUND")
            require(row[1] is None, "ACTIVE_CLAIM_EXISTS")
            self.conn.execute(
                "UPDATE tasks SET active_role=?,active_claim=?,active_operation_key=?,heartbeat_at=?,last_checkpoint=?,updated_at=? WHERE task_id=?",
                (role, claim, op_key, ts, f"STEP_START:{role}:{op_key}", ts, task_id),
            )
            self._event(task_id, "STEP_STARTED", row[0], row[0], {"role": role, "claim": claim, "operation_key": op_key}, ts)
        return claim

    def heartbeat(self, task_id: str, claim: str) -> None:
        ts = now_ts()
        with self.conn:
            row = self.conn.execute("SELECT state,active_claim FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None: raise OrchestratorError("TASK_NOT_FOUND")
            require(row[1] == claim, "STALE_STEP_CLAIM")
            self.conn.execute("UPDATE tasks SET heartbeat_at=?,updated_at=? WHERE task_id=?", (ts, ts, task_id))

    def finish_step(self, task_id: str, claim: str, checkpoint: str) -> None:
        ts = now_ts()
        with self.conn:
            row = self.conn.execute("SELECT state,active_claim,active_role,active_operation_key FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None: raise OrchestratorError("TASK_NOT_FOUND")
            require(row[1] == claim, "STALE_STEP_CLAIM")
            self.conn.execute(
                "UPDATE tasks SET active_role=NULL,active_claim=NULL,active_operation_key=NULL,heartbeat_at=?,last_checkpoint=?,updated_at=? WHERE task_id=?",
                (ts, checkpoint, ts, task_id),
            )
            self._event(task_id, "STEP_FINISHED", row[0], row[0], {"role": row[2], "operation_key": row[3], "checkpoint": checkpoint}, ts)

    def recover_stale(self, *, at: float | None = None) -> list[str]:
        at = now_ts() if at is None else at; recovered: list[str] = []
        rows = self.conn.execute("SELECT task_id,state,active_claim,active_operation_key,heartbeat_at,spec_json FROM tasks WHERE active_claim IS NOT NULL").fetchall()
        for row in rows:
            spec = json.loads(row["spec_json"]); hb = row["heartbeat_at"]
            if hb is not None and at - hb >= spec["budgets"]["heartbeat_timeout_seconds"]:
                with self.conn:
                    self.conn.execute(
                        "UPDATE tasks SET active_role=NULL,active_claim=NULL,active_operation_key=NULL,last_checkpoint=?,updated_at=? WHERE task_id=?",
                        (f"RECOVERED_STALE_REPLAY:{row['active_operation_key']}", at, row["task_id"]),
                    )
                    self._event(row["task_id"], "STALE_STEP_RECOVERED", row["state"], row["state"], {"operation_key": row["active_operation_key"], "semantic_retry_consumed": False}, at)
                recovered.append(row["task_id"])
        return recovered

    def events(self, task_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        out = []
        for row in rows:
            item = dict(row); item["payload"] = json.loads(item.pop("payload_json")); out.append(item)
        return out


class DurableScriptedRoleWorker:
    """Deterministic replay-safe fixture with durable per-operation receipts."""
    replay_safe = True
    def __init__(self, receipt_db: pathlib.Path, script: dict[str, dict[str, dict[str, Any]]]) -> None:
        self.receipt_db = str(receipt_db); self.script = script
        conn = sqlite3.connect(self.receipt_db)
        with conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("CREATE TABLE IF NOT EXISTS receipts(operation_key TEXT PRIMARY KEY,result_json TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS executions(operation_key TEXT PRIMARY KEY,count INTEGER NOT NULL)")
        conn.close()

    def run(self, *, role: str, task: dict[str, Any], operation_key: str, semantic_attempt: int, transient_attempt: int) -> dict[str, Any]:
        del task
        conn = sqlite3.connect(self.receipt_db)
        row = conn.execute("SELECT result_json FROM receipts WHERE operation_key=?", (operation_key,)).fetchone()
        if row is not None:
            conn.close(); return json.loads(row[0])
        role_script = self.script.get(role, {})
        item = role_script.get(f"{semantic_attempt}:{transient_attempt}") or role_script.get(f"{semantic_attempt}:*")
        if item is None:
            conn.close(); raise WorkerFailure(f"SCRIPT_EXHAUSTED:{role}:{semantic_attempt}:{transient_attempt}")
        item = dict(item)
        sleep_s = float(item.pop("sleep_seconds", 0.0))
        if sleep_s > 0: time.sleep(sleep_s)
        if item.get("raise") == "TRANSIENT":
            conn.close(); raise TransientFailure(str(item.get("detail", "TRANSIENT")))
        with conn:
            existing = conn.execute("SELECT result_json FROM receipts WHERE operation_key=?", (operation_key,)).fetchone()
            if existing is None:
                conn.execute("INSERT INTO receipts(operation_key,result_json) VALUES(?,?)", (operation_key, canonical_json(item)))
                conn.execute("INSERT OR REPLACE INTO executions(operation_key,count) VALUES(?,1)", (operation_key,))
                out = item
            else:
                out = json.loads(existing[0])
        conn.close(); return out

    def execution_count(self, op_key: str) -> int:
        conn = sqlite3.connect(self.receipt_db)
        row = conn.execute("SELECT count FROM executions WHERE operation_key=?", (op_key,)).fetchone()
        conn.close(); return 0 if row is None else int(row[0])


def mechanical_gate(spec: dict[str, Any], implement_result: dict[str, Any]) -> MechanicalResult:
    safe, code = validate_safety(spec["safety"])
    if not safe: return MechanicalResult(False, code, "deterministic safety boundary")
    required = {"status", "candidate_head", "diff_lines", "cost_microusd", "evidence_ref"}
    if not isinstance(implement_result, dict) or not required.issubset(implement_result):
        return MechanicalResult(False, "IMPLEMENT_RESULT_SCHEMA", "missing required implementation evidence")
    if implement_result["candidate_head"] != spec["candidate_head"]:
        return MechanicalResult(False, "IMPLEMENT_HEAD_MISMATCH", "implementation result not bound to candidate head")
    if implement_result["status"] != "READY": return MechanicalResult(False, "IMPLEMENT_NOT_READY", str(implement_result.get("status")))
    b = spec["budgets"]
    if not isinstance(implement_result["diff_lines"], int) or isinstance(implement_result["diff_lines"], bool) or implement_result["diff_lines"] < 0:
        return MechanicalResult(False, "DIFF_LINES_INVALID", "")
    if implement_result["diff_lines"] > b["diff_budget_lines"]: return MechanicalResult(False, "DIFF_BUDGET_EXCEEDED", str(implement_result["diff_lines"]))
    if not isinstance(implement_result["cost_microusd"], int) or isinstance(implement_result["cost_microusd"], bool) or implement_result["cost_microusd"] < 0:
        return MechanicalResult(False, "COST_INVALID", "")
    if implement_result["cost_microusd"] > b["cost_budget_microusd"]: return MechanicalResult(False, "COST_BUDGET_EXCEEDED", str(implement_result["cost_microusd"]))
    if not isinstance(implement_result["evidence_ref"], str) or not implement_result["evidence_ref"]: return MechanicalResult(False, "EVIDENCE_REF_MISSING", "")
    return MechanicalResult(True, "MECH_PASS", implement_result["evidence_ref"])


def validate_review_result(role: str, spec: dict[str, Any], out: Any) -> tuple[bool, str]:
    if not isinstance(out, dict): return False, f"{role}_RESULT_SCHEMA"
    if out.get("reviewed_head") != spec["candidate_head"]: return False, f"{role}_REVIEW_HEAD_MISMATCH"
    if not isinstance(out.get("evidence_ref"), str) or not out.get("evidence_ref"): return False, f"{role}_EVIDENCE_REF_MISSING"
    return True, "OK"


def _child_entry(worker: RoleWorker, kwargs: dict[str, Any], q: Any) -> None:
    try:
        q.put(("OK", worker.run(**kwargs)))
    except TransientFailure as exc:
        q.put(("TRANSIENT", str(exc)))
    except BaseException as exc:
        q.put(("ERROR", f"{type(exc).__name__}:{exc}"))


class Orchestrator:
    def __init__(self, store: OrchestratorStore, worker: RoleWorker, binding: BindingVerifier) -> None:
        require(getattr(worker, "replay_safe", False) is True, "WORKER_REPLAY_SAFETY_REQUIRED")
        self.store = store; self.worker = worker; self.binding = binding

    def _owner_gate(self, task_id: str, reason: str, summary_code: str, history: list[str] | None = None) -> None:
        prior = self.store.get(task_id)
        summary = {
            "attempted": "automatic candidate task progression",
            "succeeded": prior["last_checkpoint"] or "NONE",
            "failed": summary_code[:240],
            "auto_fix_history": list(history or [])[:3],
            "why_cannot_continue": reason,
            "owner_decision_one_point": "decide whether to widen this exact boundary or stop the task",
        }
        self.store.transition(task_id, "OWNER_GATE", "OWNER_GATE_REQUIRED", {"reason": reason}, owner_gate_reason=reason, result_json=canonical_json(summary), active_role=None, active_claim=None, active_operation_key=None)

    def _semantic_fail(self, task_id: str, stage: str, code: str, detail: str, fail_state: str) -> None:
        task = self.store.get(task_id); fp = fingerprint(stage, code, detail)
        repeated = task["repeated_failure_count"] + 1 if task["last_failure_fp"] == fp else 1
        retries = task["semantic_retry_count"] + 1
        if repeated >= 2:
            self._owner_gate(task_id, "REPEATED_FAILURE_FINGERPRINT", f"{stage}:{code}", [fp]); return
        if retries > task["spec"]["budgets"]["semantic_retry_budget"]:
            self._owner_gate(task_id, "SEMANTIC_RETRY_BUDGET_EXHAUSTED", f"{stage}:{code}", [fp]); return
        self.store.transition(task_id, fail_state, f"{stage}_FIX_REQUIRED", {"code": code, "fingerprint": fp}, semantic_retry_count=retries, last_failure_fp=fp, repeated_failure_count=repeated, active_role=None, active_claim=None, active_operation_key=None, last_checkpoint=f"{stage}_FAIL:{code}")

    def _transient_fail(self, task_id: str, stage: str, detail: str) -> None:
        task = self.store.get(task_id); count = task["transient_retry_count"] + 1
        if count > task["spec"]["budgets"]["transient_retry_budget"]:
            self._owner_gate(task_id, "TRANSIENT_RETRY_BUDGET_EXHAUSTED", f"{stage}:TRANSIENT"); return
        self.store.transition(task_id, task["state"], "TRANSIENT_FAILURE_CHECKPOINTED", {"stage": stage, "semantic_retry_consumed": False}, transient_retry_count=count, active_role=None, active_claim=None, active_operation_key=None, last_checkpoint=f"TRANSIENT:{stage}")

    def _execute_role(self, task_id: str, role: str, claim: str, op_key: str) -> dict[str, Any]:
        task = self.store.get(task_id); spec = task["spec"]
        semantic_attempt = task["semantic_retry_count"] + 1
        transient_attempt = task["transient_retry_count"] + 1
        kwargs = {"role": role, "task": task, "operation_key": op_key, "semantic_attempt": semantic_attempt, "transient_attempt": transient_attempt}
        ctx = mp.get_context("spawn"); q = ctx.Queue(); proc = ctx.Process(target=_child_entry, args=(self.worker, kwargs, q))
        proc.start(); started = time.monotonic(); last_hb = started
        budget = spec["budgets"]["execution_budget_seconds"]
        while proc.is_alive():
            elapsed = time.monotonic() - started
            if elapsed > budget:
                proc.terminate(); proc.join(2)
                raise WorkerTimeout(f"{role}_EXECUTION_TIME_BUDGET_EXCEEDED")
            if time.monotonic() - last_hb >= 0.05:
                self.store.heartbeat(task_id, claim); last_hb = time.monotonic()
            proc.join(0.02)
        proc.join()
        if q.empty(): raise WorkerFailure(f"{role}_NO_RESULT")
        kind, payload = q.get()
        if kind == "TRANSIENT": raise TransientFailure(str(payload))
        if kind != "OK": raise WorkerFailure(str(payload))
        require(isinstance(payload, dict), f"{role}_RESULT_NOT_OBJECT")
        return payload

    def rollback(self, task_id: str, reason: str) -> str:
        require(isinstance(reason, str) and bool(reason), "ROLLBACK_REASON")
        task = self.store.get(task_id); require(task["state"] not in TERMINAL_STATES, f"ROLLBACK_TERMINAL:{task['state']}")
        result = {"status": "ROLLED_BACK", "task_id": task_id, "domain": task["spec"]["domain"], "reason": reason, "production_or_stable_mutation": False}
        self.store.transition(task_id, "ROLLED_BACK", "CANDIDATE_ROLLBACK", result, result_json=canonical_json(result), active_role=None, active_claim=None, active_operation_key=None, last_checkpoint="ROLLED_BACK")
        return "ROLLED_BACK"

    def _binding_and_safety(self, task_id: str) -> bool:
        task = self.store.get(task_id); spec = task["spec"]
        ok, code = self.binding.verify(spec)
        if not ok:
            self._owner_gate(task_id, code, code); return False
        safe, code = validate_safety(spec["safety"])
        if not safe:
            self._owner_gate(task_id, code, code); return False
        return True

    def _run_claimed(self, task_id: str, role: str, *, crash_after_worker_return: bool = False) -> tuple[dict[str, Any] | None, str]:
        task = self.store.get(task_id); op_key = operation_key(task_id, role, task["semantic_retry_count"])
        claim = self.store.start_step(task_id, role, op_key)
        try:
            out = self._execute_role(task_id, role, claim, op_key)
        except TransientFailure as exc:
            self._transient_fail(task_id, role, str(exc)); return None, "TRANSIENT"
        except WorkerTimeout:
            self._semantic_fail(task_id, role, "EXECUTION_TIME_BUDGET_EXCEEDED", "hard process timeout", {"IMPLEMENT":"MECH_GATE_FAIL","LAB":"LAB_FIX_REQUIRED","AUDIT":"AUDIT_FIX_REQUIRED"}[role]); return None, "TIMEOUT"
        except WorkerFailure:
            self._owner_gate(task_id, "WORKER_EXECUTION_FAILURE", f"{role}_WORKER_FAILURE"); return None, "OWNER_GATE"
        if crash_after_worker_return:
            raise InjectedCrash(f"AFTER_WORKER_RETURN:{role}:{op_key}")
        self.store.finish_step(task_id, claim, f"{role}_RESULT_CAPTURED:{op_key}")
        return out, "OK"

    def step(self, task_id: str, *, crash_after_worker_return: str | None = None) -> str:
        task = self.store.get(task_id); state = task["state"]; spec = task["spec"]
        if state in TERMINAL_STATES: return state
        if not self._binding_and_safety(task_id): return "OWNER_GATE"
        if state in {"PENDING", "MECH_GATE_FAIL", "LAB_FIX_REQUIRED", "AUDIT_FIX_REQUIRED"}:
            self.store.transition(task_id, "IN_IMPLEMENT", "ENTER_IMPLEMENT", {"from": state}); state = "IN_IMPLEMENT"

        if state == "IN_IMPLEMENT":
            out, status = self._run_claimed(task_id, "IMPLEMENT", crash_after_worker_return=crash_after_worker_return == "IMPLEMENT")
            if status != "OK": return self.store.get(task_id)["state"]
            mech = mechanical_gate(spec, out or {})
            if not mech.ok:
                self._semantic_fail(task_id, "MECH", mech.code, mech.detail, "MECH_GATE_FAIL"); return self.store.get(task_id)["state"]
            self.store.transition(task_id, "IN_LAB", "MECHANICAL_GATE_PASS", {"evidence_ref": mech.detail, "candidate_head": spec["candidate_head"]}, last_checkpoint="MECHANICAL_GATE_PASS")
            return "IN_LAB"

        if state == "IN_LAB":
            out, status = self._run_claimed(task_id, "LAB", crash_after_worker_return=crash_after_worker_return == "LAB")
            if status != "OK": return self.store.get(task_id)["state"]
            valid, code = validate_review_result("LAB", spec, out)
            if not valid:
                self._owner_gate(task_id, code, code); return "OWNER_GATE"
            verdict = out.get("verdict")
            if verdict == "PASS":
                self.store.transition(task_id, "IN_AUDIT", "LAB_PASS", {"evidence_ref": out["evidence_ref"], "reviewed_head": out["reviewed_head"]}, last_checkpoint="LAB_PASS", repeated_failure_count=0, last_failure_fp=None)
                return "IN_AUDIT"
            if verdict == "FIX_REQUIRED":
                self._semantic_fail(task_id, "LAB", str(out.get("code", "FIX_REQUIRED")), str(out.get("detail", "")), "LAB_FIX_REQUIRED"); return self.store.get(task_id)["state"]
            self._owner_gate(task_id, "LAB_UNPARSABLE_OR_MATERIAL_BLOCK", "LAB_NONPASS_NONFIX"); return "OWNER_GATE"

        if state == "IN_AUDIT":
            out, status = self._run_claimed(task_id, "AUDIT", crash_after_worker_return=crash_after_worker_return == "AUDIT")
            if status != "OK": return self.store.get(task_id)["state"]
            valid, code = validate_review_result("AUDIT", spec, out)
            if not valid:
                self._owner_gate(task_id, code, code); return "OWNER_GATE"
            verdict = out.get("verdict")
            if verdict == "PASS":
                result = {"status": "DONE", "task_id": task_id, "domain": spec["domain"], "candidate_head": spec["candidate_head"], "owner_copy_paste_count": 0, "owner_continue_prompt_count": 0, "owner_keep_alive_count": 0, "semantic_retries": self.store.get(task_id)["semantic_retry_count"], "transient_retries": self.store.get(task_id)["transient_retry_count"], "audit_evidence_ref": out["evidence_ref"]}
                self.store.transition(task_id, "DONE", "AUDITOR_PASS_DONE", result, result_json=canonical_json(result), last_checkpoint="DONE", repeated_failure_count=0, last_failure_fp=None)
                return "DONE"
            if verdict == "FIX_REQUIRED":
                self._semantic_fail(task_id, "AUDIT", str(out.get("code", "FIX_REQUIRED")), str(out.get("detail", "")), "AUDIT_FIX_REQUIRED"); return self.store.get(task_id)["state"]
            self._owner_gate(task_id, "AUDIT_UNPARSABLE_OR_MATERIAL_BLOCK", "AUDIT_NONPASS_NONFIX"); return "OWNER_GATE"
        raise OrchestratorError(f"UNHANDLED_STATE:{state}")

    def run_until_terminal(self, task_id: str, *, max_steps: int = 50) -> str:
        for _ in range(max_steps):
            state = self.store.get(task_id)["state"]
            if state in TERMINAL_STATES: return state
            self.step(task_id)
        self._owner_gate(task_id, "ORCHESTRATOR_STEP_CEILING", f"max_steps={max_steps}")
        return self.store.get(task_id)["state"]


def demo_spec(task_id: str = "demo-task-v2", *, canonical_main: str = "b"*40, candidate_head: str = "a"*40) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "task_id": task_id, "domain": "DEMO_DOMAIN_NEUTRAL",
        "objective": "prove bounded automatic implement-review-fix-review completion",
        "canonical_repo": "fufufu1116/multiverse-research", "canonical_main": canonical_main,
        "candidate_branch": "agent/automation-orchestrator-mvp-20260902-v1", "candidate_head": candidate_head,
        "safety": {"candidate_only": True, "stable_production_effect": False, "secret_credential": False, "external_effect": False, "money_spend": False, "protected_data": False, "irreversible_operation": False, "authority_expansion": False, "unknown_risk": False},
        "budgets": default_budgets(),
    }


def demo_script(head: str) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "IMPLEMENT": {
            "1:*": {"status":"READY","candidate_head":head,"diff_lines":20,"cost_microusd":0,"evidence_ref":"demo-impl-v1"},
            "2:*": {"status":"READY","candidate_head":head,"diff_lines":22,"cost_microusd":0,"evidence_ref":"demo-impl-v2"},
        },
        "LAB": {
            "1:*": {"verdict":"FIX_REQUIRED","reviewed_head":head,"code":"DEMO_FIX","detail":"first pass catches deterministic issue","evidence_ref":"demo-lab-fix"},
            "2:*": {"verdict":"PASS","reviewed_head":head,"evidence_ref":"demo-lab-pass"},
        },
        "AUDIT": {"2:*": {"verdict":"PASS","reviewed_head":head,"evidence_ref":"demo-audit-pass"}},
    }


def run_demo(db_path: pathlib.Path, worker_db: pathlib.Path, *, canonical_main: str = "b"*40, candidate_head: str = "a"*40) -> dict[str, Any]:
    spec = demo_spec(canonical_main=canonical_main, candidate_head=candidate_head)
    worker = DurableScriptedRoleWorker(worker_db, demo_script(candidate_head))
    store = OrchestratorStore(db_path)
    try:
        store.create_task(spec)
        final = Orchestrator(store, worker, StaticBindingVerifier(canonical_main, candidate_head)).run_until_terminal(spec["task_id"])
        return {"final_state": final, "task": store.get(spec["task_id"]), "events": store.events(spec["task_id"])}
    finally:
        store.close()


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--demo-db"); p.add_argument("--worker-db"); p.add_argument("--canonical-main", default="b"*40); p.add_argument("--candidate-head", default="a"*40)
    args = p.parse_args()
    if args.demo_db and args.worker_db:
        out = run_demo(pathlib.Path(args.demo_db), pathlib.Path(args.worker_db), canonical_main=args.canonical_main, candidate_head=args.candidate_head)
        print(canonical_json(out)); return 0 if out["final_state"] == "DONE" else 92
    p.error("use --demo-db and --worker-db"); return 2

if __name__ == "__main__": raise SystemExit(main())
