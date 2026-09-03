#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — provider-neutral adapter contract v7.

This candidate introduces a provider-neutral request/receipt boundary while the only
runnable adapter remains a sealed deterministic local fixture. It performs no
network access, provider contact, secret handling, spend, production mutation, or
Runtime activation. Any real provider adapter remains a separate future gate.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from orchestrator_mvp_v2 import OrchestratorError, canonical_json, require
from orchestrator_role_relay_policy_source_v5 import (
    ReviewedPolicySource,
    SourceBoundPolicyRelayStore,
)
from orchestrator_role_relay_policy_v4 import _sqlite_first_open_pragma

PROVIDER_ADAPTER_SCHEMA_VERSION = "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_v7"
PROVIDER_ADAPTER_DB_SCHEMA_VERSION = 1
PROVIDER_ADAPTER_SOURCE_BRANCH = "agent/automation-orchestrator-provider-adapter-contract-v7-20260903-v1"
PROVIDER_ADAPTER_CANONICAL_MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
PROVIDER_ADAPTER_PREDECESSOR_HEAD = "e8c27fafcdb2e9ed4c54fdbc4f72d6d2fd386f0f"
PROVIDER_ADAPTER_MANIFEST_BASENAME = "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_V7.json"
PROVIDER_ADAPTER_MANIFEST_SHA256 = "35a769362d97af06259c49b7d415e5885f258c215c84f3eab63528b98c639652"
PROVIDER_ADAPTER_ID = "automation-provider-neutral-local-v7"
PROVIDER_ADAPTER_KIND = "deterministic_local_fixture"

_REQUIRED_AUTHORITY_FALSE = (
    "canonical_adoption",
    "core_adoption",
    "external_effect",
    "keirin_adoption",
    "live_provider",
    "network",
    "production",
    "runtime",
    "secret_credential",
    "spend",
)


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _nonbool_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_result_for_request(request: dict[str, Any], result: Any) -> dict[str, Any]:
    """Validate role semantics before a receipt becomes durable and again on replay."""
    require(isinstance(result, dict), "PROVIDER_ADAPTER_RESULT_SHAPE")
    role = request.get("role")
    expected_head = request.get("candidate_head")
    evidence = result.get("evidence_ref")
    require(isinstance(evidence, str) and bool(evidence), "PROVIDER_ADAPTER_EVIDENCE_REQUIRED")

    if role == "IMPLEMENT":
        required = {"status", "candidate_head", "diff_lines", "cost_microusd", "evidence_ref"}
        require(required.issubset(result), "PROVIDER_ADAPTER_IMPLEMENT_SCHEMA")
        require(result.get("candidate_head") == expected_head, "PROVIDER_ADAPTER_IMPLEMENT_HEAD_MISMATCH")
        require(result.get("status") == "READY", "PROVIDER_ADAPTER_IMPLEMENT_STATUS")
        require(_nonbool_int(result.get("diff_lines")) and result["diff_lines"] >= 0,
                "PROVIDER_ADAPTER_IMPLEMENT_DIFF_LINES")
        require(_nonbool_int(result.get("cost_microusd")) and result["cost_microusd"] == 0,
                "PROVIDER_ADAPTER_IMPLEMENT_COST")
    else:
        require(role in ("LAB", "AUDIT"), "PROVIDER_ADAPTER_RESULT_ROLE")
        required = {"verdict", "reviewed_head", "evidence_ref"}
        require(required.issubset(result), f"PROVIDER_ADAPTER_{role}_SCHEMA")
        require(result.get("reviewed_head") == expected_head, f"PROVIDER_ADAPTER_{role}_HEAD_MISMATCH")
        verdict = result.get("verdict")
        require(verdict in ("PASS", "FIX_REQUIRED"), f"PROVIDER_ADAPTER_{role}_VERDICT")
        if verdict == "FIX_REQUIRED":
            require(isinstance(result.get("code"), str) and bool(result["code"]),
                    f"PROVIDER_ADAPTER_{role}_FIX_CODE")
            require(isinstance(result.get("detail"), str), f"PROVIDER_ADAPTER_{role}_FIX_DETAIL")
    return dict(result)


