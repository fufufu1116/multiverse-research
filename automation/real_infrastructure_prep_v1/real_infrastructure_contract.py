from dataclasses import dataclass
import hashlib
import json
import re


CANONICAL_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
ADOPTED_TARGET_ENVIRONMENT_HEAD = "b587206560bfb623c74f9bdc95007f2c7cbce022"
ADOPTED_TARGET_ENVIRONMENT_CLOSURE = 5540044126
ADOPTION_DECISION_COMMENT = 5540202938
PREPARATION_AUTHORITY_COMMENT = 5540239175

TARGET_CLASS = "REMOTE_PREPRODUCTION_SINGLE_HOST_NO_EFFECT_PLANNED_v1"
ENVIRONMENT_CLASS = "PRE_PRODUCTION"
PROVIDER_BINDING = "PROVIDER_NEUTRAL_UNPROVISIONED"
HOST_BOUNDARY = "ONE_REMOTE_PREPRODUCTION_HOST_PLANNED"
SERVICE_BOUNDARY = "MULTIVERSE_RUNTIME_SUPERVISOR_NO_EFFECT"

REQUIRED_EVIDENCE_DOMAINS = frozenset(
    {
        "target_identity",
        "credential_provisioning",
        "credential_rotation",
        "credential_revocation",
        "remote_state_store",
        "backup_restore",
        "lease_fencing",
        "health_readiness",
        "logs_metrics_alerts",
        "rollback",
        "provider_idempotency",
        "duplicate_request_control",
        "kill_switch",
    }
)

AUTHORITY_FIELDS = (
    "real_network_execution",
    "live_provider_execution",
    "external_effect_enabled",
    "spend_enabled",
    "protected_keirin_data_enabled",
    "production_credentials_enabled",
    "production_deployment_enabled",
    "runtime_activation",
)

EXISTENCE_CLAIM_FIELDS = (
    "remote_host_provisioned",
    "remote_service_deployed",
    "remote_state_store_provisioned",
    "real_credentials_provisioned",
    "network_path_verified",
)

_SYNTHETIC_REF_RE = re.compile(
    r"^SYNTHETIC_REF:[a-z0-9_./-]+:[A-Za-z0-9._/-]+$"
)


class RealInfrastructurePreparationGateError(ValueError):
    pass


def _require_exact_str(value, name):
    if type(value) is not str:
        raise RealInfrastructurePreparationGateError(
            f"{name} must be exact str"
        )
    if not value.strip():
        raise RealInfrastructurePreparationGateError(
            f"{name} must be non-empty"
        )


def _require_exact_false(value, name):
    if type(value) is not bool or value is not False:
        raise RealInfrastructurePreparationGateError(
            f"{name} must be exact False"
        )


def _validate_synthetic_ref(value, name):
    _require_exact_str(value, name)
    if not _SYNTHETIC_REF_RE.fullmatch(value):
        raise RealInfrastructurePreparationGateError(
            f"{name} must be a SYNTHETIC_REF"
        )


