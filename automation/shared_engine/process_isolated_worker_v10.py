"""Candidate-only client for the v10 process-isolated consume-only worker.

This client never imports Shared Engine, v9 worker, task DB, provider adapter, or
receipt classes. Its only capability is a bounded local AF_UNIX JSON protocol.
It is not an authenticated worker boundary and does not protect against a
privileged/same-OS-user attacker controlling the broker process or filesystem.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import socket
import uuid

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
MAX_RUN_CYCLES = 1000
ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})


class IPCError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClientConfig:
    socket_path: str
    timeout_seconds: float = 5.0

    def validate(self) -> "ClientConfig":
        if not isinstance(self.socket_path, str) or not self.socket_path.startswith("/"):
            raise ValueError("V10_ABSOLUTE_UNIX_SOCKET_REQUIRED")
        if len(self.socket_path.encode("utf-8")) > 100:
            raise ValueError("V10_UNIX_SOCKET_PATH_BOUND")
        timeout = float(self.timeout_seconds)
        if not (0.05 <= timeout <= 10.0):
            raise ValueError("V10_TIMEOUT_BOUND")
        return self


def _reject_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise IPCError("V10_DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _decode_exact_object(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_MESSAGE_BYTES:
        raise IPCError("V10_RESPONSE_SIZE_BOUND")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IPCError("V10_INVALID_JSON") from exc
    if type(value) is not dict:
        raise IPCError("V10_OBJECT_REQUIRED")
    return value


class ProcessIsolatedWorkerClient:
    """Narrow local client. No engine/task-creation capability is retained or exposed."""

    def __init__(self, config: ClientConfig):
        if type(config) is not ClientConfig:
            raise TypeError("V10_EXACT_CLIENT_CONFIG_REQUIRED")
        self.config = config.validate()
        self.client_id = f"piw10-client-{os.getpid()}-{uuid.uuid4().hex[:12]}"

    def _request(self, op: str) -> dict:
        if op not in ALLOWED_OPS:
            raise ValueError("V10_OPCODE_DENIED")
        request_id = uuid.uuid4().hex
        payload = {"v": PROTOCOL_VERSION, "op": op, "request_id": request_id}
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise IPCError("V10_REQUEST_SIZE_BOUND")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(float(self.config.timeout_seconds))
            sock.connect(self.config.socket_path)
            sock.sendall(encoded)
            chunks = bytearray()
            while True:
                part = sock.recv(1024)
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > MAX_MESSAGE_BYTES:
                    raise IPCError("V10_RESPONSE_SIZE_BOUND")
                if b"\n" in chunks:
                    break
        raw = bytes(chunks).split(b"\n", 1)[0]
        response = _decode_exact_object(raw)
        if set(response) != {"v", "request_id", "ok", "result", "error"}:
            raise IPCError("V10_RESPONSE_SCHEMA")
        if response["v"] != PROTOCOL_VERSION or response["request_id"] != request_id:
            raise IPCError("V10_RESPONSE_BINDING")
        if type(response["ok"]) is not bool:
            raise IPCError("V10_RESPONSE_BOOL")
        if not response["ok"]:
            raise IPCError(str(response["error"]))
        if response["error"] is not None or type(response["result"]) is not dict:
            raise IPCError("V10_RESPONSE_RESULT")
        return response["result"]

    def ping(self) -> dict:
        return self._request("PING")

    def step(self) -> dict:
        return self._request("STEP")

    def stop(self) -> dict:
        return self._request("STOP")

    def run(self, *, max_cycles: int = 100) -> int:
        if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not (1 <= max_cycles <= MAX_RUN_CYCLES):
            raise ValueError("V10_RUN_CYCLE_BOUND")
        completed = 0
        for _ in range(max_cycles):
            result = self.step()
            if result.get("idle") is True:
                continue
            completed += 1
        return completed