@dataclass(frozen=True)
class ProviderAdapterManifest:
    raw_sha256: str
    canonical_json_text: str
    adapter_id: str
    adapter_kind: str
    source_branch: str
    predecessor_head: str
    canonical_main: str

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "ProviderAdapterManifest":
        p = pathlib.Path(path)
        require(p.name == PROVIDER_ADAPTER_MANIFEST_BASENAME, "PROVIDER_ADAPTER_MANIFEST_BASENAME")
        require(p.exists() and p.is_file() and not p.is_symlink(), "PROVIDER_ADAPTER_MANIFEST_FILE_CLASS")
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == PROVIDER_ADAPTER_MANIFEST_SHA256, "PROVIDER_ADAPTER_MANIFEST_SHA256")
        try:
            text = raw.decode("utf-8")
            doc = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrchestratorError("PROVIDER_ADAPTER_MANIFEST_JSON") from exc
        require(isinstance(doc, dict), "PROVIDER_ADAPTER_MANIFEST_SHAPE")
        require(text == canonical_json(doc), "PROVIDER_ADAPTER_MANIFEST_NOT_CANONICAL")
        require(doc.get("schema_version") == PROVIDER_ADAPTER_SCHEMA_VERSION, "PROVIDER_ADAPTER_SCHEMA")
        require(doc.get("adapter_id") == PROVIDER_ADAPTER_ID, "PROVIDER_ADAPTER_ID_MISMATCH")
        require(doc.get("adapter_kind") == PROVIDER_ADAPTER_KIND, "PROVIDER_ADAPTER_KIND_MISMATCH")
        require(doc.get("source_branch") == PROVIDER_ADAPTER_SOURCE_BRANCH, "PROVIDER_ADAPTER_SOURCE_BRANCH")
        require(doc.get("predecessor_head") == PROVIDER_ADAPTER_PREDECESSOR_HEAD, "PROVIDER_ADAPTER_PREDECESSOR_HEAD")
        require(doc.get("canonical_main") == PROVIDER_ADAPTER_CANONICAL_MAIN, "PROVIDER_ADAPTER_MAIN")
        require(doc.get("canonical_repo") == "fufufu1116/multiverse-research", "PROVIDER_ADAPTER_REPO")
        require(doc.get("candidate_only") is True, "PROVIDER_ADAPTER_NOT_CANDIDATE_ONLY")
        authority = doc.get("authority")
        require(isinstance(authority, dict), "PROVIDER_ADAPTER_AUTHORITY_SHAPE")
        require(set(authority) == set(_REQUIRED_AUTHORITY_FALSE), "PROVIDER_ADAPTER_AUTHORITY_KEYS")
        for key in _REQUIRED_AUTHORITY_FALSE:
            require(authority.get(key) is False, f"PROVIDER_ADAPTER_AUTHORITY_DENIED:{key}")
        return cls(digest, text, doc["adapter_id"], doc["adapter_kind"], doc["source_branch"],
                   doc["predecessor_head"], doc["canonical_main"])


class DeterministicLocalAdapter:
    """Sealed no-network/no-effect adapter used only to prove the neutral contract."""

    replay_safe = True
    external_effect = False
    network = False
    spend = False
    secret_credential = False

    def __init__(self, script: dict[str, dict[str, dict[str, Any]]]) -> None:
        require(isinstance(script, dict), "PROVIDER_ADAPTER_SCRIPT_SHAPE")
        self.script = script

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        require(isinstance(request, dict), "PROVIDER_REQUEST_SHAPE")
        require(request.get("adapter_id") == PROVIDER_ADAPTER_ID, "PROVIDER_REQUEST_ADAPTER_ID")
        role = request.get("role")
        generation = str(int(request.get("semantic_generation")) + 1)
        result = self.script.get(role, {}).get(generation)
        require(isinstance(result, dict), f"PROVIDER_SCRIPT_EXHAUSTED:{role}:{generation}")
        return dict(result)


