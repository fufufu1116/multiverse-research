from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_result_v2_for_assignment,
)
from automation.multimodel_research_v1.claude_adapter import (
    parse_claude_messages_response,
)
from automation.multimodel_research_v1.gemini_adapter import (
    parse_gemini_interactions_v1_response,
)
from automation.multimodel_research_v1.model import (
    canonical_json,
    require,
    sha256_json,
)
from automation.multimodel_research_v1.observation_binding import (
    provider_observation_binding_sha256,
    validate_provider_observation_binding,
)
from automation.multimodel_research_v1.pilot_matrix import (
    build_provider_pilot_matrix,
    provider_pilot_matrix_sha256,
)
from automation.multimodel_research_v1.provider_result_ingestion import (
    build_provider_result_ingestion,
    provider_result_ingestion_sha256,
)
from automation.multimodel_research_v1.provider_result_schema import (
    build_result_v2_response_schema,
    result_v2_response_schema_sha256,
)
from automation.multimodel_research_v1.receipt import (
    execution_receipt_sha256,
    validate_execution_receipt,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
)
from automation.multimodel_research_v1.termination import (
    termination_record_sha256,
    validate_termination_record,
)

PILOT_ROUNDTRIP_V2_SCHEMA = "MULTIVERSE_PROVIDER_PILOT_ROUNDTRIP_v2"

PILOT_ROUNDTRIP_V2_KEYS = {
    "schema",
    "roundtrip_id",
    "provider",
    "assignment_provider",
    "model_id",
    "response_schema_sha256",
    "pilot_matrix_sha256",
    "simulated_provider_response_sha256",
    "provider_observation_sha256",
    "provider_result_ingestion_sha256",
    "termination_record_sha256",
    "result_sha256",
    "execution_receipt_sha256",
    "observation_binding_sha256",
    "provider_response_id",
    "normalized_state",
    "input_tokens",
    "output_tokens",
    "attestation_state",
    "result_from_provider_output",
    "synthetic_only",
    "live_provider_execution",
    "provider_credentials",
    "spend_authorized",
    "runtime",
    "adoption_authority",
}

_BOOTSTRAP_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string"},
    },
    "required": ["status"],
}


def _plus_seconds(value: str, seconds: int) -> str:
    require(
        isinstance(value, str) and value.endswith("Z"),
        "PILOT_ROUNDTRIP_V2_TIME",
    )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError("PILOT_ROUNDTRIP_V2_TIME") from exc
    require(
        parsed.tzinfo == timezone.utc,
        "PILOT_ROUNDTRIP_V2_TIME",
    )
    return (
        parsed + timedelta(seconds=seconds)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _synthetic_evidence(task: dict[str, Any]) -> dict[str, Any]:
    manifest = task.get("evidence_manifest")
    require(
        isinstance(manifest, list) and bool(manifest),
        "PILOT_ROUNDTRIP_V2_EVIDENCE_MANIFEST",
    )
    for item in manifest:
        if (
            isinstance(item, dict)
            and isinstance(item.get("primitive"), str)
            and isinstance(item.get("ref"), str)
            and isinstance(item.get("sha256"), str)
        ):
            return {
                "primitive": item["primitive"],
                "ref": item["ref"],
                "sha256": item["sha256"],
            }
    raise RuntimeError(
        "PILOT_ROUNDTRIP_V2_SYNTHETIC_EVIDENCE_REQUIRED"
    )


def _synthetic_result(
    task: dict[str, Any],
    assignment: dict[str, Any],
    produced_at: str,
) -> dict[str, Any]:
    result = {
        "schema": "MULTIVERSE_RESEARCH_RESULT_v2",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "submission_id":
            f"pilot-roundtrip-v2-{assignment['target_provider']}-result-001",
        "snapshot_id": task["snapshot_id"],
        "produced_at": produced_at,
        "model_identity": {
            "provider": assignment["target_provider"],
            "model": assignment["target_model"],
            "role": assignment["requested_role"],
        },
        "status": "COMPLETED",
        "findings": [
            {
                "finding_id": "pilot-roundtrip-v2-finding-001",
                "claim_key": "provider-output-result-v2-chain",
                "position": "UNKNOWN",
                "severity": "INFO",
                "assertion":
                    "Provider output bytes decoded to the exact bound RESULT v2.",
                "evidence": _synthetic_evidence(task),
                "confidence": 0.5,
                "uncertainty":
                    "Synthetic provider response only; not live-provider proof.",
                "recommendation":
                    "Require separate provider authority before any live call.",
                "validation_plan":
                    "Run a separately authorized provider smoke only after gates.",
            }
        ],
        "uncertainty_factors": [
            "Synthetic provider response; no external provider was called."
        ],
        "nonauthority": dict(task["nonauthority"]),
        "assignment_sha256": assignment_sha256(
            task,
            assignment,
        ),
    }
    validate_result_v2_for_assignment(
        task,
        assignment,
        result,
    )
    return result


def _simulated_response(
    provider: str,
    model_id: str,
    output_text: str,
) -> dict[str, Any]:
    if provider == "GOOGLE_GEMINI":
        return {
            "id": "gemini-sim-roundtrip-v2-001",
            "model": model_id,
            "status": "completed",
            "usage": {
                "total_input_tokens": 10,
                "total_output_tokens": 20,
            },
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": output_text,
                        }
                    ],
                }
            ],
        }
    if provider == "ANTHROPIC_CLAUDE":
        return {
            "id": "claude-sim-roundtrip-v2-001",
            "type": "message",
            "role": "assistant",
            "model": model_id,
            "content": [
                {
                    "type": "text",
                    "text": output_text,
                }
            ],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "stop_details": None,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
            },
        }
    raise RuntimeError("PILOT_ROUNDTRIP_V2_PROVIDER")


