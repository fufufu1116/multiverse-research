#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — repository-reviewed policy source v5.

v5 removes the v4 worker's ability to accept an arbitrary runtime-constructed
CandidateBindingPolicy. Instead it compiles the exact SHA-256 identity, source
branch and canonical-main binding of one reviewed JSON policy artifact into the
adapter. This is Candidate-only provenance enforcement, not canonical adoption.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from orchestrator_mvp_v2 import OrchestratorError, TransientFailure, canonical_json, operation_key, require
from orchestrator_role_relay_v3 import DurableFixtureReceiptStore
from orchestrator_role_relay_policy_v4 import CandidateBindingPolicy, PolicyRelayStore

POLICY_SOURCE_SCHEMA_VERSION = "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_v5"
POLICY_SOURCE_DB_SCHEMA_VERSION = 3
REVIEWED_POLICY_SOURCE_BRANCH = "agent/automation-orchestrator-policy-source-v5-20260903-v1"
REVIEWED_POLICY_SOURCE_CANONICAL_MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
REVIEWED_POLICY_MANIFEST_SHA256 = "51f9b4030da3f6fdf38c6ea85e765b450721898049c66764e1a6a216404c319f"
REVIEWED_POLICY_MANIFEST_BASENAME = "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"

_REQUIRED_AUTHORITY_FALSE = (
    "canonical_adoption",
    "core_adoption",
    "keirin_adoption",
    "live_provider",
    "production",
    "runtime",
    "spend",
)


@dataclass(frozen=True)
class ReviewedPolicySource:
    raw_sha256: str
    canonical_json_text: str
    source_branch: str
    canonical_main: str
    policy_id: str
    policy: CandidateBindingPolicy

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "ReviewedPolicySource":
        p = pathlib.Path(path)
        require(p.name == REVIEWED_POLICY_MANIFEST_BASENAME, "POLICY_SOURCE_BASENAME_MISMATCH")
        require(p.exists() and p.is_file() and not p.is_symlink(), "POLICY_SOURCE_FILE_CLASS")
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == REVIEWED_POLICY_MANIFEST_SHA256, "POLICY_SOURCE_SHA256_MISMATCH")
        try:
            text = raw.decode("utf-8")
            doc = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrchestratorError("POLICY_SOURCE_JSON_INVALID") from exc
        require(isinstance(doc, dict), "POLICY_SOURCE_DOCUMENT_SHAPE")
        require(text == canonical_json(doc), "POLICY_SOURCE_NOT_CANONICAL_JSON")
        require(doc.get("schema_version") == POLICY_SOURCE_SCHEMA_VERSION, "POLICY_SOURCE_SCHEMA")
        require(doc.get("source_branch") == REVIEWED_POLICY_SOURCE_BRANCH, "POLICY_SOURCE_BRANCH_BINDING")
        require(doc.get("canonical_main") == REVIEWED_POLICY_SOURCE_CANONICAL_MAIN, "POLICY_SOURCE_MAIN_BINDING")
        require(doc.get("canonical_repo") == "fufufu1116/multiverse-research", "POLICY_SOURCE_REPO_BINDING")
        require(doc.get("candidate_only") is True, "POLICY_SOURCE_NOT_CANDIDATE_ONLY")
        authority = doc.get("authority")
        require(isinstance(authority, dict), "POLICY_SOURCE_AUTHORITY_SHAPE")
        for key in _REQUIRED_AUTHORITY_FALSE:
            require(authority.get(key) is False, f"POLICY_SOURCE_AUTHORITY_DENIED:{key}")
        require(set(authority) == set(_REQUIRED_AUTHORITY_FALSE), "POLICY_SOURCE_AUTHORITY_KEYS")
        bindings_raw = doc.get("allowed_bindings")
        require(isinstance(bindings_raw, list) and bool(bindings_raw), "POLICY_SOURCE_BINDINGS_EMPTY")
        bindings: list[tuple[str, str]] = []
        for item in bindings_raw:
            require(isinstance(item, dict) and set(item) == {"domain", "candidate_branch"},
                    "POLICY_SOURCE_BINDING_SHAPE")
            bindings.append((item["domain"], item["candidate_branch"]))
        policy = CandidateBindingPolicy.exact(doc["canonical_repo"], *bindings)
        policy_id = doc.get("policy_id")
        require(isinstance(policy_id, str) and 1 <= len(policy_id) <= 128, "POLICY_SOURCE_ID")
        return cls(digest, text, doc["source_branch"], doc["canonical_main"], policy_id, policy)


