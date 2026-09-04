from real_infrastructure_contract import (
    ENVIRONMENT_CLASS,
    HOST_BOUNDARY,
    PROVIDER_BINDING,
    REQUIRED_EVIDENCE_DOMAINS,
    SERVICE_BOUNDARY,
    TARGET_CLASS,
    RealInfrastructurePreparationSpec,
)


def build_preparation_plan():
    evidence_refs = {
        domain: f"SYNTHETIC_REF:evidence/{domain}:planned-v1"
        for domain in sorted(REQUIRED_EVIDENCE_DOMAINS)
    }

    credential_refs = {
        "provisioning":
            "SYNTHETIC_REF:credential/provisioning:planned-v1",
        "rotation":
            "SYNTHETIC_REF:credential/rotation:planned-v1",
        "revocation":
            "SYNTHETIC_REF:credential/revocation:planned-v1",
    }

    spec = RealInfrastructurePreparationSpec(
        target_class=TARGET_CLASS,
        environment_class=ENVIRONMENT_CLASS,
        provider_binding=PROVIDER_BINDING,
        host_boundary=HOST_BOUNDARY,
        service_boundary=SERVICE_BOUNDARY,
        evidence_refs=evidence_refs,
        credential_refs=credential_refs,
    )

    receipt = spec.receipt()

    return {
        "target_class":
            TARGET_CLASS,
        "environment_class":
            ENVIRONMENT_CLASS,
        "provider_binding":
            PROVIDER_BINDING,
        "host_boundary":
            HOST_BOUNDARY,
        "service_boundary":
            SERVICE_BOUNDARY,
        "evidence_refs":
            evidence_refs,
        "credential_refs":
            credential_refs,
        "requirements": {
            "target_identity": {
                "must_bind_exact_remote_target_identifier": True,
                "must_not_claim_provisioning_before_evidence": True,
            },
            "credential_lifecycle": {
                "least_privilege_scope_required": True,
                "provisioning_evidence_required": True,
                "rotation_evidence_required": True,
                "revocation_evidence_required": True,
                "real_secret_material_allowed_in_repo": False,
            },
            "state_store": {
                "remote_binding_evidence_required": True,
                "backup_execution_evidence_required": True,
                "restore_execution_evidence_required": True,
            },
            "lease_fencing": {
                "single_host_boundary_explicit": True,
                "multi_host_failover_proven": False,
                "future_fencing_evidence_required": True,
            },
            "observability": {
                "health_readiness_evidence_required": True,
                "logs_metrics_evidence_required": True,
                "alert_delivery_evidence_required": True,
                "production_on_call_proven": False,
            },
            "rollback": {
                "rollback_trigger_required": True,
                "rollback_execution_evidence_required": True,
                "production_rollback_proven": False,
            },
            "provider_effect_safety": {
                "idempotency_evidence_required": True,
                "duplicate_request_negative_control_required": True,
                "live_provider_execution_authorized": False,
                "real_network_execution_authorized": False,
                "external_effect_authorized": False,
            },
        },
        "authority": receipt["authority"],
        "existence_claims": receipt["existence_claims"],
        "runtime": receipt["runtime"],
        "ready_for_external_execution":
            receipt["ready_for_external_execution"],
        "proof_ceiling":
            receipt["proof_ceiling"],
        "receipt":
            receipt,
    }
