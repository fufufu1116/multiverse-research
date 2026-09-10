"""MULTIVERSE target-environment evidence v1 — fail-closed, no activation authority."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any

CANONICAL_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
ADOPTED_RUNTIME_HEAD = "8685193cc6d592a36ea78bc7a8647ceadce13ae6"
ADOPTED_DEPLOYMENT_HEAD = "722465fda607198858e48f66ec9b936430ff3d6a"
RUNTIME = "OFF"
MODE = "TARGET_ENVIRONMENT_EVIDENCE_ONLY"
ALLOWED_ENVIRONMENT_CLASSES = {"PRE_PRODUCTION", "PRODUCTION_SHADOW_NO_EFFECT"}
REQUIRED_EVIDENCE_DOMAINS = {
    "credential_scope",
    "credential_provisioning",
    "credential_rotation",
    "credential_revocation",
    "provider_idempotency",
    "duplicate_request_control",
    "state_store_binding",
    "backup_restore",
    "crash_restart_recovery",
    "host_model",
    "lease_fencing",
    "health_readiness",
    "logs_metrics_alerts",
    "kill_switch",
    "rollback_execution",
}

class TargetEnvironmentGateError(RuntimeError):
    pass

def _exact_str(value: object, error: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise TargetEnvironmentGateError(error)
    return value

def _sha256(value: object, error: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise TargetEnvironmentGateError(error)
    return value

def _evidence_ref(value: object, error: str) -> str:
    value = _exact_str(value, error)
    if not value.startswith("EVIDENCE_REF:") or len(value) <= len("EVIDENCE_REF:"):
        raise TargetEnvironmentGateError(error)
    return value

@dataclass(frozen=True)
class TargetEnvironmentEvidence:
    target_id: str
    environment_class: str
    artifact_sha256: str
    rollback_artifact_sha256: str
    evidence_refs: dict[str, str]
    network_enabled: bool = False
    external_effect_enabled: bool = False
    spend_enabled: bool = False
    protected_keirin_data_enabled: bool = False
    production_credentials_enabled: bool = False
    runtime_activation: bool = False

    def validate(self) -> None:
        _exact_str(self.target_id, "TARGET_ID_REQUIRED")
        if type(self.environment_class) is not str or self.environment_class not in ALLOWED_ENVIRONMENT_CLASSES:
            raise TargetEnvironmentGateError("TARGET_CLASS_NOT_ALLOWED")
        _sha256(self.artifact_sha256, "ARTIFACT_DIGEST_INVALID")
        _sha256(self.rollback_artifact_sha256, "ROLLBACK_DIGEST_INVALID")
        if type(self.evidence_refs) is not dict or set(self.evidence_refs) != REQUIRED_EVIDENCE_DOMAINS:
            raise TargetEnvironmentGateError("EVIDENCE_DOMAIN_SET_INVALID")
        for domain, ref in self.evidence_refs.items():
            if type(domain) is not str:
                raise TargetEnvironmentGateError("EVIDENCE_DOMAIN_TYPE_INVALID")
            _evidence_ref(ref, f"{domain.upper()}_EVIDENCE_REF_REQUIRED")
        denied = (
            self.network_enabled,
            self.external_effect_enabled,
            self.spend_enabled,
            self.protected_keirin_data_enabled,
            self.production_credentials_enabled,
            self.runtime_activation,
        )
        if any(type(v) is not bool or v is not False for v in denied):
            raise TargetEnvironmentGateError("DEFAULT_DENY_AUTHORITY_REQUIRED")

    def receipt(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": "MULTIVERSE_TARGET_ENVIRONMENT_EVIDENCE_v1",
            "canonical_main": CANONICAL_MAIN,
            "adopted_runtime_head": ADOPTED_RUNTIME_HEAD,
            "adopted_deployment_head": ADOPTED_DEPLOYMENT_HEAD,
            "mode": MODE,
            "runtime": RUNTIME,
            "ready_for_activation": False,
            "evidence": asdict(self),
            "proof_ceiling": "Evidence-reference package only; ref shape is mechanically validated but referenced real-world execution must be independently verified. No Runtime activation, production effect, spend, protected-data, merge, main/ruleset mutation, or production credential authority.",
        }

def canonical_receipt_sha256(receipt: dict[str, Any]) -> str:
    if type(receipt) is not dict:
        raise TargetEnvironmentGateError("RECEIPT_TYPE_INVALID")
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
