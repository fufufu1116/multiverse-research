"""Fail-closed PRE_PRODUCTION wrapper for PreparedPostgresRuntimeBridge validation."""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from automation.postgres_runtime_bridge_preprod_v1.bridge_validation import (
    EXECUTION_STATE,
    PROOF_CEILING,
    RUNTIME,
    RUNTIME_ID,
    run_bridge_validation,
)
from automation.runtime_postgres_adapter_v1.postgres_adapter import (
    PostgresDistributedControlStore,
)

TARGET_CLASS = "RENDER_PREPRODUCTION_POSTGRES_RUNTIME_BRIDGE_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
EXPECTED_POSTGRES_ID = "dpg-dadou0on74is73b09570-a"
EXECUTION_AUTHORITY = "OWNER_AUTHORIZED_POSTGRES_RUNTIME_BRIDGE_PREPROD_V1"

STATE: dict[str, Any] = {
    "ready": False,
    "database_bound": False,
    "execution_authorized": False,
    "complete": False,
    "last_error": None,
    "evidence": None,
}


class BridgeExecutionViolation(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _required(name: str, env: Any) -> str:
    value = env.get(name)
    if value is None or value == "":
        raise BridgeExecutionViolation(f"MISSING_{name}")
    return value


def validate_nonsecret_environment(env: dict[str, str] | None = None) -> dict[str, str]:
    source = os.environ if env is None else env
    exact = {
        "MULTIVERSE_TARGET_CLASS": TARGET_CLASS,
        "MULTIVERSE_ENVIRONMENT_CLASS": ENVIRONMENT_CLASS,
        "MULTIVERSE_POSTGRES_RUNTIME_BRIDGE_EXECUTION_AUTHORITY": EXECUTION_AUTHORITY,
        "MULTIVERSE_RUNTIME": RUNTIME,
        "MULTIVERSE_RUNTIME_ACTIVATION_BRIDGE_ENABLED": "false",
        "MULTIVERSE_PROVIDER_EFFECT_ADAPTER_ENABLED": "false",
        "MULTIVERSE_LIVE_BUSINESS_EFFECT": "false",
        "MULTIVERSE_PROTECTED_KEIRIN_DATA": "false",
        "MULTIVERSE_PRODUCTION_CREDENTIALS": "false",
        "MULTIVERSE_INCREMENTAL_SPEND_USD": "0",
        "MULTIVERSE_EXPECTED_POSTGRES_ID": EXPECTED_POSTGRES_ID,
        "MULTIVERSE_RUNTIME_ID": RUNTIME_ID,
    }

    for key, expected in exact.items():
        actual = _required(key, source)
        if actual != expected:
            raise BridgeExecutionViolation(f"{key}_MISMATCH")
    return exact


def build_connection_factory() -> Callable[[], Any]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise BridgeExecutionViolation("DATABASE_URL_MISSING")

    import psycopg

    def connect() -> Any:
        return psycopg.connect(database_url)

    return connect


def execute_remote_validation() -> None:
    try:
        validate_nonsecret_environment()
        STATE["execution_authorized"] = True

        store = PostgresDistributedControlStore(
            runtime_id=RUNTIME_ID,
            connection_factory=build_connection_factory(),
        )
        store.initialize_schema()

        evidence = run_bridge_validation(store)
        STATE["database_bound"] = True
        STATE["evidence"] = evidence
        STATE["complete"] = bool(evidence.get("complete"))
        STATE["ready"] = True

    except Exception as exc:
        STATE["last_error"] = f"{type(exc).__name__}:{exc}"
        STATE["ready"] = False


class Handler(BaseHTTPRequestHandler):
    server_version = "MULTIVERSE-PostgresRuntimeBridge-NoEffect/1"

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "runtime": RUNTIME,
                    "target_class": TARGET_CLASS,
                    "proof_ceiling": PROOF_CEILING,
                    "execution_state": EXECUTION_STATE,
                },
            )
            return

        if self.path == "/ready":
            self._send_json(
                200 if STATE["ready"] else 503,
                {
                    "ready": STATE["ready"],
                    "database_bound": STATE["database_bound"],
                    "execution_authorized": STATE["execution_authorized"],
                    "complete": STATE["complete"],
                    "last_error": STATE["last_error"],
                    "runtime_activation_bridge_enabled": False,
                    "activation_ready": False,
                    "runtime": RUNTIME,
                },
            )
            return

        if self.path == "/evidence":
            if STATE["evidence"] is None:
                self._send_json(
                    503,
                    {
                        "error": STATE["last_error"] or "evidence_not_ready",
                        "runtime": RUNTIME,
                    },
                )
            else:
                self._send_json(200, dict(STATE["evidence"]))
            return

        self._send_json(404, {"error": "not_found", "runtime": RUNTIME})

    def _deny(self) -> None:
        self._send_json(
            403,
            {
                "error": "state_changes_disabled_over_http",
                "runtime": RUNTIME,
            },
        )

    def do_POST(self) -> None:
        self._deny()

    def do_PUT(self) -> None:
        self._deny()

    def do_PATCH(self) -> None:
        self._deny()

    def do_DELETE(self) -> None:
        self._deny()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(
            json.dumps(
                {
                    "component": "http",
                    "message": fmt % args,
                    "runtime": RUNTIME,
                },
                sort_keys=True,
            ),
            flush=True,
        )


def main() -> None:
    validate_nonsecret_environment()

    thread = threading.Thread(
        target=execute_remote_validation,
        name="postgres-runtime-bridge-validation",
        daemon=True,
    )
    thread.start()

    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