class SourceBoundPolicyRelayStore(PolicyRelayStore):
    """v4 queue semantics with v5 source-identity pinning and DB schema isolation."""

    def __init__(self, path: pathlib.Path | str, source: ReviewedPolicySource) -> None:
        require(isinstance(source, ReviewedPolicySource), "POLICY_SOURCE_REQUIRED")
        self.path = str(path)
        self.source = source
        self.policy = source.policy
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._init_v5()

    def _init_v5(self) -> None:
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
                self.conn.execute("INSERT INTO meta(k,v) VALUES('schema',?)", (str(POLICY_SOURCE_DB_SCHEMA_VERSION),))
            elif row[0] != str(POLICY_SOURCE_DB_SCHEMA_VERSION):
                raise OrchestratorError("POLICY_SOURCE_DB_SCHEMA_VERSION_MISMATCH")
            expected = {
                "policy_source_sha256": self.source.raw_sha256,
                "policy_source_json": self.source.canonical_json_text,
                "policy_source_branch": self.source.source_branch,
                "policy_source_canonical_main": self.source.canonical_main,
                "policy_source_id": self.source.policy_id,
                "binding_policy_fingerprint": self.policy.fingerprint,
                "binding_policy_json": canonical_json(self.policy.as_jsonable()),
            }
            rows = {row["k"]: row["v"] for row in self.conn.execute(
                "SELECT k,v FROM meta WHERE k IN (" + ",".join("?" for _ in expected) + ")",
                tuple(expected),
            ).fetchall()}
            if not rows:
                for key, value in expected.items():
                    self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?)", (key, value))
            else:
                require(set(rows) == set(expected), "POLICY_SOURCE_META_PARTIAL")
                for key, value in expected.items():
                    require(rows[key] == value, f"POLICY_SOURCE_META_MISMATCH:{key}")

    def _validate_job(self, role: str, task: dict[str, Any], op_key: str,
                      semantic_attempt: int) -> tuple[dict[str, Any], int]:
        spec, generation = super()._validate_job(role, task, op_key, semantic_attempt)
        require(spec.get("canonical_main") == self.source.canonical_main, "POLICY_SOURCE_TASK_MAIN_MISMATCH")
        return spec, generation


class SourceBoundPolicyRelayRoleWorker:
    replay_safe = True

    def __init__(self, relay_db: pathlib.Path | str, manifest_path: pathlib.Path | str, *,
                 poll_seconds: float = 0.02, result_wait_seconds: float = 5.0) -> None:
        require(poll_seconds > 0, "RELAY_POLL_SECONDS")
        require(result_wait_seconds > 0, "RELAY_WAIT_SECONDS")
        self.relay_db = str(relay_db)
        self.manifest_path = str(manifest_path)
        self.poll_seconds = poll_seconds
        self.result_wait_seconds = result_wait_seconds

    def run(self, *, role: str, task: dict[str, Any], operation_key: str,
            semantic_attempt: int, transient_attempt: int) -> dict[str, Any]:
        source = ReviewedPolicySource.load(self.manifest_path)
        store = SourceBoundPolicyRelayStore(self.relay_db, source)
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


def source_fixture_process_one(relay_db: str, receipt_db: str, manifest_path: str,
                               worker_id: str, script: dict[str, dict[str, dict[str, Any]]], *,
                               lease_seconds: int = 2, crash_after_receipt: bool = False) -> str:
    """Deterministic fixture only; no arbitrary-provider exactly-once claim."""
    source = ReviewedPolicySource.load(manifest_path)
    relay = SourceBoundPolicyRelayStore(relay_db, source)
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
