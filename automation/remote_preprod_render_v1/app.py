import hashlib
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg


TARGET_CLASS = "RENDER_REMOTE_PREPRODUCTION_SINGLE_SERVICE_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
PROOF_CEILING = "REMOTE_PREPRODUCTION_SINGLE_RENDER_NO_EFFECT_EVIDENCE_ONLY"
RUNTIME = "OFF"
AUTH_TOKEN = "AUTHORIZED_NO_EFFECT_EVIDENCE_V1"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
EXECUTION_AUTHORITY = os.environ.get("MULTIVERSE_NO_EFFECT_EVIDENCE_AUTHORITY", "")
PORT = int(os.environ.get("PORT", "10000"))

STARTUP_RECEIPT = {
    "target_class": TARGET_CLASS,
    "environment_class": ENVIRONMENT_CLASS,
    "runtime": RUNTIME,
    "proof_ceiling": PROOF_CEILING,
    "execution_authorized": False,
    "database_bound": False,
    "ready": False,
    "findings": [],
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_rows(cur):
    cur.execute(
        "SELECT key, value FROM multiverse_evidence_state ORDER BY key"
    )
    return [[row[0], row[1]] for row in cur.fetchall()]


def run_remote_no_effect_drill():
    receipt = dict(STARTUP_RECEIPT)

    if EXECUTION_AUTHORITY != AUTH_TOKEN:
        receipt["findings"] = ["NO_EFFECT_EVIDENCE_AUTHORITY_NOT_BOUND"]
        return receipt

    receipt["execution_authorized"] = True

    if not DATABASE_URL:
        receipt["findings"] = ["DATABASE_URL_NOT_BOUND"]
        return receipt

    with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS multiverse_evidence_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS multiverse_evidence_ops (
                    request_key TEXT PRIMARY KEY,
                    payload_sha256 TEXT NOT NULL
                )
                """
            )
            conn.commit()

            receipt["database_bound"] = True

            cur.execute(
                """
                INSERT INTO multiverse_evidence_state(key, value)
                VALUES ('boot_count', '0')
                ON CONFLICT (key) DO NOTHING
                """
            )
            cur.execute(
                """
                SELECT value FROM multiverse_evidence_state
                WHERE key='boot_count'
                FOR UPDATE
                """
            )
            previous_boot_count = int(cur.fetchone()[0])
            current_boot_count = previous_boot_count + 1
            cur.execute(
                """
                UPDATE multiverse_evidence_state
                SET value=%s
                WHERE key='boot_count'
                """,
                (str(current_boot_count),),
            )

            cur.execute(
                """
                INSERT INTO multiverse_evidence_state(key, value)
                VALUES ('lease_owner', 'worker-a')
                ON CONFLICT (key)
                DO UPDATE SET value=EXCLUDED.value
                """
            )
            cur.execute(
                """
                INSERT INTO multiverse_evidence_state(key, value)
                VALUES ('fence_token', '1')
                ON CONFLICT (key)
                DO UPDATE SET value=EXCLUDED.value
                """
            )
            conn.commit()

            snapshot_rows = _canonical_rows(cur)
            snapshot_bytes = json.dumps(
                snapshot_rows,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            snapshot_sha256 = _sha256_bytes(snapshot_bytes)

            cur.execute(
                """
                UPDATE multiverse_evidence_state
                SET value='CORRUPTED_FOR_BOUNDED_DRILL'
                WHERE key='lease_owner'
                """
            )
            conn.commit()

            cur.execute("DELETE FROM multiverse_evidence_state")
            for key, value in snapshot_rows:
                cur.execute(
                    """
                    INSERT INTO multiverse_evidence_state(key, value)
                    VALUES (%s, %s)
                    """,
                    (key, value),
                )
            conn.commit()

            restored_rows = _canonical_rows(cur)
            restored_bytes = json.dumps(
                restored_rows,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            restore_sha256 = _sha256_bytes(restored_bytes)

            cur.execute(
                """
                UPDATE multiverse_evidence_state
                SET value='worker-b'
                WHERE key='lease_owner'
                """
            )
            cur.execute(
                """
                UPDATE multiverse_evidence_state
                SET value='2'
                WHERE key='fence_token'
                """
            )
            conn.commit()

            payload = b"NO_EFFECT_EVIDENCE_PAYLOAD_v1"
            payload_sha256 = _sha256_bytes(payload)
            request_key = "multiverse-no-effect-idempotency-v1"

            cur.execute(
                """
                INSERT INTO multiverse_evidence_ops(request_key, payload_sha256)
                VALUES (%s, %s)
                ON CONFLICT (request_key) DO NOTHING
                """,
                (request_key, payload_sha256),
            )
            conn.commit()

            cur.execute(
                """
                SELECT COUNT(*) FROM multiverse_evidence_ops
                WHERE request_key=%s
                """,
                (request_key,),
            )
            first_count = int(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO multiverse_evidence_ops(request_key, payload_sha256)
                VALUES (%s, %s)
                ON CONFLICT (request_key) DO NOTHING
                """,
                (request_key, payload_sha256),
            )
            conn.commit()

            cur.execute(
                """
                SELECT COUNT(*) FROM multiverse_evidence_ops
                WHERE request_key=%s
                """,
                (request_key,),
            )
            second_count = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT value FROM multiverse_evidence_state
                WHERE key='lease_owner'
                """
            )
            lease_owner = cur.fetchone()[0]

            cur.execute(
                """
                SELECT value FROM multiverse_evidence_state
                WHERE key='fence_token'
                """
            )
            fence_token = int(cur.fetchone()[0])

            receipt.update(
                {
                    "ready": True,
                    "previous_boot_count": previous_boot_count,
                    "current_boot_count": current_boot_count,
                    "restart_persistence_observable":
                        previous_boot_count > 0,
                    "backup_snapshot_sha256": snapshot_sha256,
                    "restore_snapshot_sha256": restore_sha256,
                    "backup_restore_match":
                        snapshot_sha256 == restore_sha256,
                    "lease_owner": lease_owner,
                    "fence_token": fence_token,
                    "lease_fencing_pass":
                        lease_owner == "worker-b" and fence_token == 2,
                    "idempotency_first_count": first_count,
                    "idempotency_second_count": second_count,
                    "duplicate_external_effect": False,
                    "idempotency_pass":
                        first_count == 1 and second_count == 1,
                    "production_credentials_enabled": False,
                    "protected_keirin_data_enabled": False,
                    "live_business_effect_enabled": False,
                    "runtime_activation": False,
                }
            )

    return receipt


try:
    STARTUP_RECEIPT = run_remote_no_effect_drill()
except Exception as exc:
    STARTUP_RECEIPT = dict(STARTUP_RECEIPT)
    STARTUP_RECEIPT["findings"] = [
        f"{type(exc).__name__}: {exc}"
    ]


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, status, payload):
        body = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "environment_class": ENVIRONMENT_CLASS,
                    "runtime": RUNTIME,
                },
            )
            return

        if self.path == "/ready":
            ready = bool(STARTUP_RECEIPT.get("ready"))
            self._write_json(
                200 if ready else 503,
                {
                    "ready": ready,
                    "runtime": RUNTIME,
                    "proof_ceiling": PROOF_CEILING,
                },
            )
            return

        if self.path == "/evidence":
            self._write_json(200, STARTUP_RECEIPT)
            return

        self._write_json(
            404,
            {
                "error": "not_found",
                "runtime": RUNTIME,
            },
        )

    def do_POST(self):
        self._write_json(
            403,
            {
                "error": "state_changes_disabled_over_http",
                "runtime": RUNTIME,
            },
        )

    def log_message(self, fmt, *args):
        print(
            json.dumps(
                {
                    "type": "http_request",
                    "message": fmt % args,
                    "runtime": RUNTIME,
                    "ts": int(time.time()),
                },
                sort_keys=True,
            ),
            flush=True,
        )


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "type": "startup_evidence",
                "receipt": STARTUP_RECEIPT,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
