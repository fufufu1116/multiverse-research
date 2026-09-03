#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — policy-bound durable role relay v4.

v4 keeps the independently validated v3 transport/concurrency implementation and
adds an immutable, DB-pinned candidate-binding policy. It supports more than one
explicit candidate branch without turning branch choice into caller-controlled
authority. No live provider, secret, spend, production or Runtime path is added.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from orchestrator_mvp_v2 import (
    OrchestratorError,
    TransientFailure,
    canonical_json,
    operation_key,
    require,
)
from orchestrator_role_relay_v3 import (
    DurableFixtureReceiptStore,
    RELAY_ROLES,
    RelayStore,
)

POLICY_RELAY_SCHEMA_VERSION = "MULTIVERSE_ORCHESTRATOR_ROLE_RELAY_POLICY_v4"
POLICY_RELAY_DB_SCHEMA_VERSION = 2
_AGENT_BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,199}")
_DOMAIN_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


def _sqlite_first_open_pragma(conn: sqlite3.Connection, sql: str, timeout_seconds: float = 10.0):
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            return conn.execute(sql)
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if ("locked" not in message and "busy" not in message) or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _candidate_branch_shape(branch: Any) -> bool:
    if not isinstance(branch, str) or not branch.startswith("agent/"):
        return False
    if _AGENT_BRANCH_RE.fullmatch(branch) is None:
        return False
    if branch.endswith(("/", ".")) or branch.startswith("-"):
        return False
    if any(token in branch for token in ("..", "//", "@{", "\\", "~", "^", ":", "?", "*", "[", " ")):
        return False
    parts = branch.split("/")
    if any(part in {"", ".", ".."} or part.endswith(".lock") for part in parts):
        return False
    return True


@dataclass(frozen=True)
class CandidateBindingPolicy:
    """Exact repo + (domain, candidate branch) bindings, independent of task input."""

    canonical_repo: str
    allowed_bindings: frozenset[tuple[str, str]]

    def __post_init__(self) -> None:
        require(isinstance(self.canonical_repo, str) and self.canonical_repo.count("/") == 1,
                "RELAY_POLICY_REPO_INVALID")
        require(isinstance(self.allowed_bindings, frozenset) and bool(self.allowed_bindings),
                "RELAY_POLICY_BINDINGS_EMPTY")
        for item in self.allowed_bindings:
            require(isinstance(item, tuple) and len(item) == 2, "RELAY_POLICY_BINDING_SHAPE")
            domain, branch = item
            require(isinstance(domain, str) and _DOMAIN_RE.fullmatch(domain) is not None,
                    "RELAY_POLICY_DOMAIN_INVALID")
            require(_candidate_branch_shape(branch), "RELAY_POLICY_BRANCH_INVALID")

    @classmethod
    def exact(cls, canonical_repo: str, *bindings: tuple[str, str]) -> "CandidateBindingPolicy":
        return cls(canonical_repo=canonical_repo, allowed_bindings=frozenset(bindings))

    def allows(self, domain: Any, branch: Any) -> bool:
        return isinstance(domain, str) and isinstance(branch, str) and (domain, branch) in self.allowed_bindings

    def as_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": POLICY_RELAY_SCHEMA_VERSION,
            "canonical_repo": self.canonical_repo,
            "allowed_bindings": [
                {"domain": domain, "candidate_branch": branch}
                for domain, branch in sorted(self.allowed_bindings)
            ],
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.as_jsonable()).encode()).hexdigest()