class ProviderAdapterReceiptStore:
    """Durable local receipt boundary for the sealed deterministic adapter.

    The adapter call is serialized inside a SQLite writer transaction. This is safe
    only because the reviewed v7 adapter has no network or external effect. A future
    live adapter requires a different independently reviewed idempotency design.
    """

    def __init__(self, path: pathlib.Path | str, manifest: ProviderAdapterManifest) -> None:
        require(isinstance(manifest, ProviderAdapterManifest), "PROVIDER_ADAPTER_MANIFEST_REQUIRED")
        self.path = str(path)
        self.manifest = manifest
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=10000")
        _sqlite_first_open_pragma(self.conn, "PRAGMA journal_mode=WAL")
        _sqlite_first_open_pragma(self.conn, "PRAGMA synchronous=FULL")
        self._init()

    def close(self) -> None:
        self.conn.close()

    def _init(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS receipts(
                operation_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )""")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS executions(
                operation_key TEXT PRIMARY KEY,
                count INTEGER NOT NULL
            )""")
            expected = {
                "schema": str(PROVIDER_ADAPTER_DB_SCHEMA_VERSION),
                "manifest_sha256": self.manifest.raw_sha256,
                "manifest_json": self.manifest.canonical_json_text,
                "adapter_id": self.manifest.adapter_id,
                "adapter_kind": self.manifest.adapter_kind,
                "source_branch": self.manifest.source_branch,
                "predecessor_head": self.manifest.predecessor_head,
                "canonical_main": self.manifest.canonical_main,
            }
            rows = {r["k"]: r["v"] for r in self.conn.execute(
                "SELECT k,v FROM meta WHERE k IN (" + ",".join("?" for _ in expected) + ")",
                tuple(expected),
            ).fetchall()}
            if not rows:
                for key, value in expected.items():
                    self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?)", (key, value))
            else:
                require(set(rows) == set(expected), "PROVIDER_ADAPTER_META_PARTIAL")
                for key, value in expected.items():
                    require(rows[key] == value, f"PROVIDER_ADAPTER_META_MISMATCH:{key}")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def execute_local_once(self, operation_key_value: str, request: dict[str, Any],
                           adapter: DeterministicLocalAdapter) -> dict[str, Any]:
        require(type(adapter) is DeterministicLocalAdapter, "PROVIDER_ADAPTER_RUNTIME_INJECTION_DENIED")
        require(adapter.replay_safe is True, "PROVIDER_ADAPTER_NOT_REPLAY_SAFE")
        require(adapter.external_effect is False, "PROVIDER_ADAPTER_EXTERNAL_EFFECT_DENIED")
        require(adapter.network is False, "PROVIDER_ADAPTER_NETWORK_DENIED")
        require(adapter.spend is False, "PROVIDER_ADAPTER_SPEND_DENIED")
        require(adapter.secret_credential is False, "PROVIDER_ADAPTER_SECRET_DENIED")
        require(isinstance(operation_key_value, str) and bool(operation_key_value), "PROVIDER_ADAPTER_OPERATION_KEY")
        request_json = canonical_json(request)
        request_fp = hashlib.sha256(request_json.encode()).hexdigest()
        now = time.time()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT request_fingerprint,result_json FROM receipts WHERE operation_key=?",
                (operation_key_value,),
            ).fetchone()
            if row is not None:
                require(row["request_fingerprint"] == request_fp, "PROVIDER_ADAPTER_CONFLICTING_REPLAY")
                out = _validate_result_for_request(request, json.loads(row["result_json"]))
                self.conn.commit()
                return out
            result = _validate_result_for_request(request, adapter.execute(request))
            self.conn.execute(
                "INSERT INTO receipts(operation_key,request_fingerprint,request_json,result_json,created_at) VALUES(?,?,?,?,?)",
                (operation_key_value, request_fp, request_json, canonical_json(result), now),
            )
            self.conn.execute(
                "INSERT INTO executions(operation_key,count) VALUES(?,1)",
                (operation_key_value,),
            )
            self.conn.commit()
            return result
        except BaseException:
            self.conn.rollback()
            raise

    def execution_count(self, operation_key_value: str) -> int:
        row = self.conn.execute("SELECT count FROM executions WHERE operation_key=?", (operation_key_value,)).fetchone()
        return 0 if row is None else int(row[0])


