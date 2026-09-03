#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — provider idempotency simulator v8.

No network, provider, credential, spend, production, Core/Keirin or Runtime authority.
The "remote" side is an independent local SQLite store used only to model provider-side
idempotency and crash reconciliation without holding a local writer transaction across it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import time
from typing import Any

from orchestrator_mvp_v2 import OrchestratorError, canonical_json, require
from orchestrator_provider_adapter_v7 import _validate_result_for_request
from orchestrator_role_relay_policy_source_v5 import ReviewedPolicySource, SourceBoundPolicyRelayStore
from orchestrator_role_relay_policy_v4 import _sqlite_first_open_pragma

V8_SCHEMA_VERSION = "MULTIVERSE_AUTOMATION_PROVIDER_IDEMPOTENCY_v8"
V8_DB_SCHEMA = 1
V8_SOURCE_BRANCH = "agent/automation-orchestrator-provider-idempotency-v8-20260903-v1"
V8_CANONICAL_MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
V8_PREDECESSOR_HEAD = "4a72ef46116043094c7a8e494404956925a5b3bf"
V8_MANIFEST_BASENAME = "MULTIVERSE_AUTOMATION_PROVIDER_IDEMPOTENCY_V8.json"
V8_MANIFEST_SHA256 = "b8efff3e38b7142418bda87b7b42f76ff892c6d7f6a96b10f3403ab78e3a49a9"
V8_ADAPTER_ID = "automation-provider-idempotency-simulator-v8"
V8_PROTOCOL_ID = "automation-provider-idempotency-v8"


class RemoteResponseLost(RuntimeError):
    pass


class RemoteStatusUnknown(RuntimeError):
    pass


def _fp(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _expected_provider_receipt_id(idempotency_key: str) -> str:
    require(isinstance(idempotency_key, str) and idempotency_key, "V8_PROVIDER_RECEIPT_KEY_SHAPE")
    return "sim-" + hashlib.sha256(("receipt:" + idempotency_key).encode()).hexdigest()[:32]


def _open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    _sqlite_first_open_pragma(conn, "PRAGMA journal_mode=WAL")
    _sqlite_first_open_pragma(conn, "PRAGMA synchronous=FULL")
    return conn


class V8Manifest:
    def __init__(self, path: pathlib.Path | str) -> None:
        p = pathlib.Path(path)
        require(p.name == V8_MANIFEST_BASENAME, "V8_MANIFEST_BASENAME")
        require(p.exists() and p.is_file() and not p.is_symlink(), "V8_MANIFEST_FILE_CLASS")
        raw = p.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == V8_MANIFEST_SHA256, "V8_MANIFEST_SHA256")
        try:
            text = raw.decode("utf-8")
            doc = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrchestratorError("V8_MANIFEST_JSON") from exc
        require(text == canonical_json(doc), "V8_MANIFEST_NOT_CANONICAL")
        require(doc.get("schema_version") == V8_SCHEMA_VERSION, "V8_MANIFEST_SCHEMA")
        require(doc.get("source_branch") == V8_SOURCE_BRANCH, "V8_MANIFEST_BRANCH")
        require(doc.get("predecessor_head") == V8_PREDECESSOR_HEAD, "V8_MANIFEST_PREDECESSOR")
        require(doc.get("canonical_main") == V8_CANONICAL_MAIN, "V8_MANIFEST_MAIN")
        require(doc.get("canonical_repo") == "fufufu1116/multiverse-research", "V8_MANIFEST_REPO")
        require(doc.get("adapter_id") == V8_ADAPTER_ID, "V8_MANIFEST_ADAPTER")
        require(doc.get("protocol_id") == V8_PROTOCOL_ID, "V8_MANIFEST_PROTOCOL")
        require(doc.get("candidate_only") is True, "V8_MANIFEST_CANDIDATE_ONLY")
        expected = {
            "canonical_adoption": False,
            "core_adoption": False,
            "credential": False,
            "external_effect": False,
            "keirin_adoption": False,
            "live_provider": False,
            "network": False,
            "production": False,
            "runtime": False,
            "secret_credential": False,
            "spend": False,
        }
        require(doc.get("authority") == expected, "V8_MANIFEST_AUTHORITY")
        ceiling = doc.get("proof_ceiling")
        require(isinstance(ceiling, dict) and ceiling.get("simulated_remote_idempotency_protocol_only") is True,
                "V8_MANIFEST_PROOF_CEILING")
        for key in (
            "authenticated_provider_identity",
            "authenticated_reviewer_identity",
            "arbitrary_provider_exactly_once",
            "provider_documented_idempotency_semantics",
            "real_network_or_provider_contact",
        ):
            require(ceiling.get(key) is False, f"V8_MANIFEST_PROOF_CEILING:{key}")
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.canonical_json_text = text


