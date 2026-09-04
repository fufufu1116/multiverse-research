"""MULTIVERSE Runtime deployment-evidence v1 — sealed, no-effect validation surface."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
from typing import Any

ADOPTED_RUNTIME_HEAD = "8685193cc6d592a36ea78bc7a8647ceadce13ae6"
CANONICAL_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
MODE = "SEALED_DEPLOYMENT_VALIDATION"
RUNTIME = "OFF"
TARGET_ENVIRONMENT = "LOCAL_SEALED_DRY_RUN"
SNAPSHOT_SCHEMA = "MULTIVERSE_RUNTIME_STATE_SNAPSHOT_v1"


class DeploymentGateError(RuntimeError):
    pass


DEFAULT_DENY_CAPABILITIES = {
    "production": False,
    "runtime_activation": False,
    "live_provider": False,
    "network": False,
    "external_effect": False,
    "spend": False,
    "protected_keirin_data": False,
    "secret_persistence": False,
    "workflow_dispatch_rerun": False,
    "main_mutation": False,
    "ruleset_mutation": False,
}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class DeploymentManifest:
    adopted_runtime_head: str
    canonical_main: str
    mode: str
    runtime: str
    target_environment: str
    artifact_sha256: str
    rollback_ref: str
    rollback_artifact_sha256: str
    credential_source: str
    credential_persistence: bool
    capabilities: dict[str, bool]

    def validate(
        self,
        *,
        artifact_path: str | Path,
        rollback_artifact_path: str | Path,
    ) -> None:
        if self.adopted_runtime_head != ADOPTED_RUNTIME_HEAD:
            raise DeploymentGateError("ADOPTED_RUNTIME_HEAD_MISMATCH")
        if self.canonical_main != CANONICAL_MAIN:
            raise DeploymentGateError("CANONICAL_MAIN_MISMATCH")
        if self.mode != MODE or self.runtime != RUNTIME:
            raise DeploymentGateError("SEALED_MODE_REQUIRED")
        if self.target_environment != TARGET_ENVIRONMENT:
            raise DeploymentGateError("TARGET_ENVIRONMENT_MISMATCH")
        if self.credential_source != "INJECTED_EPHEMERAL_ONLY":
            raise DeploymentGateError("EPHEMERAL_CREDENTIAL_INJECTION_REQUIRED")
        if self.credential_persistence is not False:
            raise DeploymentGateError("SECRET_PERSISTENCE_FORBIDDEN")
        if self.capabilities != DEFAULT_DENY_CAPABILITIES:
            raise DeploymentGateError("CAPABILITY_DEFAULT_DENY_REQUIRED")
        if self.rollback_ref != ADOPTED_RUNTIME_HEAD:
            raise DeploymentGateError("ROLLBACK_BINDING_REQUIRED")

        artifact_path = Path(artifact_path)
        rollback_artifact_path = Path(rollback_artifact_path)
        if not artifact_path.is_file():
            raise DeploymentGateError("DEPLOYMENT_ARTIFACT_MISSING")
        if not rollback_artifact_path.is_file():
            raise DeploymentGateError("ROLLBACK_ARTIFACT_MISSING")

        actual_artifact_sha = sha256_file(artifact_path)
        actual_rollback_sha = sha256_file(rollback_artifact_path)
        if self.artifact_sha256 != actual_artifact_sha:
            raise DeploymentGateError("DEPLOYMENT_ARTIFACT_DIGEST_MISMATCH")
        if self.rollback_artifact_sha256 != actual_rollback_sha:
            raise DeploymentGateError("ROLLBACK_ARTIFACT_DIGEST_MISMATCH")

    def receipt(
        self,
        *,
        artifact_path: str | Path,
        rollback_artifact_path: str | Path,
    ) -> dict[str, Any]:
        self.validate(
            artifact_path=artifact_path,
            rollback_artifact_path=rollback_artifact_path,
        )
        return {"status": "PASS", **asdict(self)}


@dataclass(frozen=True)
class SnapshotIntegrityReceipt:
    schema_version: str
    snapshot_identity: str
    adopted_runtime_head: str
    canonical_main: str
    source_sha256: str
    snapshot_sha256: str
    byte_length: int

    def validate_metadata(
        self,
        *,
        expected_identity: str,
        expected_runtime_head: str,
        expected_main: str,
    ) -> None:
        if self.schema_version != SNAPSHOT_SCHEMA:
            raise DeploymentGateError("SNAPSHOT_SCHEMA_MISMATCH")
        if self.snapshot_identity != expected_identity:
            raise DeploymentGateError("SNAPSHOT_IDENTITY_MISMATCH")
        if self.adopted_runtime_head != expected_runtime_head:
            raise DeploymentGateError("SNAPSHOT_RUNTIME_HEAD_MISMATCH")
        if self.canonical_main != expected_main:
            raise DeploymentGateError("SNAPSHOT_MAIN_MISMATCH")
        if self.source_sha256 != self.snapshot_sha256:
            raise DeploymentGateError("SNAPSHOT_SOURCE_DIGEST_MISMATCH")
        if self.byte_length < 0:
            raise DeploymentGateError("SNAPSHOT_LENGTH_INVALID")


def snapshot_bytes(
    source: str | Path,
    snapshot: str | Path,
    *,
    snapshot_identity: str,
) -> dict[str, Any]:
    if not snapshot_identity or snapshot_identity.strip() != snapshot_identity:
        raise DeploymentGateError("SNAPSHOT_IDENTITY_REQUIRED")
    source = Path(source)
    snapshot = Path(snapshot)
    data = source.read_bytes()
    snapshot.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    receipt = SnapshotIntegrityReceipt(
        schema_version=SNAPSHOT_SCHEMA,
        snapshot_identity=snapshot_identity,
        adopted_runtime_head=ADOPTED_RUNTIME_HEAD,
        canonical_main=CANONICAL_MAIN,
        source_sha256=digest,
        snapshot_sha256=sha256_file(snapshot),
        byte_length=len(data),
    )
    receipt.validate_metadata(
        expected_identity=snapshot_identity,
        expected_runtime_head=ADOPTED_RUNTIME_HEAD,
        expected_main=CANONICAL_MAIN,
    )
    return asdict(receipt)


def restore_bytes(
    snapshot: str | Path,
    restored: str | Path,
    *,
    expected_receipt: dict[str, Any],
    expected_identity: str,
    expected_runtime_head: str = ADOPTED_RUNTIME_HEAD,
    expected_main: str = CANONICAL_MAIN,
) -> dict[str, Any]:
    try:
        receipt = SnapshotIntegrityReceipt(**expected_receipt)
    except (TypeError, KeyError) as e:
        raise DeploymentGateError("SNAPSHOT_RECEIPT_INVALID") from e

    receipt.validate_metadata(
        expected_identity=expected_identity,
        expected_runtime_head=expected_runtime_head,
        expected_main=expected_main,
    )

    snapshot = Path(snapshot)
    restored = Path(restored)
    if not snapshot.is_file():
        raise DeploymentGateError("SNAPSHOT_MISSING")
    data = snapshot.read_bytes()
    actual_snapshot_sha = hashlib.sha256(data).hexdigest()
    if actual_snapshot_sha != receipt.snapshot_sha256:
        raise DeploymentGateError("SNAPSHOT_DIGEST_MISMATCH")
    if len(data) != receipt.byte_length:
        raise DeploymentGateError("SNAPSHOT_LENGTH_MISMATCH")

    restored.write_bytes(data)
    restored_sha = sha256_file(restored)
    if restored_sha != receipt.source_sha256:
        restored.unlink(missing_ok=True)
        raise DeploymentGateError("RESTORED_DIGEST_MISMATCH")

    return {
        "schema_version": receipt.schema_version,
        "snapshot_identity": receipt.snapshot_identity,
        "snapshot_sha256": actual_snapshot_sha,
        "restored_sha256": restored_sha,
        "byte_length": len(data),
        "integrity": "PASS",
    }


def health_receipt(
    manifest: DeploymentManifest,
    *,
    kill_switch_engaged: bool,
    artifact_path: str | Path,
    rollback_artifact_path: str | Path,
) -> dict[str, Any]:
    manifest.validate(
        artifact_path=artifact_path,
        rollback_artifact_path=rollback_artifact_path,
    )
    if kill_switch_engaged is not True:
        raise DeploymentGateError("KILL_SWITCH_MUST_REMAIN_ENGAGED")
    return {
        "schema_version": "MULTIVERSE_RUNTIME_DEPLOYMENT_HEALTH_v1",
        "runtime": "OFF",
        "ready_for_live_activation": False,
        "kill_switch_engaged": True,
        "manifest": manifest.receipt(
            artifact_path=artifact_path,
            rollback_artifact_path=rollback_artifact_path,
        ),
    }


def canonical_json_sha256(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