def provider_request_from_job(job: dict[str, Any], manifest: ProviderAdapterManifest) -> dict[str, Any]:
    require(isinstance(job, dict), "PROVIDER_JOB_SHAPE")
    require(job.get("authority") == {
        "candidate_only": True,
        "live_provider": False,
        "production": False,
        "runtime": False,
        "spend": False,
    }, "PROVIDER_JOB_AUTHORITY")
    require(_sha40(job.get("candidate_head")), "PROVIDER_JOB_HEAD")
    require(_sha40(job.get("canonical_main")), "PROVIDER_JOB_MAIN")
    require(job.get("canonical_main") == manifest.canonical_main, "PROVIDER_JOB_MAIN_MISMATCH")
    require(isinstance(job.get("candidate_branch"), str) and bool(job["candidate_branch"]), "PROVIDER_JOB_BRANCH")
    require(job.get("role") in ("IMPLEMENT", "LAB", "AUDIT"), "PROVIDER_JOB_ROLE")
    require(isinstance(job.get("semantic_generation"), int) and job["semantic_generation"] >= 0,
            "PROVIDER_JOB_GENERATION")
    require(isinstance(job.get("operation_key"), str) and bool(job["operation_key"]), "PROVIDER_JOB_OPERATION_KEY")
    return {
        "schema_version": PROVIDER_ADAPTER_SCHEMA_VERSION,
        "adapter_id": manifest.adapter_id,
        "adapter_kind": manifest.adapter_kind,
        "operation_key": job["operation_key"],
        "task_id": job["task_id"],
        "role": job["role"],
        "semantic_generation": job["semantic_generation"],
        "candidate_head": job["candidate_head"],
        "candidate_branch": job["candidate_branch"],
        "canonical_main": job["canonical_main"],
        "objective": job["objective"],
        "authority": {
            "candidate_only": True,
            "external_effect": False,
            "live_provider": False,
            "network": False,
            "production": False,
            "runtime": False,
            "secret_credential": False,
            "spend": False,
        },
    }


def provider_adapter_process_one(relay_db: str, receipt_db: str, policy_manifest_path: str,
                                 adapter_manifest_path: str, worker_id: str,
                                 script: dict[str, dict[str, dict[str, Any]]], *,
                                 lease_seconds: int = 2, crash_after_receipt: bool = False) -> str:
    manifest = ProviderAdapterManifest.load(adapter_manifest_path)
    source = ReviewedPolicySource.load(policy_manifest_path)
    require(source.canonical_main == manifest.canonical_main, "PROVIDER_POLICY_MAIN_MISMATCH")
    relay = SourceBoundPolicyRelayStore(relay_db, source)
    try:
        job = relay.claim_next(worker_id=worker_id, lease_seconds=lease_seconds)
        if job is None:
            return "NO_JOB"
        request = provider_request_from_job(job, manifest)
        adapter = DeterministicLocalAdapter(script)
        receipts = ProviderAdapterReceiptStore(receipt_db, manifest)
        try:
            durable = receipts.execute_local_once(job["operation_key"], request, adapter)
            if crash_after_receipt:
                return "CRASH_AFTER_RECEIPT"
            relay.complete(job["operation_key"], job["claim_token"], durable)
            return "COMPLETE"
        finally:
            receipts.close()
    finally:
        relay.close()


def request_fingerprint(request: dict[str, Any]) -> str:
    return _fingerprint(request)
