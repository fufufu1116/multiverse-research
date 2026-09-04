"""Trusted local broker for v10 process isolation.

The full v9/PR91/PR88 capability exists only in this broker process. The IPC
surface is an explicit JSON allowlist and never exposes task creation or generic
dispatch. Accepted request IDs are durably reserved before dispatch in a
bounded, non-evicting SQLite anti-replay store. This is bounded local-process
evidence, not a deployed daemon.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3

import config
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from integration_bridge import IntegrationBinding
from local_persistent_worker_v9 import LocalPersistentWorker, WorkerConfig

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})
REQUEST_KEYS = frozenset({"v", "op", "request_id"})
REPLAY_CAPACITY = 256
REPLAY_SCHEMA_VERSION = 1


class ProtocolError(RuntimeError):
    pass


def _reject_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ProtocolError("V10_DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _decode_request(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_MESSAGE_BYTES:
        raise ProtocolError("V10_REQUEST_SIZE_BOUND")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("V10_INVALID_JSON") from exc
    if type(value) is not dict or set(value) != REQUEST_KEYS:
        raise ProtocolError("V10_REQUEST_SCHEMA")
    if type(value["v"]) is not int or value["v"] != PROTOCOL_VERSION:
        raise ProtocolError("V10_PROTOCOL_VERSION")
    if value["op"] not in ALLOWED_OPS:
        raise ProtocolError("V10_OPCODE_DENIED")
    if not isinstance(value["request_id"], str) or not (1 <= len(value["request_id"]) <= 64):
        raise ProtocolError("V10_REQUEST_ID_BOUND")
    return value


def _request_fingerprint(request: dict) -> str:
    canonical = json.dumps(request, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class DurableReplayStore:
    """Bounded deny-only transport state; never workflow/task authority."""

    def __init__(self, path: str):
        if not isinstance(path, str) or not path.startswith("/") or len(path.encode("utf-8")) > 240:
            raise ValueError("V10_REPLAY_DB_PATH_BOUND")
        self.path = path
        self._init_schema()

    def _connect(self):
        con = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def _init_schema(self):
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "CREATE TABLE IF NOT EXISTS ipc_replay("
                "request_id TEXT PRIMARY KEY,"
                "fingerprint TEXT NOT NULL,"
                "schema_version INTEGER NOT NULL"
                ")"
            )
            con.execute(
                "CREATE TABLE IF NOT EXISTS ipc_replay_meta("
                "k TEXT PRIMARY KEY,"
                "v TEXT NOT NULL"
                ")"
            )
            row = con.execute("SELECT v FROM ipc_replay_meta WHERE k='schema_version'").fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO ipc_replay_meta(k,v) VALUES('schema_version',?)",
                    (str(REPLAY_SCHEMA_VERSION),),
                )
            elif row[0] != str(REPLAY_SCHEMA_VERSION):
                raise ProtocolError("V10_REPLAY_SCHEMA_MISMATCH")
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def reserve(self, request: dict) -> None:
        request_id = request["request_id"]
        fingerprint = _request_fingerprint(request)
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT fingerprint FROM ipc_replay WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is not None:
                if row[0] == fingerprint:
                    raise ProtocolError("V10_REQUEST_REPLAY_DENIED")
                raise ProtocolError("V10_REQUEST_ID_CONFLICT")
            count = con.execute("SELECT COUNT(*) FROM ipc_replay").fetchone()[0]
            if count >= REPLAY_CAPACITY:
                raise ProtocolError("V10_REPLAY_STORE_FULL")
            con.execute(
                "INSERT INTO ipc_replay(request_id,fingerprint,schema_version) VALUES(?,?,?)",
                (request_id, fingerprint, REPLAY_SCHEMA_VERSION),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def count(self) -> int:
        con = self._connect()
        try:
            return int(con.execute("SELECT COUNT(*) FROM ipc_replay").fetchone()[0])
        finally:
            con.close()


def _response(request_id: str, ok: bool, result=None, error=None) -> bytes:
    payload = {"v": PROTOCOL_VERSION, "request_id": request_id, "ok": bool(ok),
               "result": result if ok else None, "error": None if ok else str(error)}
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("V10_RESPONSE_SIZE_BOUND")
    return encoded


class ConsumeOnlyBroker:
    def __init__(self, binding: IntegrationBinding, bridge_db: str, provider_db: str, worker_config: WorkerConfig):
        self.worker = LocalPersistentWorker(binding, bridge_db, provider_db, worker_config)

    def dispatch(self, request: dict) -> dict:
        op = request["op"]
        if op == "PING":
            return {"broker_pid": os.getpid(), "worker_id": self.worker.worker_id}
        if op == "STEP":
            result = self.worker.step()
            if result is None:
                return {"idle": True}
            task_id, state = result
            return {"idle": False, "task_id": task_id, "state": state}
        if op == "STOP":
            self.worker.stop()
            return {"stopped": True}
        raise ProtocolError("V10_OPCODE_DENIED")


def serve_unix(
    socket_path: str,
    broker: ConsumeOnlyBroker,
    replay_store: DurableReplayStore,
    *,
    max_requests: int = 1000,
) -> int:
    if not isinstance(socket_path, str) or not socket_path.startswith("/") or len(socket_path.encode()) > 100:
        raise ValueError("V10_UNIX_SOCKET_PATH_BOUND")
    if type(replay_store) is not DurableReplayStore:
        raise TypeError("V10_EXACT_REPLAY_STORE_REQUIRED")
    if isinstance(max_requests, bool) or not isinstance(max_requests, int) or not (1 <= max_requests <= 10000):
        raise ValueError("V10_MAX_REQUESTS_BOUND")
    try:
        os.unlink(socket_path)
    except FileNotFoundError:
        pass
    served = 0
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(socket_path)
        os.chmod(socket_path, 0o600)
        server.listen(8)
        while served < max_requests:
            conn, _ = server.accept()
            with conn:
                chunks = bytearray()
                while True:
                    part = conn.recv(1024)
                    if not part:
                        break
                    chunks.extend(part)
                    if len(chunks) > MAX_MESSAGE_BYTES:
                        break
                    if b"\n" in chunks:
                        break
                raw = bytes(chunks).split(b"\n", 1)[0]
                request_id = "invalid"
                try:
                    request = _decode_request(raw)
                    request_id = request["request_id"]
                    replay_store.reserve(request)
                    body = _response(request_id, True, broker.dispatch(request))
                except Exception as exc:
                    body = _response(request_id, False, error=f"{type(exc).__name__}:{exc}")
                conn.sendall(body)
                served += 1
    try:
        os.unlink(socket_path)
    except FileNotFoundError:
        pass
    return served


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--task-db", required=True)
    parser.add_argument("--bridge-db", required=True)
    parser.add_argument("--provider-db", required=True)
    parser.add_argument("--replay-db", required=True)
    parser.add_argument("--candidate-branch", required=True)
    parser.add_argument("--candidate-head", required=True)
    parser.add_argument("--lease", type=float, default=120.0)
    parser.add_argument("--heartbeat", type=float, default=20.0)
    parser.add_argument("--poll", type=float, default=0.25)
    parser.add_argument("--max-requests", type=int, default=1000)
    args = parser.parse_args()
    db_paths = [args.task_db, args.bridge_db, args.provider_db, args.replay_db]
    if any(not isinstance(p, str) or not os.path.isabs(p) for p in db_paths):
        raise ValueError("V10_ABSOLUTE_DB_PATHS_REQUIRED")
    real_db_paths = [os.path.realpath(p) for p in db_paths]
    if len(set(real_db_paths)) != len(real_db_paths):
        raise ValueError("V10_REPLAY_DB_MUST_BE_DISTINCT")
    for i, left in enumerate(db_paths):
        for right in db_paths[i + 1:]:
            try:
                if os.path.samefile(left, right):
                    raise ValueError("V10_REPLAY_DB_MUST_BE_DISTINCT")
            except FileNotFoundError:
                pass
    socket_real = os.path.realpath(args.socket)
    if socket_real in set(real_db_paths):
        raise ValueError("V10_SOCKET_DB_PATH_COLLISION")
    for path in db_paths:
        try:
            if os.path.samefile(args.socket, path):
                raise ValueError("V10_SOCKET_DB_PATH_COLLISION")
        except FileNotFoundError:
            pass
    config.DB_PATH = args.task_db
    binding = IntegrationBinding(CANONICAL_MAIN, args.candidate_branch, args.candidate_head, V7_HEAD)
    replay_store = DurableReplayStore(args.replay_db)
    broker = ConsumeOnlyBroker(binding, args.bridge_db, args.provider_db,
                               WorkerConfig(args.lease, args.heartbeat, args.poll).validate())
    try:
        return 0 if serve_unix(args.socket, broker, replay_store, max_requests=args.max_requests) >= 0 else 1
    finally:
        broker.worker.stop()


if __name__ == "__main__":
    raise SystemExit(main())
