"""MULTIVERSE Runtime Supervisor v1 — sealed construction surface.

This module proves local lifecycle/checkpoint/identity/kill-switch mechanics only.
It cannot contact a provider or network, cannot create Independent Lab/Auditor
verdicts, and carries no production/Runtime activation authority.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

SCHEMA_VERSION = "MULTIVERSE_RUNTIME_SUPERVISOR_V1"
CANONICAL_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
CANONICAL_TREE = "2c957c4ad8a553b3a0e7122ebcdb22e75398afaf"
MODE = "SEALED_DRY_RUN"
WORKER_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
MAX_TOKEN_AGE_SECONDS = 300
FORBIDDEN_REVIEW_ROLES = frozenset({"LAB", "AUDIT", "INDEPENDENT_LAB", "INDEPENDENT_AUDITOR"})
ALLOWED_ACTIONS = frozenset({"IMPLEMENT", "CHECKPOINT", "RECOVERY"})

AUTHORITY = {
    "runtime_activation": False,
    "production": False,
    "live_provider": False,
    "network": False,
    "external_effect": False,
    "spend": False,
    "secret_persistence": False,
    "protected_keirin_data": False,
    "main_mutation": False,
    "ruleset_mutation": False,
    "lab_verdict": False,
    "auditor_verdict": False,
}


class RuntimeGateError(RuntimeError):
    pass


class WorkerIdentityError(RuntimeGateError):
    pass


class KillSwitchEngaged(RuntimeGateError):
    pass


class ReviewRoleBoundaryError(RuntimeGateError):
    pass


@dataclass(frozen=True)
class VerifiedWorker:
    worker_id: str
    issued_at: int
    nonce: str


class WorkerIdentityVerifier:
    """HMAC verifier using injected key bytes only; key material is never persisted."""

    def __init__(self, key: bytes, *, clock: Callable[[], float] = time.time):
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise WorkerIdentityError("EPHEMERAL_KEY_MIN_32_BYTES_REQUIRED")
        self._key = bytes(key)
        self._clock = clock

    def mint_for_test(self, worker_id: str, *, issued_at: int | None = None, nonce: str | None = None) -> str:
        """Candidate test helper. This is not a production identity issuer."""
        self._validate_worker_id(worker_id)
        ts = int(self._clock()) if issued_at is None else int(issued_at)
        nonce = nonce or uuid.uuid4().hex
        payload = f"{worker_id}|{ts}|{nonce}"
        mac = hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}|{mac}"

    def verify(self, token: str) -> VerifiedWorker:
        if not isinstance(token, str):
            raise WorkerIdentityError("TOKEN_STRING_REQUIRED")
        parts = token.split("|")
        if len(parts) != 4:
            raise WorkerIdentityError("TOKEN_SHAPE_INVALID")
        worker_id, ts_s, nonce, supplied = parts
        self._validate_worker_id(worker_id)
        if not nonce or len(nonce) > 128:
            raise WorkerIdentityError("TOKEN_NONCE_INVALID")
        try:
            ts = int(ts_s)
        except ValueError as exc:
            raise WorkerIdentityError("TOKEN_TIMESTAMP_INVALID") from exc
        now = int(self._clock())
        if ts > now + 5 or now - ts > MAX_TOKEN_AGE_SECONDS:
            raise WorkerIdentityError("TOKEN_EXPIRED_OR_FUTURE")
        payload = f"{worker_id}|{ts}|{nonce}"
        expected = hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise WorkerIdentityError("TOKEN_MAC_INVALID")
        return VerifiedWorker(worker_id, ts, nonce)

    @staticmethod
    def _validate_worker_id(worker_id: str) -> None:
        if not isinstance(worker_id, str) or WORKER_RE.fullmatch(worker_id) is None:
            raise WorkerIdentityError("WORKER_ID_INVALID")


class SupervisorStore:
    """Durable local runtime-control journal, separate from Shared Engine task authority."""

    def __init__(self, path: str):
        self.path = path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA busy_timeout=10000")
        return c

    def _init(self) -> None:
        c = self._conn()
        with c:
            c.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL)")
            c.execute("""CREATE TABLE IF NOT EXISTS journal(
                id INTEGER PRIMARY KEY AUTOINCREMENT, instance_id TEXT NOT NULL,
                worker_id TEXT, event_type TEXT NOT NULL, detail_json TEXT NOT NULL,
                created_at REAL NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS checkpoints(
                checkpoint_key TEXT PRIMARY KEY, value_json TEXT NOT NULL,
                instance_id TEXT NOT NULL, updated_at REAL NOT NULL)""")
            self._set_default(c, "schema_version", SCHEMA_VERSION)
            self._set_default(c, "canonical_main", CANONICAL_MAIN)
            self._set_default(c, "canonical_tree", CANONICAL_TREE)
            self._set_default(c, "mode", MODE)
            self._set_default(c, "kill_switch", "1")
            self._set_default(c, "incarnation", "0")
        c.close()
        self.assert_binding()

    @staticmethod
    def _set_default(c: sqlite3.Connection, key: str, value: str) -> None:
        c.execute("INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)", (key, value))

    def assert_binding(self) -> None:
        c = self._conn()
        rows = {r["k"]: r["v"] for r in c.execute("SELECT k,v FROM meta")}
        c.close()
        expected = {
            "schema_version": SCHEMA_VERSION,
            "canonical_main": CANONICAL_MAIN,
            "canonical_tree": CANONICAL_TREE,
            "mode": MODE,
        }
        if any(rows.get(k) != v for k, v in expected.items()):
            raise RuntimeGateError("RUNTIME_STORE_BINDING_MISMATCH")

    def start_instance(self) -> tuple[str, int]:
        c = self._conn(); c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT v FROM meta WHERE k='incarnation'").fetchone()
            inc = int(row["v"]) + 1
            c.execute("UPDATE meta SET v=? WHERE k='incarnation'", (str(inc),))
            instance_id = f"runtime-v1-{inc}-{uuid.uuid4().hex[:12]}"
            now = time.time()
            c.execute("INSERT INTO journal(instance_id,worker_id,event_type,detail_json,created_at) VALUES(?,?,?,?,?)",
                      (instance_id, None, "INSTANCE_STARTED", json.dumps({"incarnation": inc}), now))
            c.commit(); c.close(); return instance_id, inc
        except BaseException:
            c.rollback(); c.close(); raise

    def kill_switch_engaged(self) -> bool:
        c = self._conn(); row = c.execute("SELECT v FROM meta WHERE k='kill_switch'").fetchone(); c.close()
        return row["v"] == "1"

    def set_test_kill_switch(self, engaged: bool, *, authority: str) -> None:
        if authority != "TEST_ONLY_LOCAL_CANDIDATE":
            raise RuntimeGateError("KILL_SWITCH_AUTHORITY_DENIED")
        c = self._conn()
        with c:
            c.execute("UPDATE meta SET v=? WHERE k='kill_switch'", ("1" if engaged else "0",))
        c.close()

    def journal(self, instance_id: str, event_type: str, *, worker_id: str | None = None, detail: dict[str, Any] | None = None) -> None:
        c = self._conn(); now = time.time()
        with c:
            c.execute("INSERT INTO journal(instance_id,worker_id,event_type,detail_json,created_at) VALUES(?,?,?,?,?)",
                      (instance_id, worker_id, event_type, json.dumps(detail or {}, sort_keys=True, separators=(",", ":")), now))
        c.close()

    def checkpoint(self, key: str, value: dict[str, Any], *, instance_id: str) -> None:
        if not isinstance(key, str) or not key or len(key) > 128:
            raise RuntimeGateError("CHECKPOINT_KEY_INVALID")
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
        c = self._conn(); now = time.time()
        with c:
            c.execute("""INSERT INTO checkpoints(checkpoint_key,value_json,instance_id,updated_at)
                       VALUES(?,?,?,?) ON CONFLICT(checkpoint_key) DO UPDATE SET
                       value_json=excluded.value_json,instance_id=excluded.instance_id,updated_at=excluded.updated_at""",
                      (key, payload, instance_id, now))
        c.close()

    def get_checkpoint(self, key: str) -> dict[str, Any] | None:
        c = self._conn(); row = c.execute("SELECT value_json FROM checkpoints WHERE checkpoint_key=?", (key,)).fetchone(); c.close()
        return None if row is None else json.loads(row["value_json"])

    def events(self) -> list[dict[str, Any]]:
        c = self._conn(); rows = c.execute("SELECT * FROM journal ORDER BY id").fetchall(); c.close()
        out = []
        for r in rows:
            d = dict(r); d["detail"] = json.loads(d.pop("detail_json")); out.append(d)
        return out


class RuntimeSupervisor:
    """Bounded supervisor loop. Executes injected local actions only in SEALED_DRY_RUN."""

    def __init__(self, store: SupervisorStore, verifier: WorkerIdentityVerifier):
        self.store = store
        self.verifier = verifier
        self.instance_id, self.incarnation = store.start_instance()

    def heartbeat(self, token: str) -> VerifiedWorker:
        worker = self.verifier.verify(token)
        if self.store.kill_switch_engaged():
            self.store.journal(self.instance_id, "HEARTBEAT_BLOCKED_KILL_SWITCH", worker_id=worker.worker_id)
            raise KillSwitchEngaged("KILL_SWITCH_ENGAGED")
        self.store.journal(self.instance_id, "HEARTBEAT", worker_id=worker.worker_id)
        return worker

    def step(self, token: str, action_type: str, checkpoint_key: str,
             action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        worker = self.verifier.verify(token)
        if action_type in FORBIDDEN_REVIEW_ROLES:
            self.store.journal(self.instance_id, "REVIEW_ROLE_REJECTED", worker_id=worker.worker_id,
                               detail={"role": action_type})
            raise ReviewRoleBoundaryError("INDEPENDENT_REVIEW_CANNOT_BE_SELF_MANUFACTURED")
        if action_type not in ALLOWED_ACTIONS:
            raise RuntimeGateError("ACTION_TYPE_DENIED")
        if self.store.kill_switch_engaged():
            self.store.journal(self.instance_id, "STEP_BLOCKED_KILL_SWITCH", worker_id=worker.worker_id,
                               detail={"action_type": action_type})
            raise KillSwitchEngaged("KILL_SWITCH_ENGAGED")
        self.store.journal(self.instance_id, "STEP_STARTED", worker_id=worker.worker_id,
                           detail={"action_type": action_type, "checkpoint_key": checkpoint_key})
        try:
            result = action()
            if not isinstance(result, dict):
                raise RuntimeGateError("ACTION_RESULT_OBJECT_REQUIRED")
            # serialization check before durable success/checkpoint
            json.dumps(result, sort_keys=True)
            self.store.checkpoint(checkpoint_key, result, instance_id=self.instance_id)
            self.store.journal(self.instance_id, "STEP_COMPLETED", worker_id=worker.worker_id,
                               detail={"action_type": action_type, "checkpoint_key": checkpoint_key})
            return result
        except BaseException as exc:
            self.store.journal(self.instance_id, "STEP_FAILED", worker_id=worker.worker_id,
                               detail={"action_type": action_type, "error_type": type(exc).__name__})
            raise

    def run_bounded(self, token: str, action_type: str, checkpoint_key: str,
                    action: Callable[[], dict[str, Any]], *, max_steps: int) -> list[dict[str, Any]]:
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not (1 <= max_steps <= 100):
            raise RuntimeGateError("MAX_STEPS_BOUNDED_1_100_REQUIRED")
        results = []
        for _ in range(max_steps):
            results.append(self.step(token, action_type, checkpoint_key, action))
        return results
