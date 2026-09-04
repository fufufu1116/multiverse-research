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


@dataclass(frozen=True)
class DeploymentManifest:
    adopted_runtime_head: str
    canonical_main: str
    mode: str
    runtime: str
    target_environment: str
    artifact_sha256: str
    rollback_ref: str
    credential_source: str
    credential_persistence: bool
    capabilities: dict[str, bool]

    def validate(self) -> None:
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
        if len(self.artifact_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.artifact_sha256):
            raise DeploymentGateError("ARTIFACT_SHA256_REQUIRED")
        if self.rollback_ref != ADOPTED_RUNTIME_HEAD:
            raise DeploymentGateError("ROLLBACK_BINDING_REQUIRED")

    def receipt(self) -> dict[str, Any]:
        self.validate()
        return {"status": "PASS", **asdict(self)}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_bytes(source: str | Path, snapshot: str | Path) -> dict[str, str]:
    source = Path(source)
    snapshot = Path(snapshot)
    data = source.read_bytes()
    snapshot.write_bytes(data)
    return {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    }


def restore_bytes(snapshot: str | Path, restored: str | Path) -> dict[str, str]:
    snapshot = Path(snapshot)
    restored = Path(restored)
    data = snapshot.read_bytes()
    restored.write_bytes(data)
    return {
        "snapshot_sha256": hashlib.sha256(data).hexdigest(),
        "restored_sha256": hashlib.sha256(restored.read_bytes()).hexdigest(),
    }


def health_receipt(manifest: DeploymentManifest, *, kill_switch_engaged: bool) -> dict[str, Any]:
    manifest.validate()
    if kill_switch_engaged is not True:
        raise DeploymentGateError("KILL_SWITCH_MUST_REMAIN_ENGAGED")
    return {
        "schema_version": "MULTIVERSE_RUNTIME_DEPLOYMENT_HEALTH_v1",
        "runtime": "OFF",
        "ready_for_live_activation": False,
        "kill_switch_engaged": True,
        "manifest": manifest.receipt(),
    }


def canonical_json_sha256(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