class PolicyRelayStore(RelayStore):
    """v3 durable queue with a v4-only DB schema and immutable binding policy."""

    def __init__(self, path: pathlib.Path | str, policy: CandidateBindingPolicy) -> None:
        require(isinstance(policy, CandidateBindingPolicy), "RELAY_POLICY_REQUIRED")
        self.path = str(path)
        self.policy = policy
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=10000")
        _sqlite_first_open_pragma(self.conn, "PRAGMA journal_mode=WAL")
        _sqlite_first_open_pragma(self.conn, "PRAGMA synchronous=FULL")
        self._init_v4()

    def _init_v4(self) -> None:
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
                self.conn.execute("INSERT INTO meta(k,v) VALUES('schema',?)",
                                  (str(POLICY_RELAY_DB_SCHEMA_VERSION),))
            elif row[0] != str(POLICY_RELAY_DB_SCHEMA_VERSION):
                raise OrchestratorError("POLICY_RELAY_DB_SCHEMA_VERSION_MISMATCH")

            policy_json = canonical_json(self.policy.as_jsonable())
            fp_row = self.conn.execute("SELECT v FROM meta WHERE k='binding_policy_fingerprint'").fetchone()
            json_row = self.conn.execute("SELECT v FROM meta WHERE k='binding_policy_json'").fetchone()
            if fp_row is None and json_row is None:
                self.conn.execute("INSERT INTO meta(k,v) VALUES('binding_policy_fingerprint',?)",
                                  (self.policy.fingerprint,))
                self.conn.execute("INSERT INTO meta(k,v) VALUES('binding_policy_json',?)", (policy_json,))
            else:
                require(fp_row is not None and json_row is not None, "RELAY_POLICY_META_PARTIAL")
                require(fp_row[0] == self.policy.fingerprint, "RELAY_POLICY_FINGERPRINT_MISMATCH")
                require(json_row[0] == policy_json, "RELAY_POLICY_JSON_MISMATCH")

    def _validate_job(self, role: str, task: dict[str, Any], op_key: str,
                      semantic_attempt: int) -> tuple[dict[str, Any], int]:
        require(role in RELAY_ROLES, "RELAY_ROLE_UNKNOWN")
        require(isinstance(task, dict) and isinstance(task.get("spec"), dict), "RELAY_TASK_SHAPE")
        spec = task["spec"]
        generation = semantic_attempt - 1
        require(generation >= 0, "RELAY_SEMANTIC_GENERATION")
        require(op_key == operation_key(task["task_id"], role, generation), "RELAY_OPERATION_KEY_MISMATCH")
        require(spec.get("canonical_repo") == self.policy.canonical_repo, "RELAY_REPO_POLICY_DENIED")
        require(self.policy.allows(spec.get("domain"), spec.get("candidate_branch")),
                "RELAY_BINDING_POLICY_DENIED")
        require(_sha40(spec.get("candidate_head")), "RELAY_CANDIDATE_HEAD")
        require(_sha40(spec.get("canonical_main")), "RELAY_CANONICAL_MAIN")
        require(spec.get("safety", {}).get("candidate_only") is True, "RELAY_NOT_CANDIDATE_ONLY")
        for key in ("stable_production_effect", "secret_credential", "external_effect", "money_spend",
                    "protected_data", "irreversible_operation", "authority_expansion", "unknown_risk"):
            require(spec.get("safety", {}).get(key) is False, f"RELAY_SAFETY_FAIL_CLOSED:{key}")
        require(spec.get("budgets", {}).get("cost_budget_microusd") == 0, "RELAY_SPEND_DENIED")
        return spec, generation


class PolicyRelayRoleWorker:
    """v2 RoleWorker adapter using a DB-pinned explicit candidate-binding policy."""

    replay_safe = True

    def __init__(self, relay_db: pathlib.Path | str, policy: CandidateBindingPolicy, *,
                 poll_seconds: float = 0.02, result_wait_seconds: float = 5.0) -> None:
        require(poll_seconds > 0, "RELAY_POLL_SECONDS")
        require(result_wait_seconds > 0, "RELAY_WAIT_SECONDS")
        self.relay_db = str(relay_db)
        self.policy = policy
        self.poll_seconds = poll_seconds
        self.result_wait_seconds = result_wait_seconds

    def run(self, *, role: str, task: dict[str, Any], operation_key: str,
            semantic_attempt: int, transient_attempt: int) -> dict[str, Any]:
        store = PolicyRelayStore(self.relay_db, self.policy)
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


def policy_fixture_process_one(relay_db: str, receipt_db: str, policy: CandidateBindingPolicy,
                               worker_id: str, script: dict[str, dict[str, dict[str, Any]]], *,
                               lease_seconds: int = 2, crash_after_receipt: bool = False) -> str:
    """Deterministic fixture only; no claim about arbitrary future provider exactly-once."""
    relay = PolicyRelayStore(relay_db, policy)
    job = relay.claim_next(worker_id=worker_id, lease_seconds=lease_seconds)
    if job is None:
        relay.close()
        return "NO_JOB"
    role = job["role"]
    generation = str(job["semantic_generation"] + 1)
    result = script.get(role, {}).get(generation)
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