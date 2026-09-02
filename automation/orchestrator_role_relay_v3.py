#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — durable external-role relay v3.

This candidate adds a persistent relay between the already-validated v2 orchestrator
and future independent role workers. It contains no live provider adapter, network
client, secret handling, spend path, production authority, or Runtime activation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import time
import uuid
from typing import Any

from orchestrator_mvp_v2 import (
    OrchestratorError,
    TransientFailure,
    canonical_json,
    operation_key,
    require,
)

RELAY_SCHEMA_VERSION = "MULTIVERSE_ORCHESTRATOR_ROLE_RELAY_v3"
RELAY_DB_SCHEMA_VERSION = 1
RELAY_ROLES = ("IMPLEMENT", "LAB", "AUDIT")
MAX_RELAY_LEASE_SECONDS = 60
CANDIDATE_BRANCH = "agent/automation-orchestrator-mvp-v3-durable-role-relay-20260903-v1"


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class RelayStore:
    """Durable role queue. Separate from v2 orchestration-state SQLite."""

    def __init__(self, path: pathlib.Path | str) -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._init()

    def close(self) -> None:
        self.conn.close()

    def _init(self) -> None:
        with self.conn:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS jobs(
                operation_key TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                role TEXT NOT NULL,
                semantic_generation INTEGER NOT NULL,
                candidate_head TEXT NOT NULL,
                candidate_branch TEXT NOT NULL,
                canonical_main TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                claim_token TEXT,
                worker_id TEXT,
                lease_expires_at REAL,
                result_json TEXT,
                result_fingerprint TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )""")
            row = self.conn.execute("SELECT v FROM meta WHERE k='schema'").fetchone()
            if row is None:
                self.conn.execute("INSERT INTO meta(k,v) VALUES('schema',?)", (str(RELAY_DB_SCHEMA_VERSION),))
            elif row[0] != str(RELAY_DB_SCHEMA_VERSION):
                raise OrchestratorError("RELAY_DB_SCHEMA_VERSION_MISMATCH")

    @staticmethod
    def _validate_job(role: str, task: dict[str, Any], op_key: str, semantic_attempt: int) -> tuple[dict[str, Any], int]:
        require(role in RELAY_ROLES, "RELAY_ROLE_UNKNOWN")
        require(isinstance(task, dict) and isinstance(task.get("spec"), dict), "RELAY_TASK_SHAPE")
        spec = task["spec"]
        generation = semantic_attempt - 1
        require(generation >= 0, "RELAY_SEMANTIC_GENERATION")
        require(op_key == operation_key(task["task_id"], role, generation), "RELAY_OPERATION_KEY_MISMATCH")
        require(_sha40(spec.get("candidate_head")), "RELAY_CANDIDATE_HEAD")
        require(spec.get("candidate_branch") == CANDIDATE_BRANCH, "RELAY_CANDIDATE_BRANCH_MISMATCH")
        require(_sha40(spec.get("canonical_main")), "RELAY_CANONICAL_MAIN")
        require(spec.get("safety", {}).get("candidate_only") is True, "RELAY_NOT_CANDIDATE_ONLY")
        for k in ("stable_production_effect", "secret_credential", "external_effect", "money_spend",
                  "protected_data", "irreversible_operation", "authority_expansion", "unknown_risk"):
            require(spec.get("safety", {}).get(k) is False, f"RELAY_SAFETY_FAIL_CLOSED:{k}")
        require(spec.get("budgets", {}).get("cost_budget_microusd") == 0, "RELAY_SPEND_DENIED")
        return spec, generation

    def enqueue(self, *, role: str, task: dict[str, Any], operation_key_value: str,
                semantic_attempt: int, transient_attempt: int) -> None:
        spec, generation = self._validate_job(role, task, operation_key_value, semantic_attempt)
        payload = {
            "schema_version": RELAY_SCHEMA_VERSION,
            "task_id": task["task_id"],
            "role": role,
            "operation_key": operation_key_value,
            "semantic_generation": generation,
            "semantic_attempt": semantic_attempt,
            "transient_attempt_observed": transient_attempt,
            "candidate_head": spec["candidate_head"],
            "candidate_branch": spec["candidate_branch"],
            "canonical_main": spec["canonical_main"],
            "objective": spec["objective"],
            "authority": {
                "candidate_only": True,
                "live_provider": False,
                "spend": False,
                "production": False,
                "runtime": False,
            },
        }
        now = time.time()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.conn.execute("SELECT * FROM jobs WHERE operation_key=?", (operation_key_value,)).fetchone()
            if existing is None:
                self.conn.execute("""INSERT INTO jobs(operation_key,task_id,role,semantic_generation,candidate_head,candidate_branch,
                    canonical_main,payload_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (operation_key_value, task["task_id"], role, generation, spec["candidate_head"], spec["candidate_branch"],
                     spec["canonical_main"], canonical_json(payload), "QUEUED", now, now))
            else:
                require(existing["task_id"] == task["task_id"], "RELAY_REPLAY_TASK_MISMATCH")
                require(existing["role"] == role, "RELAY_REPLAY_ROLE_MISMATCH")
                require(existing["semantic_generation"] == generation, "RELAY_REPLAY_GENERATION_MISMATCH")
                require(existing["candidate_head"] == spec["candidate_head"], "RELAY_REPLAY_HEAD_MISMATCH")
                require(existing["candidate_branch"] == spec["candidate_branch"], "RELAY_REPLAY_BRANCH_MISMATCH")
                require(existing["canonical_main"] == spec["canonical_main"], "RELAY_REPLAY_MAIN_MISMATCH")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def recover_expired(self, *, at: float | None = None) -> list[str]:
        """Atomically recover only claims that are still expired when written.

        BEGIN IMMEDIATE prevents a heartbeat or completion writer from succeeding
        between the expiry validation and the conditional recovery update.
        """
        at = time.time() if at is None else at
        recovered: list[str] = []
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            rows = self.conn.execute(
                "SELECT operation_key,claim_token FROM jobs "
                "WHERE status='CLAIMED' AND claim_token IS NOT NULL "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<=?",
                (at,),
            ).fetchall()
            for row in rows:
                cur = self.conn.execute(
                    "UPDATE jobs SET status='QUEUED',claim_token=NULL,worker_id=NULL,"
                    "lease_expires_at=NULL,updated_at=? "
                    "WHERE operation_key=? AND status='CLAIMED' AND claim_token=? "
                    "AND lease_expires_at IS NOT NULL AND lease_expires_at<=?",
                    (at, row["operation_key"], row["claim_token"], at),
                )
                if cur.rowcount == 1:
                    recovered.append(row["operation_key"])
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return recovered

    def claim_next(self, *, worker_id: str, lease_seconds: int = 30) -> dict[str, Any] | None:
        require(isinstance(worker_id, str) and bool(worker_id), "RELAY_WORKER_ID")
        require(isinstance(lease_seconds, int) and 1 <= lease_seconds <= MAX_RELAY_LEASE_SECONDS, "RELAY_LEASE_WIDENING_DENIED")
        now = time.time()
        self.recover_expired(at=now)
        token = uuid.uuid4().hex
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created_at,operation_key LIMIT 1").fetchone()
            if row is None:
                self.conn.commit()
                return None
            cur = self.conn.execute(
                "UPDATE jobs SET status='CLAIMED',claim_token=?,worker_id=?,lease_expires_at=?,updated_at=? WHERE operation_key=? AND status='QUEUED'",
                (token, worker_id, now + lease_seconds, now, row["operation_key"]),
            )
            if cur.rowcount != 1:
                self.conn.rollback()
                return None
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        out = json.loads(row["payload_json"])
        out["claim_token"] = token
        out["worker_id"] = worker_id
        out["lease_seconds"] = lease_seconds
        return out

    def heartbeat(self, operation_key_value: str, claim_token: str, *, lease_seconds: int = 30) -> None:
        require(1 <= lease_seconds <= MAX_RELAY_LEASE_SECONDS, "RELAY_LEASE_WIDENING_DENIED")
        now = time.time()
        with self.conn:
            cur = self.conn.execute(
                "UPDATE jobs SET lease_expires_at=?,updated_at=? WHERE operation_key=? AND status='CLAIMED' AND claim_token=?",
                (now + lease_seconds, now, operation_key_value, claim_token),
            )
            require(cur.rowcount == 1, "RELAY_STALE_CLAIM")

    def complete(self, operation_key_value: str, claim_token: str, result: dict[str, Any]) -> None:
        """Validate and complete under one SQLite writer transaction.

        The final UPDATE repeats status+claim-token ownership predicates so stale
        ownership cannot become COMPLETE even if this method is later refactored.
        """
        require(isinstance(result, dict), "RELAY_RESULT_OBJECT")
        now = time.time()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT * FROM jobs WHERE operation_key=?", (operation_key_value,)).fetchone()
            require(row is not None, "RELAY_JOB_NOT_FOUND")
            if row["status"] == "COMPLETE":
                require(row["result_json"] == canonical_json(result), "RELAY_CONFLICTING_DUPLICATE_RESULT")
                self.conn.commit()
                return
            require(row["status"] == "CLAIMED" and row["claim_token"] == claim_token, "RELAY_STALE_CLAIM")
            if row["role"] == "IMPLEMENT":
                require(result.get("candidate_head") == row["candidate_head"], "RELAY_IMPLEMENT_HEAD_MISMATCH")
            else:
                require(result.get("reviewed_head") == row["candidate_head"], f"RELAY_{row['role']}_HEAD_MISMATCH")
            require(isinstance(result.get("evidence_ref"), str) and bool(result["evidence_ref"]), "RELAY_EVIDENCE_REQUIRED")
            fp = _fingerprint(result)
            cur = self.conn.execute(
                "UPDATE jobs SET status='COMPLETE',result_json=?,result_fingerprint=?,"
                "lease_expires_at=NULL,updated_at=? "
                "WHERE operation_key=? AND status='CLAIMED' AND claim_token=?",
                (canonical_json(result), fp, now, operation_key_value, claim_token),
            )
            require(cur.rowcount == 1, "RELAY_STALE_CLAIM")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def result(self, operation_key_value: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT status,result_json FROM jobs WHERE operation_key=?", (operation_key_value,)).fetchone()
        if row is None or row["status"] != "COMPLETE":
            return None
        return json.loads(row["result_json"])

    def job(self, operation_key_value: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE operation_key=?", (operation_key_value,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(out.pop("payload_json"))
        out["result"] = json.loads(out["result_json"]) if out["result_json"] else None
        return out


class RelayRoleWorker:
    """v2 RoleWorker adapter backed by a persistent external-role relay queue."""

    replay_safe = True

    def __init__(self, relay_db: pathlib.Path | str, *, poll_seconds: float = 0.02, result_wait_seconds: float = 5.0) -> None:
        require(poll_seconds > 0, "RELAY_POLL_SECONDS")
        require(result_wait_seconds > 0, "RELAY_WAIT_SECONDS")
        self.relay_db = str(relay_db)
        self.poll_seconds = poll_seconds
        self.result_wait_seconds = result_wait_seconds

    def run(self, *, role: str, task: dict[str, Any], operation_key: str,
            semantic_attempt: int, transient_attempt: int) -> dict[str, Any]:
        store = RelayStore(self.relay_db)
        try:
            store.enqueue(role=role, task=task, operation_key_value=operation_key,
                          semantic_attempt=semantic_attempt, transient_attempt=transient_attempt)
            deadline = time.monotonic() + self.result_wait_seconds
            while time.monotonic() < deadline:
                out = store.result(operation_key)
                if out is not None:
                    return out
                time.sleep(self.poll_seconds)
        finally:
            store.close()
        raise TransientFailure("RELAY_RESULT_NOT_READY")


class DurableFixtureReceiptStore:
    """Replay-safe fixture standing in for a future external provider adapter."""

    def __init__(self, path: pathlib.Path | str) -> None:
        self.path = str(path)
        conn = sqlite3.connect(self.path, timeout=10)
        with conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("CREATE TABLE IF NOT EXISTS receipts(operation_key TEXT PRIMARY KEY,result_json TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS executions(operation_key TEXT PRIMARY KEY,count INTEGER NOT NULL)")
        conn.close()

    def execute_once(self, operation_key_value: str, result: dict[str, Any]) -> dict[str, Any]:
        conn = sqlite3.connect(self.path, timeout=10)
        with conn:
            row = conn.execute("SELECT result_json FROM receipts WHERE operation_key=?", (operation_key_value,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO receipts(operation_key,result_json) VALUES(?,?)", (operation_key_value, canonical_json(result)))
                conn.execute("INSERT INTO executions(operation_key,count) VALUES(?,1)", (operation_key_value,))
                out = result
            else:
                out = json.loads(row[0])
        conn.close()
        return out

    def execution_count(self, operation_key_value: str) -> int:
        conn = sqlite3.connect(self.path)
        row = conn.execute("SELECT count FROM executions WHERE operation_key=?", (operation_key_value,)).fetchone()
        conn.close()
        return 0 if row is None else int(row[0])


def fixture_process_one(relay_db: str, receipt_db: str, worker_id: str,
                        script: dict[str, dict[str, dict[str, Any]]], *,
                        lease_seconds: int = 2, crash_after_receipt: bool = False) -> str:
    relay = RelayStore(relay_db)
    job = relay.claim_next(worker_id=worker_id, lease_seconds=lease_seconds)
    if job is None:
        relay.close()
        return "NO_JOB"
    role = job["role"]
    generation = str(job["semantic_generation"] + 1)
    role_script = script.get(role, {})
    result = role_script.get(generation)
    if result is None:
        relay.close()
        raise OrchestratorError(f"FIXTURE_SCRIPT_EXHAUSTED:{role}:{generation}")
    receipts = DurableFixtureReceiptStore(receipt_db)
    durable = receipts.execute_once(job["operation_key"], dict(result))
    if crash_after_receipt:
        relay.close()
        return "CRASH_AFTER_RECEIPT"
    relay.complete(job["operation_key"], job["claim_token"], durable)
    relay.close()
    return "COMPLETE"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--relay-db")
    p.add_argument("--show-job")
    args = p.parse_args()
    if args.relay_db and args.show_job:
        store = RelayStore(args.relay_db)
        try:
            print(canonical_json(store.job(args.show_job)))
        finally:
            store.close()
        return 0
    p.error("use --relay-db and --show-job")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())