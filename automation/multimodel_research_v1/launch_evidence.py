from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.assignment import assignment_sha256
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.pilot_matrix import (
    provider_pilot_matrix_sha256,
    validate_provider_pilot_matrix,
)
from automation.multimodel_research_v1.pre_execution_bundle import (
    provider_pre_execution_bundle_sha256,
    validate_provider_pre_execution_bundle,
)

LAUNCH_EVIDENCE_SCHEMA = "MULTIVERSE_PROVIDER_LAUNCH_EVIDENCE_v1"

LAUNCH_EVIDENCE_KEYS = {
    "schema",
    "evidence_id",
    "provider",
    "model_id",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "pilot_matrix_sha256",
    "pre_execution_bundle_sha256",
    "assignment_sha256",
    "request_envelope_sha256",
    "execution_prep_sha256",
    "readiness_report_sha256",
    "checked_at",
    "max_input_tokens",
    "max_output_tokens",
    "estimated_max_cost_usd_micros",
    "evidence_state",
    "repository_evidence_aligned",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
    "adoption_authority",
}


def _aligned_context(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    pilot_matrix: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    pre_execution_bundle: dict[str, Any],
) -> dict[str, Any]:
    validate_provider_pilot_matrix(
        task,
        catalog_snapshot,
        response_schema,
        pilot_matrix,
    )
    validate_provider_pre_execution_bundle(
        catalog_snapshot,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        pre_execution_bundle,
    )

    provider = pilot_matrix["provider"]
    require(
        provider == pilot_plan["provider"],
        "LAUNCH_EVIDENCE_PROVIDER_MISMATCH",
    )
    require(
        provider == pre_execution_bundle["provider"],
        "LAUNCH_EVIDENCE_PROVIDER_MISMATCH",
    )

    model_id = pilot_matrix["assignment"]["target_model"]
    require(
        model_id == pilot_plan["model_id"],
        "LAUNCH_EVIDENCE_MODEL_MISMATCH",
    )
    require(
        model_id == pre_execution_bundle["model_id"],
        "LAUNCH_EVIDENCE_MODEL_MISMATCH",
    )

    prep = pilot_matrix["execution_prep"]
    require(
        prep["max_input_tokens"] == pilot_plan["max_input_tokens"],
        "LAUNCH_EVIDENCE_INPUT_CEILING_MISMATCH",
    )
    require(
        prep["max_output_tokens"] == pilot_plan["max_output_tokens"],
        "LAUNCH_EVIDENCE_OUTPUT_CEILING_MISMATCH",
    )
    require(
        prep["proposed_max_cost_usd_micros"]
        == pilot_plan["estimated_max_cost_usd_micros"],
        "LAUNCH_EVIDENCE_COST_CEILING_MISMATCH",
    )
    require(
        prep["max_attempts"] == pilot_plan["max_attempts"] == 1,
        "LAUNCH_EVIDENCE_ATTEMPT_MISMATCH",
    )
    require(
        pilot_matrix["readiness_report"]["provider"] == provider,
        "LAUNCH_EVIDENCE_READINESS_PROVIDER_MISMATCH",
    )

    return {
        "provider": provider,
        "model_id": model_id,
        "prelive_candidate_head":
            pre_execution_bundle["prelive_candidate_head"],
        "prelive_candidate_seal_blob":
            pre_execution_bundle["prelive_candidate_seal_blob"],
        "pilot_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                pilot_matrix,
            ),
        "pre_execution_bundle_sha256":
            provider_pre_execution_bundle_sha256(
                catalog_snapshot,
                pilot_plan,
                freshness_receipt,
                pilot_freshness_binding,
                time_attestation,
                freshness_time_binding,
                pre_execution_bundle,
            ),
        "assignment_sha256":
            assignment_sha256(task, pilot_matrix["assignment"]),
        "request_envelope_sha256":
            sha256_json(pilot_matrix["request_envelope"]),
        "execution_prep_sha256":
            sha256_json(pilot_matrix["execution_prep"]),
        "readiness_report_sha256":
            sha256_json(pilot_matrix["readiness_report"]),
        "checked_at": pre_execution_bundle["checked_at"],
        "max_input_tokens": pilot_plan["max_input_tokens"],
        "max_output_tokens": pilot_plan["max_output_tokens"],
        "estimated_max_cost_usd_micros":
            pilot_plan["estimated_max_cost_usd_micros"],
    }


def build_provider_launch_evidence(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    pilot_matrix: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    pre_execution_bundle: dict[str, Any],
) -> dict[str, Any]:
    context = _aligned_context(
        task,
        catalog_snapshot,
        response_schema,
        pilot_matrix,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        pre_execution_bundle,
    )
    evidence = {
        "schema": LAUNCH_EVIDENCE_SCHEMA,
        "evidence_id": "first-provider-launch-evidence-001",
        **context,
        "evidence_state":
            "REPOSITORY_EVIDENCE_ALIGNED_AUTHORITY_ABSENT",
        "repository_evidence_aligned": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }
    return validate_provider_launch_evidence(
        task,
        catalog_snapshot,
        response_schema,
        pilot_matrix,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        pre_execution_bundle,
        evidence,
    )


def validate_provider_launch_evidence(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    pilot_matrix: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    pre_execution_bundle: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    context = _aligned_context(
        task,
        catalog_snapshot,
        response_schema,
        pilot_matrix,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        pre_execution_bundle,
    )
    require(
        isinstance(evidence, dict)
        and set(evidence) == LAUNCH_EVIDENCE_KEYS,
        "LAUNCH_EVIDENCE_SCHEMA_KEYS",
    )
    require(
        evidence["schema"] == LAUNCH_EVIDENCE_SCHEMA,
        "LAUNCH_EVIDENCE_SCHEMA_VERSION",
    )
    require(
        evidence["evidence_id"]
        == "first-provider-launch-evidence-001",
        "LAUNCH_EVIDENCE_ID",
    )
    for key, expected in context.items():
        require(
            evidence[key] == expected,
            f"LAUNCH_EVIDENCE_FIELD_MISMATCH:{key}",
        )
    require(
        evidence["evidence_state"]
        == "REPOSITORY_EVIDENCE_ALIGNED_AUTHORITY_ABSENT",
        "LAUNCH_EVIDENCE_STATE",
    )
    require(
        evidence["repository_evidence_aligned"] is True,
        "LAUNCH_EVIDENCE_NOT_ALIGNED",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "adoption_authority",
    ):
        require(
            evidence[key] is False,
            f"LAUNCH_EVIDENCE_FORBIDDEN_TRUE:{key}",
        )
    require(
        evidence["runtime"] == "OFF",
        "LAUNCH_EVIDENCE_RUNTIME_NOT_OFF",
    )
    return evidence


def provider_launch_evidence_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    pilot_matrix: dict[str, Any],
    pilot_plan: dict[str, Any],
    freshness_receipt: dict[str, Any],
    pilot_freshness_binding: dict[str, Any],
    time_attestation: dict[str, Any],
    freshness_time_binding: dict[str, Any],
    pre_execution_bundle: dict[str, Any],
    evidence: dict[str, Any],
) -> str:
    validate_provider_launch_evidence(
        task,
        catalog_snapshot,
        response_schema,
        pilot_matrix,
        pilot_plan,
        freshness_receipt,
        pilot_freshness_binding,
        time_attestation,
        freshness_time_binding,
        pre_execution_bundle,
        evidence,
    )
    return sha256_json(evidence)
