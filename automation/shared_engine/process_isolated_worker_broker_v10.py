"""Trusted local broker for v10 process isolation.

The full v9/PR91/PR88 capability exists only in this broker process. The IPC
surface is an explicit JSON allowlist and never exposes task creation or generic
dispatch. This is bounded local-process evidence, not a deployed daemon.
"""
from __future__ import annotations

import argparse
import json
import os
import socket

import config
from canonical_v7_binding import CANONICAL_MAIN, V7_HEAD
from integration_bridge import IntegrationBinding
from local_persistent_worker_v9 import LocalPersistentWorker, WorkerConfig

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})
REQUEST_KEYS = frozenset({"v", "op", "request_id"})


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
    if value["v"] != PROTOCOL_VERSION:
        raise ProtocolError("V10_PROTOCOL_VERSION")
    if value["op"] not in ALLOWED_OPS:
        raise ProtocolError("V10_OPCODE_DENIED")
    if not isinstance(value["request_id"], str) or not (1 <= len(value["request_id"]) <= 64):
        raise ProtocolError("V10_REQUEST_ID_BOUND")
    return value


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


def serve_unix(socket_path: str, broker: ConsumeOnlyBroker, *, max_requests: int = 1000) -> int:
    if not isinstance(socket_path, str) or not socket_path.startswith("/") or len(socket_path.encode()) > 100:
        raise ValueError("V10_UNIX_SOCKET_PATH_BOUND")
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
    parser.add_argument("--candidate-branch", required=True)
    parser.add_argument("--candidate-head", required=True)
    parser.add_argument("--lease", type=float, default=120.0)
    parser.add_argument("--heartbeat", type=float, default=20.0)
    parser.add_argument("--poll", type=float, default=0.25)
    parser.add_argument("--max-requests", type=int, default=1000)
    args = parser.parse_args()
    config.DB_PATH = args.task_db
    binding = IntegrationBinding(CANONICAL_MAIN, args.candidate_branch, args.candidate_head, V7_HEAD)
    broker = ConsumeOnlyBroker(binding, args.bridge_db, args.provider_db,
                               WorkerConfig(args.lease, args.heartbeat, args.poll).validate())
    try:
        return 0 if serve_unix(args.socket, broker, max_requests=args.max_requests) >= 0 else 1
    finally:
        broker.worker.stop()


if __name__ == "__main__":
    raise SystemExit(main())
