from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.launch_evidence import (
    provider_launch_evidence_sha256,
    validate_provider_launch_evidence,
)
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.pilot_roundtrip import (
    provider_pilot_roundtrip_sha256,
    validate_provider_pilot_roundtrip,
)
from automation.multimodel_research_v1.provider_catalog import (
    estimate_smoke_cost_usd_micros,
)

REHEARSAL_SCHEMA = "MULTIVERSE_PROVIDER_REHEARSAL_CONVERGENCE_v1"

REHEARSAL_KEYS = {
    "schema",
    "rehearsal_id",
    "provider",
    "model_id",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "pilot_matrix_sha256",
    "launch_evidence_sha256",
    "pilot_roundtrip_sha256",
    "observation_binding_sha256",
    "checked_at",
    "input_tokens",
    "output_tokens",
    "simulated_usage_cost_usd_micros",
    "estimated_max_cost_usd_micros",
    "within_preflight_cost_ceiling",
    "rehearsal_state",
    "synthetic_only",
    "repository_evidence_aligned",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_provider_execution",
    "adoption_authority",
    "runtime",
}


def _validated_context(
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
    launch_evidence: dict[str, Any],
    roundtrip: dict[str, Any],
) -> dict[str, Any]:
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
        launch_evidence,
    )
    provider = launch_evidence["provider"]
    validate_provider_pilot_roundtrip(
        task,
        catalog_snapshot,
        provider,
        response_schema,
        roundtrip,
    )

    require(
        roundtrip["provider"] == provider,
        "REHEARSAL_PROVIDER_MISMATCH",
    )
    require(
        roundtrip["model_id"] == launch_evidence["model_id"],
        "REHEARSAL_MODEL_MISMATCH",
    )
    require(
        roundtrip["pilot_matrix_sha256"]
        == launch_evidence["pilot_matrix_sha256"],
        "REHEARSAL_MATRIX_SHA256_MISMATCH",
    )
    require(
        roundtrip["synthetic_only"] is True,
        "REHEARSAL_SYNTHETIC_ONLY_REQUIRED",
    )
    require(
        roundtrip["live_provider_execution"] is False,
        "REHEARSAL_LIVE_EXECUTION_FORBIDDEN",
    )
    require(
        launch_evidence["repository_evidence_aligned"] is True,
        "REHEARSAL_LAUNCH_EVIDENCE_NOT_ALIGNED",
    )
    require(
        roundtrip["input_tokens"] <= launch_evidence["max_input_tokens"],
        "REHEARSAL_INPUT_TOKENS_EXCEED_PREFLIGHT",
    )
    require(
        roundtrip["output_tokens"] <= launch_evidence["max_output_tokens"],
        "REHEARSAL_OUTPUT_TOKENS_EXCEED_PREFLIGHT",
    )
    simulated_cost = estimate_smoke_cost_usd_micros(
        catalog_snapshot,
        provider,
        roundtrip["input_tokens"],
        roundtrip["output_tokens"],
    )
    require(
        simulated_cost
        <= launch_evidence["estimated_max_cost_usd_micros"],
        "REHEARSAL_SIMULATED_COST_EXCEEDS_PREFLIGHT",
    )

    return {
        "provider": provider,
        "model_id": launch_evidence["model_id"],
        "prelive_candidate_head":
            launch_evidence["prelive_candidate_head"],
        "prelive_candidate_seal_blob":
            launch_evidence["prelive_candidate_seal_blob"],
        "pilot_matrix_sha256":
            launch_evidence["pilot_matrix_sha256"],
        "launch_evidence_sha256":
            provider_launch_evidence_sha256(
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
                launch_evidence,
            ),
        "pilot_roundtrip_sha256":
            provider_pilot_roundtrip_sha256(
                task,
                catalog_snapshot,
                provider,
                response_schema,
                roundtrip,
            ),
        "observation_binding_sha256":
            roundtrip["observation_binding_sha256"],
        "checked_at": launch_evidence["checked_at"],
        "input_tokens": roundtrip["input_tokens"],
        "output_tokens": roundtrip["output_tokens"],
        "simulated_usage_cost_usd_micros": simulated_cost,
        "estimated_max_cost_usd_micros":
            launch_evidence["estimated_max_cost_usd_micros"],
        "within_preflight_cost_ceiling": True,
    }


def build_provider_rehearsal_convergence(
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
    launch_evidence: dict[str, Any],
    roundtrip: dict[str, Any],
) -> dict[str, Any]:
    context = _validated_context(
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
        launch_evidence,
        roundtrip,
    )
    record = {
        "schema": REHEARSAL_SCHEMA,
        "rehearsal_id":
            f"provider-rehearsal-{context['provider'].lower()}-001",
        **context,
        "rehearsal_state":
            "FULL_OFFLINE_REHEARSAL_ALIGNED_AUTHORITY_ABSENT",
        "synthetic_only": True,
        "repository_evidence_aligned": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }
    return validate_provider_rehearsal_convergence(
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
        launch_evidence,
        roundtrip,
        record,
    )


def validate_provider_rehearsal_convergence(
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
    launch_evidence: dict[str, Any],
    roundtrip: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    context = _validated_context(
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
        launch_evidence,
        roundtrip,
    )
    require(
        isinstance(record, dict)
        and set(record) == REHEARSAL_KEYS,
        "REHEARSAL_SCHEMA_KEYS",
    )
    require(
        record["schema"] == REHEARSAL_SCHEMA,
        "REHEARSAL_SCHEMA_VERSION",
    )
    for key, expected in context.items():
        require(
            record[key] == expected,
            f"REHEARSAL_FIELD_MISMATCH:{key}",
        )
    require(
        record["rehearsal_state"]
        == "FULL_OFFLINE_REHEARSAL_ALIGNED_AUTHORITY_ABSENT",
        "REHEARSAL_STATE",
    )
    require(
        record["synthetic_only"] is True,
        "REHEARSAL_SYNTHETIC_ONLY_REQUIRED",
    )
    require(
        record["repository_evidence_aligned"] is True,
        "REHEARSAL_NOT_ALIGNED",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_provider_execution",
        "adoption_authority",
    ):
        require(
            record[key] is False,
            f"REHEARSAL_FORBIDDEN_TRUE:{key}",
        )
    require(
        record["runtime"] == "OFF",
        "REHEARSAL_RUNTIME_NOT_OFF",
    )
    return record


def provider_rehearsal_convergence_sha256(
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
    launch_evidence: dict[str, Any],
    roundtrip: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_provider_rehearsal_convergence(
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
        launch_evidence,
        roundtrip,
        record,
    )
    return sha256_json(record)