def request_from_job(job: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(job, dict), "V8_JOB_SHAPE")
    require(job.get("role") in ("IMPLEMENT", "LAB", "AUDIT"), "V8_JOB_ROLE")
    require(_sha40(job.get("candidate_head")), "V8_JOB_HEAD")
    require(job.get("canonical_main") == V8_CANONICAL_MAIN, "V8_JOB_MAIN")
    require(
        isinstance(job.get("semantic_generation"), int)
        and not isinstance(job["semantic_generation"], bool)
        and job["semantic_generation"] >= 0,
        "V8_JOB_GENERATION",
    )
    require(isinstance(job.get("operation_key"), str) and job["operation_key"], "V8_JOB_OPERATION_KEY")
    require(
        job.get("authority")
        == {"candidate_only": True, "live_provider": False, "production": False, "runtime": False, "spend": False},
        "V8_JOB_AUTHORITY",
    )
    request = {
        "schema_version": V8_SCHEMA_VERSION,
        "protocol_id": V8_PROTOCOL_ID,
        "adapter_id": V8_ADAPTER_ID,
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
            "credential": False,
            "external_effect": False,
            "live_provider": False,
            "network": False,
            "production": False,
            "runtime": False,
            "secret_credential": False,
            "spend": False,
        },
    }
    request["request_fingerprint"] = _fp(request)
    request["idempotency_key"] = hashlib.sha256(
        ("multiverse-v8-idempotency:" + request["request_fingerprint"]).encode()
    ).hexdigest()
    return request


def _validate_request(request: dict[str, Any]) -> None:
    require(isinstance(request, dict), "V8_REQUEST_SHAPE")
    require(request.get("schema_version") == V8_SCHEMA_VERSION, "V8_REQUEST_SCHEMA")
    require(request.get("protocol_id") == V8_PROTOCOL_ID, "V8_REQUEST_PROTOCOL")
    require(request.get("adapter_id") == V8_ADAPTER_ID, "V8_REQUEST_ADAPTER")
    supplied_fp = request.get("request_fingerprint")
    supplied_key = request.get("idempotency_key")
    bare = dict(request)
    bare.pop("request_fingerprint", None)
    bare.pop("idempotency_key", None)
    expected_fp = _fp(bare)
    expected_key = hashlib.sha256(("multiverse-v8-idempotency:" + expected_fp).encode()).hexdigest()
    require(supplied_fp == expected_fp, "V8_REQUEST_FINGERPRINT")
    require(supplied_key == expected_key, "V8_IDEMPOTENCY_KEY_DERIVATION")
    require(request.get("canonical_main") == V8_CANONICAL_MAIN, "V8_REQUEST_MAIN")
    require(
        request.get("authority")
        == {
            "candidate_only": True,
            "credential": False,
            "external_effect": False,
            "live_provider": False,
            "network": False,
            "production": False,
            "runtime": False,
            "secret_credential": False,
            "spend": False,
        },
        "V8_REQUEST_AUTHORITY",
    )


