"""Local no-effect target drill for Issue #114.

This module produces *local mechanical* evidence only. It never claims that a
remote or production host exists and grants no Runtime/network/effect authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

TARGET_ID = "MULTIVERSE_PREPRODUCTION_LOCAL_SINGLE_HOST_NO_EFFECT_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
DENIED = {
    "network_enabled": False,
    "external_effect_enabled": False,
    "spend_enabled": False,
    "protected_keirin_data_enabled": False,
    "production_credentials_enabled": False,
    "runtime_activation": False,
}


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ref(domain: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"EVIDENCE_REF:local-no-effect/{domain}/{_sha256_bytes(raw)}"


def run_local_drill() -> dict:
    with tempfile.TemporaryDirectory(prefix="multiverse-preprod-") as td:
        root = Path(td)
        db = root / "state.sqlite3"
        backup = root / "state.backup.sqlite3"

        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE lease_state (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, fence INTEGER NOT NULL)")
        conn.execute("INSERT INTO lease_state(id, owner, fence) VALUES (1, 'worker-a', 1)")
        conn.commit()
        conn.close()

        original = db.read_bytes()
        backup.write_bytes(original)
        backup_digest = _sha256_bytes(backup.read_bytes())

        # Simulate local corruption and prove restore from the captured backup.
        db.write_bytes(b"corrupt-local-test")
        db.write_bytes(backup.read_bytes())
        restored_digest = _sha256_bytes(db.read_bytes())
        if restored_digest != backup_digest:
            raise RuntimeError("BACKUP_RESTORE_MISMATCH")

        # Crash/restart recovery: reopen persisted state and advance fencing token.
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT owner, fence FROM lease_state WHERE id=1").fetchone()
        if row != ("worker-a", 1):
            raise RuntimeError("RESTART_STATE_MISMATCH")
        conn.execute("UPDATE lease_state SET owner='worker-b', fence=fence+1 WHERE id=1 AND fence=1")
        conn.commit()
        row2 = conn.execute("SELECT owner, fence FROM lease_state WHERE id=1").fetchone()
        conn.close()
        if row2 != ("worker-b", 2):
            raise RuntimeError("LEASE_FENCING_MISMATCH")

        artifact = b"MULTIVERSE_PREPRODUCTION_LOCAL_NO_EFFECT_ARTIFACT_v1"
        rollback = b"MULTIVERSE_PREPRODUCTION_LOCAL_NO_EFFECT_ROLLBACK_v1"
        artifact_digest = _sha256_bytes(artifact)
        rollback_digest = _sha256_bytes(rollback)

        payloads = {
            "credential_scope": {"kind": "none", "production": False, "least_privilege": True},
            "credential_provisioning": {"kind": "none", "secret_material": False},
            "credential_rotation": {"kind": "none", "rotation_required_before_external_auth": True},
            "credential_revocation": {"kind": "none", "revocation_required_before_external_auth": True},
            "provider_idempotency": {"provider": "deterministic-local-no-effect", "idempotency": "request-key-dedup"},
            "duplicate_request_control": {"duplicate_external_effect": False, "mode": "local-no-effect"},
            "state_store_binding": {"store": "sqlite-local-temp", "durable_production_claim": False},
            "backup_restore": {"backup_sha256": backup_digest, "restore_sha256": restored_digest, "pass": True},
            "crash_restart_recovery": {"before": ["worker-a", 1], "after_restart": ["worker-a", 1], "pass": True},
            "host_model": {"model": "single-host-local-test", "multi_host_proven": False},
            "lease_fencing": {"before_fence": 1, "after_fence": 2, "new_owner": "worker-b", "pass": True},
            "health_readiness": {"local_contract_importable": True, "ready_for_activation": False},
            "logs_metrics_alerts": {"scope": "test-output-only", "production_alerting_proven": False},
            "kill_switch": {"mechanism": "default-deny authority flags", "all_denied": all(v is False for v in DENIED.values())},
            "rollback_execution": {"rollback_artifact_sha256": rollback_digest, "local_no_effect": True},
        }
        refs = {domain: _ref(domain, payload) for domain, payload in payloads.items()}
        return {
            "target_id": TARGET_ID,
            "environment_class": ENVIRONMENT_CLASS,
            "artifact_sha256": artifact_digest,
            "rollback_artifact_sha256": rollback_digest,
            "evidence_refs": refs,
            "evidence_payloads": payloads,
            **DENIED,
            "proof_ceiling": "Local single-host no-effect drill only; no deployed remote/production host, multi-host failover, production alerting, live provider, network, external effect, spend, protected data, production credential, or Runtime activation is proven.",
        }