def _parse_response(
    provider: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    if provider == "GOOGLE_GEMINI":
        return parse_gemini_interactions_v1_response(response)
    if provider == "ANTHROPIC_CLAUDE":
        return parse_claude_messages_response(response)
    raise RuntimeError("PILOT_ROUNDTRIP_V2_PROVIDER")


def _build_artifacts(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    bootstrap_matrix = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        provider,
        _BOOTSTRAP_RESPONSE_SCHEMA,
    )
    bootstrap_assignment = bootstrap_matrix["assignment"]
    response_schema = build_result_v2_response_schema(
        task,
        bootstrap_assignment,
    )
    matrix = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        provider,
        response_schema,
    )
    assignment = matrix["assignment"]
    require(
        assignment == bootstrap_assignment,
        "PILOT_ROUNDTRIP_V2_SCHEMA_CHANGED_ASSIGNMENT",
    )

    envelope = matrix["request_envelope"]
    result = _synthetic_result(
        task,
        assignment,
        _plus_seconds(envelope["created_at"], 6),
    )
    output_text = canonical_json(result)
    require(
        len(output_text.encode("utf-8"))
        <= assignment["max_output_bytes"],
        "PILOT_ROUNDTRIP_V2_OUTPUT_LIMIT",
    )

    response = _simulated_response(
        provider,
        assignment["target_model"],
        output_text,
    )
    observation = _parse_response(provider, response)
    require(
        observation["normalized_state"] == "COMPLETED",
        "PILOT_ROUNDTRIP_V2_NOT_COMPLETED",
    )

    response_received_at = _plus_seconds(
        envelope["created_at"],
        5,
    )
    native_reason = (
        observation["native_status"]
        if provider == "GOOGLE_GEMINI"
        else observation["native_stop_reason"]
    )
    termination = {
        "schema": "MULTIVERSE_PROVIDER_TERMINATION_RECORD_v1",
        "assignment_sha256": assignment_sha256(
            task,
            assignment,
        ),
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                matrix["model_target_policy"],
                matrix["capability_policy"],
                matrix["prompt"],
                envelope,
            ),
        "provider_response_id":
            observation["provider_response_id"],
        "native_reason": native_reason,
        "normalized_state": observation["normalized_state"],
        "input_tokens": observation["input_tokens"],
        "output_tokens": observation["output_tokens"],
        "usage_metadata_sha256":
            observation["usage_metadata_sha256"],
        "response_received_at": response_received_at,
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_termination_record(
        task,
        assignment,
        matrix["model_target_policy"],
        matrix["capability_policy"],
        matrix["prompt"],
        envelope,
        termination,
    )

    ingestion = build_provider_result_ingestion(
        task,
        assignment,
        assignment["target_provider"],
        observation,
    )
    require(
        ingestion["result"] == result,
        "PILOT_ROUNDTRIP_V2_RESULT_NOT_FROM_PROVIDER_OUTPUT",
    )

    receipt = {
        "schema": "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1",
        "receipt_id":
            f"pilot-roundtrip-v2-{provider.lower()}-receipt-001",
        "task_sha256": sha256_json(task),
        "assignment_sha256": assignment_sha256(
            task,
            assignment,
        ),
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                matrix["model_target_policy"],
                matrix["capability_policy"],
                matrix["prompt"],
                envelope,
            ),
        "termination_record_sha256":
            termination_record_sha256(
                task,
                assignment,
                matrix["model_target_policy"],
                matrix["capability_policy"],
                matrix["prompt"],
                envelope,
                termination,
            ),
        "submission_id": result["submission_id"],
        "observed_provider": assignment["target_provider"],
        "observed_model_id": observation["observed_model_id"],
        "provider_response_id":
            observation["provider_response_id"],
        "provider_response_sha256":
            observation["provider_response_sha256"],
        "result_sha256": sha256_json(result),
        "adapter_sha256": assignment["adapter_sha256"],
        "request_started_at":
            _plus_seconds(envelope["created_at"], 1),
        "response_received_at": response_received_at,
        "receipt_created_at":
            _plus_seconds(envelope["created_at"], 7),
        "attestation_state": "LIVE_ATTESTED",
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_execution_receipt(
        task,
        assignment,
        matrix["model_target_policy"],
        matrix["capability_policy"],
        matrix["prompt"],
        envelope,
        termination,
        result,
        receipt,
    )

    binding = validate_provider_observation_binding(
        provider=provider,
        observation=observation,
        task=task,
        assignment=assignment,
        model_target_policy=matrix["model_target_policy"],
        capability_policy=matrix["capability_policy"],
        prompt=matrix["prompt"],
        request_envelope=envelope,
        termination_record=termination,
        result=result,
        receipt=receipt,
    )

    return {
        "response_schema": response_schema,
        "matrix": matrix,
        "response": response,
        "observation": observation,
        "termination": termination,
        "ingestion": ingestion,
        "result": result,
        "receipt": receipt,
        "binding": binding,
    }