class SimulatedProviderStore:
    """Independent durable provider-side simulator. Never shares a local journal transaction."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.conn = _open_db(path)
        self._init()

    def _init(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS effects(
                idempotency_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                request_json TEXT NOT NULL,
                provider_receipt_id TEXT NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                result_hash TEXT NOT NULL,
                effect_count INTEGER NOT NULL,
                created_at REAL NOT NULL
            )"""
            )
            rows = {r["k"]: r["v"] for r in self.conn.execute("SELECT k,v FROM meta").fetchall()}
            expected = {"schema": str(V8_DB_SCHEMA), "protocol_id": V8_PROTOCOL_ID}
            if not rows:
                for k, v in expected.items():
                    self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?)", (k, v))
            else:
                require(rows == expected, "V8_REMOTE_META_MISMATCH")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def close(self) -> None:
        self.conn.close()

    def lookup(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT request_fingerprint,provider_receipt_id,result_json,result_hash,effect_count "
            "FROM effects WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        expected_rid = _expected_provider_receipt_id(idempotency_key)
        require(row["provider_receipt_id"] == expected_rid, "V8_REMOTE_RECEIPT_ID_INTEGRITY")
        result = json.loads(row["result_json"])
        require(hashlib.sha256(canonical_json(result).encode()).hexdigest() == row["result_hash"],
                "V8_REMOTE_RESULT_HASH_INTEGRITY")
        require(int(row["effect_count"]) == 1, "V8_REMOTE_EFFECT_COUNT_INTEGRITY")
        return {
            "protocol_id": V8_PROTOCOL_ID,
            "idempotency_key": idempotency_key,
            "request_fingerprint": row["request_fingerprint"],
            "provider_receipt_id": row["provider_receipt_id"],
            "result": result,
            "result_hash": row["result_hash"],
            "effect_count": int(row["effect_count"]),
        }

    def effect_once(
        self,
        request: dict[str, Any],
        result: dict[str, Any],
        *,
        lose_response_after_commit: bool = False,
    ) -> dict[str, Any]:
        _validate_request(request)
        require(isinstance(result, dict), "V8_REMOTE_RESULT_SHAPE")
        key = request["idempotency_key"]
        req_fp = request["request_fingerprint"]
        req_json = canonical_json(request)
        result_json = canonical_json(result)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()
        expected_rid = _expected_provider_receipt_id(key)
        created = False
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT request_fingerprint,request_json,provider_receipt_id,result_json,result_hash,effect_count "
                "FROM effects WHERE idempotency_key=?",
                (key,),
            ).fetchone()
            if row is None:
                self.conn.execute(
                    "INSERT INTO effects(idempotency_key,request_fingerprint,request_json,provider_receipt_id,"
                    "result_json,result_hash,effect_count,created_at) VALUES(?,?,?,?,?,?,1,?)",
                    (key, req_fp, req_json, expected_rid, result_json, result_hash, time.time()),
                )
                created = True
            else:
                require(
                    row["request_fingerprint"] == req_fp and row["request_json"] == req_json,
                    "V8_REMOTE_IDEMPOTENCY_KEY_CONFLICT",
                )
                require(
                    row["provider_receipt_id"] == expected_rid,
                    "V8_REMOTE_RECEIPT_ID_INTEGRITY",
                )
                require(
                    row["result_json"] == result_json and row["result_hash"] == result_hash,
                    "V8_REMOTE_RESULT_CONFLICT",
                )
                require(int(row["effect_count"]) == 1, "V8_REMOTE_EFFECT_COUNT_INTEGRITY")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        receipt = self.lookup(key)
        require(receipt is not None and receipt["effect_count"] == 1, "V8_REMOTE_RECEIPT_MISSING")
        if created and lose_response_after_commit:
            raise RemoteResponseLost("V8_REMOTE_RESPONSE_LOST_AFTER_COMMIT")
        return receipt

    def effect_count(self, idempotency_key: str) -> int:
        row = self.conn.execute("SELECT effect_count FROM effects WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        return 0 if row is None else int(row[0])


class DeterministicRemoteSimulator:
    replay_safe = True
    simulated_remote_effect = True
    real_external_effect = False
    network = False
    live_provider = False
    credential = False
    spend = False
    runtime = False

    def __init__(self, store: SimulatedProviderStore, script: dict[str, dict[str, dict[str, Any]]]) -> None:
        require(type(store) is SimulatedProviderStore, "V8_REMOTE_STORE_INJECTION_DENIED")
        require(isinstance(script, dict), "V8_REMOTE_SCRIPT_SHAPE")
        self.store = store
        self.script = script

    def result_for(self, request: dict[str, Any]) -> dict[str, Any]:
        role = request.get("role")
        generation = str(int(request.get("semantic_generation")) + 1)
        result = self.script.get(role, {}).get(generation)
        require(isinstance(result, dict), f"V8_REMOTE_SCRIPT_EXHAUSTED:{role}:{generation}")
        return dict(result)

    def execute(
        self,
        request: dict[str, Any],
        *,
        lose_response_after_commit: bool = False,
        timeout_before_effect: bool = False,
        ambiguous_without_receipt: bool = False,
    ) -> dict[str, Any]:
        _validate_request(request)
        if timeout_before_effect:
            raise TimeoutError("V8_REMOTE_TIMEOUT_BEFORE_EFFECT")
        if ambiguous_without_receipt:
            raise RemoteStatusUnknown("V8_REMOTE_STATUS_UNKNOWN")
        return self.store.effect_once(
            request,
            self.result_for(request),
            lose_response_after_commit=lose_response_after_commit,
        )


class LocalIdempotencyJournal:
    """Local staged journal. The simulated provider is never called while this writer transaction is open."""

    def __init__(self, path: str, manifest: V8Manifest) -> None:
        require(type(manifest) is V8Manifest, "V8_MANIFEST_REQUIRED")
        self.path = path
        self.manifest = manifest
        self.conn = _open_db(path)
        self._init()

    def _init(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS journal(
                operation_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                request_json TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL,
                provider_receipt_id TEXT,
                provider_result_hash TEXT,
                result_json TEXT,
                updated_at REAL NOT NULL
            )"""
            )
            expected = {
                "schema": str(V8_DB_SCHEMA),
                "manifest_sha256": self.manifest.sha256,
                "manifest_json": self.manifest.canonical_json_text,
                "protocol_id": V8_PROTOCOL_ID,
            }
            rows = {r["k"]: r["v"] for r in self.conn.execute("SELECT k,v FROM meta").fetchall()}
            if not rows:
                for k, v in expected.items():
                    self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?)", (k, v))
            else:
                require(rows == expected, "V8_LOCAL_META_MISMATCH")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def close(self) -> None:
        self.conn.close()

    def prepare(self, request: dict[str, Any]) -> str:
        _validate_request(request)
        op = request["operation_key"]
        fp = request["request_fingerprint"]
        key = request["idempotency_key"]
        req_json = canonical_json(request)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT request_fingerprint,request_json,idempotency_key,state FROM journal WHERE operation_key=?",
                (op,),
            ).fetchone()
            if row is None:
                self.conn.execute(
                    "INSERT INTO journal(operation_key,request_fingerprint,request_json,idempotency_key,state,updated_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (op, fp, req_json, key, "PREPARED", time.time()),
                )
            else:
                require(
                    row["request_fingerprint"] == fp
                    and row["request_json"] == req_json
                    and row["idempotency_key"] == key,
                    "V8_LOCAL_CONFLICTING_REPLAY",
                )
                require(row["state"] in ("PREPARED", "OBSERVED"), "V8_LOCAL_STATE")
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        require(self.conn.in_transaction is False, "V8_LOCAL_TRANSACTION_LEAK_AFTER_PREPARE")
        return key

    def observed_result(self, request: dict[str, Any]) -> dict[str, Any] | None:
        _validate_request(request)
        row = self.conn.execute(
            "SELECT request_fingerprint,idempotency_key,state,provider_receipt_id,provider_result_hash,result_json "
            "FROM journal WHERE operation_key=?",
            (request["operation_key"],),
        ).fetchone()
        if row is None or row["state"] != "OBSERVED":
            return None
        require(row["request_fingerprint"] == request["request_fingerprint"], "V8_LOCAL_OBSERVED_REQUEST_MISMATCH")
        require(row["idempotency_key"] == request["idempotency_key"], "V8_LOCAL_OBSERVED_KEY_MISMATCH")
        require(
            row["provider_receipt_id"] == _expected_provider_receipt_id(request["idempotency_key"]),
            "V8_LOCAL_OBSERVED_RECEIPT_ID_INTEGRITY",
        )
        require(isinstance(row["result_json"], str), "V8_LOCAL_OBSERVED_RESULT_MISSING")
        result = _validate_result_for_request(request, json.loads(row["result_json"]))
        result_json = canonical_json(result)
        expected_hash = hashlib.sha256(result_json.encode()).hexdigest()
        require(row["provider_result_hash"] == expected_hash, "V8_LOCAL_OBSERVED_RESULT_HASH_INTEGRITY")
        return result

    def record_observed(self, request: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
        _validate_request(request)
        require(isinstance(receipt, dict), "V8_PROVIDER_RECEIPT_SHAPE")
        require(receipt.get("protocol_id") == V8_PROTOCOL_ID, "V8_PROVIDER_RECEIPT_PROTOCOL")
        require(receipt.get("idempotency_key") == request["idempotency_key"], "V8_PROVIDER_RECEIPT_KEY")
        require(receipt.get("request_fingerprint") == request["request_fingerprint"], "V8_PROVIDER_RECEIPT_REQUEST")
        rid = receipt.get("provider_receipt_id")
        require(isinstance(rid, str) and rid, "V8_PROVIDER_RECEIPT_ID")
        require(
            rid == _expected_provider_receipt_id(request["idempotency_key"]),
            "V8_PROVIDER_RECEIPT_ID_INTEGRITY",
        )
        result = _validate_result_for_request(request, receipt.get("result"))
        result_json = canonical_json(result)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()
        require(receipt.get("result_hash") == result_hash, "V8_PROVIDER_RECEIPT_RESULT_HASH")
        require(receipt.get("effect_count") == 1, "V8_PROVIDER_EFFECT_COUNT")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT request_fingerprint,idempotency_key,state,provider_receipt_id,provider_result_hash,result_json "
                "FROM journal WHERE operation_key=?",
                (request["operation_key"],),
            ).fetchone()
            require(row is not None, "V8_LOCAL_PREPARED_REQUIRED")
            require(
                row["request_fingerprint"] == request["request_fingerprint"]
                and row["idempotency_key"] == request["idempotency_key"],
                "V8_LOCAL_BINDING_MISMATCH",
            )
            if row["state"] == "OBSERVED":
                require(
                    row["provider_receipt_id"] == rid
                    and row["provider_result_hash"] == result_hash
                    and row["result_json"] == result_json,
                    "V8_LOCAL_OBSERVED_CONFLICT",
                )
            else:
                require(row["state"] == "PREPARED", "V8_LOCAL_STATE")
                self.conn.execute(
                    "UPDATE journal SET state='OBSERVED',provider_receipt_id=?,provider_result_hash=?,result_json=?,updated_at=? "
                    "WHERE operation_key=?",
                    (rid, result_hash, result_json, time.time(), request["operation_key"]),
                )
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return result

    def state(self, operation_key: str) -> str | None:
        row = self.conn.execute("SELECT state FROM journal WHERE operation_key=?", (operation_key,)).fetchone()
        return None if row is None else str(row[0])


def execute_idempotent_simulated_remote(
    journal: LocalIdempotencyJournal,
    simulator: DeterministicRemoteSimulator,
    request: dict[str, Any],
    *,
    crash_before_remote: bool = False,
    lose_response_after_commit: bool = False,
    crash_after_local_receipt: bool = False,
    timeout_before_effect: bool = False,
    ambiguous_without_receipt: bool = False,
) -> dict[str, Any]:
    require(type(journal) is LocalIdempotencyJournal, "V8_LOCAL_JOURNAL_INJECTION_DENIED")
    require(type(simulator) is DeterministicRemoteSimulator, "V8_REMOTE_SIMULATOR_INJECTION_DENIED")
    for name, expected in (
        ("replay_safe", True),
        ("simulated_remote_effect", True),
        ("real_external_effect", False),
        ("network", False),
        ("live_provider", False),
        ("credential", False),
        ("spend", False),
        ("runtime", False),
    ):
        require(getattr(simulator, name, None) is expected, f"V8_CAPABILITY_SEAL:{name}")
    key = journal.prepare(request)
    existing = journal.observed_result(request)
    if existing is not None:
        return existing
    if crash_before_remote:
        raise RuntimeError("V8_CRASH_BEFORE_REMOTE_EFFECT")
    require(journal.conn.in_transaction is False, "V8_REMOTE_CALL_WHILE_LOCAL_TX_OPEN")
    try:
        receipt = simulator.execute(
            request,
            lose_response_after_commit=lose_response_after_commit,
            timeout_before_effect=timeout_before_effect,
            ambiguous_without_receipt=ambiguous_without_receipt,
        )
    except RemoteResponseLost:
        receipt = simulator.store.lookup(key)
        if receipt is None:
            raise OrchestratorError("V8_REMOTE_STATUS_REQUIRED")
    except RemoteStatusUnknown:
        receipt = simulator.store.lookup(key)
        if receipt is None:
            raise OrchestratorError("V8_REMOTE_STATUS_REQUIRED")
    except TimeoutError:
        receipt = simulator.store.lookup(key)
        if receipt is None:
            raise OrchestratorError("V8_REMOTE_STATUS_REQUIRED")
    require(journal.conn.in_transaction is False, "V8_LOCAL_TX_OPEN_AFTER_REMOTE")
    result = journal.record_observed(request, receipt)
    if crash_after_local_receipt:
        raise RuntimeError("V8_CRASH_AFTER_LOCAL_RECEIPT")
    return result


def process_one(
    relay_db: str,
    local_journal_db: str,
    simulated_provider_db: str,
    policy_manifest_path: str,
    v8_manifest_path: str,
    worker_id: str,
    script: dict[str, dict[str, dict[str, Any]]],
    *,
    lease_seconds: int = 2,
    lose_response_after_commit: bool = False,
    crash_after_local_receipt: bool = False,
) -> str:
    manifest = V8Manifest(v8_manifest_path)
    source = ReviewedPolicySource.load(policy_manifest_path)
    require(source.canonical_main == V8_CANONICAL_MAIN, "V8_POLICY_MAIN_MISMATCH")
    relay = SourceBoundPolicyRelayStore(relay_db, source)
    try:
        job = relay.claim_next(worker_id=worker_id, lease_seconds=lease_seconds)
        if job is None:
            return "NO_JOB"
        request = request_from_job(job)
        journal = LocalIdempotencyJournal(local_journal_db, manifest)
        remote_store = SimulatedProviderStore(simulated_provider_db)
        try:
            simulator = DeterministicRemoteSimulator(remote_store, script)
            result = execute_idempotent_simulated_remote(
                journal,
                simulator,
                request,
                lose_response_after_commit=lose_response_after_commit,
                crash_after_local_receipt=crash_after_local_receipt,
            )
            relay.complete(job["operation_key"], job["claim_token"], result)
            return "COMPLETE"
        finally:
            remote_store.close()
            journal.close()
    finally:
        relay.close()