def canonical_receipt_sha256(receipt):
    if type(receipt) is not dict:
        raise RealInfrastructurePreparationGateError(
            "receipt must be exact dict"
        )
    encoded = json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RealInfrastructurePreparationSpec:
    target_class: str
    environment_class: str
    provider_binding: str
    host_boundary: str
    service_boundary: str
    evidence_refs: dict
    credential_refs: dict

    real_network_execution: bool = False
    live_provider_execution: bool = False
    external_effect_enabled: bool = False
    spend_enabled: bool = False
    protected_keirin_data_enabled: bool = False
    production_credentials_enabled: bool = False
    production_deployment_enabled: bool = False
    runtime_activation: bool = False

    remote_host_provisioned: bool = False
    remote_service_deployed: bool = False
    remote_state_store_provisioned: bool = False
    real_credentials_provisioned: bool = False
    network_path_verified: bool = False

    def validate(self):
        _require_exact_str(self.target_class, "target_class")
        _require_exact_str(self.environment_class, "environment_class")
        _require_exact_str(self.provider_binding, "provider_binding")
        _require_exact_str(self.host_boundary, "host_boundary")
        _require_exact_str(self.service_boundary, "service_boundary")

        if self.target_class != TARGET_CLASS:
            raise RealInfrastructurePreparationGateError(
                "target_class mismatch"
            )
        if self.environment_class != ENVIRONMENT_CLASS:
            raise RealInfrastructurePreparationGateError(
                "environment_class mismatch"
            )
        if self.provider_binding != PROVIDER_BINDING:
            raise RealInfrastructurePreparationGateError(
                "provider_binding mismatch"
            )
        if self.host_boundary != HOST_BOUNDARY:
            raise RealInfrastructurePreparationGateError(
                "host_boundary mismatch"
            )
        if self.service_boundary != SERVICE_BOUNDARY:
            raise RealInfrastructurePreparationGateError(
                "service_boundary mismatch"
            )

        if type(self.evidence_refs) is not dict:
            raise RealInfrastructurePreparationGateError(
                "evidence_refs must be exact dict"
            )
        if set(self.evidence_refs) != REQUIRED_EVIDENCE_DOMAINS:
            raise RealInfrastructurePreparationGateError(
                "evidence_refs domain set mismatch"
            )

        for key, value in self.evidence_refs.items():
            _require_exact_str(key, "evidence_refs key")
            _validate_synthetic_ref(
                value,
                f"evidence_refs[{key}]",
            )

        if type(self.credential_refs) is not dict:
            raise RealInfrastructurePreparationGateError(
                "credential_refs must be exact dict"
            )
        if set(self.credential_refs) != {
            "provisioning",
            "rotation",
            "revocation",
        }:
            raise RealInfrastructurePreparationGateError(
                "credential_refs key set mismatch"
            )
        for key, value in self.credential_refs.items():
            _require_exact_str(key, "credential_refs key")
            _validate_synthetic_ref(
                value,
                f"credential_refs[{key}]",
            )

        for field in AUTHORITY_FIELDS:
            _require_exact_false(
                getattr(self, field),
                field,
            )

        for field in EXISTENCE_CLAIM_FIELDS:
            _require_exact_false(
                getattr(self, field),
                field,
            )

        return self

    def receipt(self):
        self.validate()
        receipt = {
            "schema":
                "MULTIVERSE_REAL_INFRASTRUCTURE_PREPARATION_RECEIPT_v1",
            "canonical_main":
                CANONICAL_MAIN,
            "adopted_target_environment_head":
                ADOPTED_TARGET_ENVIRONMENT_HEAD,
            "adopted_target_environment_closure":
                ADOPTED_TARGET_ENVIRONMENT_CLOSURE,
            "adoption_decision_comment":
                ADOPTION_DECISION_COMMENT,
            "preparation_authority_comment":
                PREPARATION_AUTHORITY_COMMENT,
            "target_class":
                self.target_class,
            "environment_class":
                self.environment_class,
            "provider_binding":
                self.provider_binding,
            "host_boundary":
                self.host_boundary,
            "service_boundary":
                self.service_boundary,
            "evidence_refs":
                dict(self.evidence_refs),
            "credential_refs":
                dict(self.credential_refs),
            "authority":
                {
                    field: getattr(self, field)
                    for field in AUTHORITY_FIELDS
                },
            "existence_claims":
                {
                    field: getattr(self, field)
                    for field in EXISTENCE_CLAIM_FIELDS
                },
            "runtime":
                "OFF",
            "ready_for_external_execution":
                False,
            "proof_ceiling":
                (
                    "REMOTE_PREPRODUCTION_SPECIFICATION_ONLY. "
                    "No remote host/service/state-store is claimed provisioned; "
                    "no real credential or network path is claimed available; "
                    "no live provider/network/external effect/spend/protected "
                    "Keirin data/production deployment/Runtime activation "
                    "authority is granted."
                ),
        }
        receipt["receipt_sha256"] = canonical_receipt_sha256(receipt)
        return receipt