def build_provider_pilot_roundtrip_v2_unchecked(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    artifacts = _build_artifacts(
        task,
        catalog_snapshot,
        provider,
    )
    schema = artifacts["response_schema"]
    matrix = artifacts["matrix"]
    assignment = matrix["assignment"]
    observation = artifacts["observation"]
    termination = artifacts["termination"]
    ingestion = artifacts["ingestion"]
    result = artifacts["result"]
    receipt = artifacts["receipt"]

    return {
        "schema": PILOT_ROUNDTRIP_V2_SCHEMA,
        "roundtrip_id":
            f"pilot-roundtrip-v2-{provider.lower()}-001",
        "provider": provider,
        "assignment_provider": assignment["target_provider"],
        "model_id": assignment["target_model"],
        "response_schema_sha256":
            result_v2_response_schema_sha256(
                task,
                assignment,
                schema,
            ),
        "pilot_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                schema,
                matrix,
            ),
        "simulated_provider_response_sha256":
            sha256_json(artifacts["response"]),
        "provider_observation_sha256":
            sha256_json(observation),
        "provider_result_ingestion_sha256":
            provider_result_ingestion_sha256(
                task,
                assignment,
                assignment["target_provider"],
                observation,
                ingestion,
            ),
        "termination_record_sha256":
            termination_record_sha256(
                task,
                assignment,
                matrix["model_target_policy"],
                matrix["capability_policy"],
                matrix["prompt"],
                matrix["request_envelope"],
                termination,
            ),
        "result_sha256": sha256_json(result),
        "execution_receipt_sha256":
            execution_receipt_sha256(
                task,
                assignment,
                matrix["model_target_policy"],
                matrix["capability_policy"],
                matrix["prompt"],
                matrix["request_envelope"],
                termination,
                result,
                receipt,
            ),
        "observation_binding_sha256":
            provider_observation_binding_sha256(
                provider=provider,
                observation=observation,
                task=task,
                assignment=assignment,
                model_target_policy=matrix["model_target_policy"],
                capability_policy=matrix["capability_policy"],
                prompt=matrix["prompt"],
                request_envelope=matrix["request_envelope"],
                termination_record=termination,
                result=result,
                receipt=receipt,
            ),
        "provider_response_id":
            observation["provider_response_id"],
        "normalized_state": observation["normalized_state"],
        "input_tokens": observation["input_tokens"],
        "output_tokens": observation["output_tokens"],
        "attestation_state": receipt["attestation_state"],
        "result_from_provider_output": True,
        "synthetic_only": True,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }


def build_provider_pilot_roundtrip_v2(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    value = build_provider_pilot_roundtrip_v2_unchecked(
        task,
        catalog_snapshot,
        provider,
    )
    return validate_provider_pilot_roundtrip_v2(
        task,
        catalog_snapshot,
        provider,
        value,
    )


def validate_provider_pilot_roundtrip_v2(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    roundtrip: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(roundtrip, dict)
        and set(roundtrip) == PILOT_ROUNDTRIP_V2_KEYS,
        "PILOT_ROUNDTRIP_V2_SCHEMA_KEYS",
    )
    require(
        roundtrip["schema"] == PILOT_ROUNDTRIP_V2_SCHEMA,
        "PILOT_ROUNDTRIP_V2_SCHEMA_VERSION",
    )
    expected = build_provider_pilot_roundtrip_v2_unchecked(
        task,
        catalog_snapshot,
        provider,
    )
    require(
        roundtrip == expected,
        "PILOT_ROUNDTRIP_V2_EXACT_MISMATCH",
    )
    return roundtrip


def provider_pilot_roundtrip_v2_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    roundtrip: dict[str, Any],
) -> str:
    validate_provider_pilot_roundtrip_v2(
        task,
        catalog_snapshot,
        provider,
        roundtrip,
    )
    return sha256_json(roundtrip)
