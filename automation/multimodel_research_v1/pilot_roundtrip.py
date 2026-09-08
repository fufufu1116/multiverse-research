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
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.observation_binding import (
    provider_observation_binding_sha256,
    validate_provider_observation_binding,
)
from automation.multimodel_research_v1.pilot_matrix import (
    build_provider_pilot_matrix,
    provider_pilot_matrix_sha256,
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

PILOT_ROUNDTRIP_SCHEMA = "MULTIVERSE_PROVIDER_PILOT_ROUNDTRIP_v1"

PILOT_ROUNDTRIP_KEYS = {
    "schema",
    "roundtrip_id",
    "provider",
    "model_id",
    "pilot_matrix_sha256",
    "simulated_provider_response_sha256",
    "provider_observation_sha256",
    "termination_record_sha256",
    "result_sha256",
    "execution_receipt_sha256",
    "observation_binding_sha256",
    "provider_response_id",
    "normalized_state",
    "attestation_state",
    "synthetic_only",
    "live_provider_execution",
    "provider_credentials",
    "spend_authorized",
    "runtime",
    "adoption_authority",
}


def _plus_seconds(value: str, seconds: int) -> str:
    require(
        isinstance(value, str) and value.endswith("Z"),
        "PILOT_ROUNDTRIP_TIME",
    )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError("PILOT_ROUNDTRIP_TIME") from exc
    require(parsed.tzinfo == timezone.utc, "PILOT_ROUNDTRIP_TIME")
    return (
        parsed + timedelta(seconds=seconds)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _synthetic_evidence(task: dict[str, Any]) -> dict[str, Any]:
    manifest = task.get("evidence_manifest")
    require(
        isinstance(manifest, list) and bool(manifest),
        "PILOT_ROUNDTRIP_EVIDENCE_MANIFEST",
    )
    for item in manifest:
        if (
            isinstance(item, dict)
            and item.get("primitive") == "NORMALIZED_JSON_SHA256"
            and isinstance(item.get("ref"), str)
            and isinstance(item.get("sha256"), str)
        ):
            return {
                "primitive": item["primitive"],
                "ref": item["ref"],
                "sha256": item["sha256"],
            }
    raise RuntimeError("PILOT_ROUNDTRIP_SYNTHETIC_EVIDENCE_REQUIRED")


def _simulated_response(
    provider: str,
    model_id: str,
) -> dict[str, Any]:
    text = '{"status":"ok","mode":"synthetic_roundtrip"}'
    if provider == "GOOGLE_GEMINI":
        return {
            "id": "gemini-sim-roundtrip-001",
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
                            "text": text,
                        }
                    ],
                }
            ],
        }
    if provider == "ANTHROPIC_CLAUDE":
        return {
            "id": "claude-sim-roundtrip-001",
            "type": "message",
            "role": "assistant",
            "model": model_id,
            "content": [
                {
                    "type": "text",
                    "text": text,
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
    raise RuntimeError("PILOT_ROUNDTRIP_PROVIDER")


def _parse_response(
    provider: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    if provider == "GOOGLE_GEMINI":
        return parse_gemini_interactions_v1_response(response)
    if provider == "ANTHROPIC_CLAUDE":
        return parse_claude_messages_response(response)
    raise RuntimeError("PILOT_ROUNDTRIP_PROVIDER")


def _build_artifacts(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    matrix = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        provider,
        response_schema,
    )
    assignment = matrix["assignment"]
    target_policy = matrix["model_target_policy"]
    capability_policy = matrix["capability_policy"]
    prompt = matrix["prompt"]
    envelope = matrix["request_envelope"]

    response = _simulated_response(
        provider,
        assignment["target_model"],
    )
    observation = _parse_response(provider, response)
    require(
        observation["observed_model_id"] == assignment["target_model"],
        "PILOT_ROUNDTRIP_MODEL_MISMATCH",
    )
    require(
        observation["normalized_state"] == "COMPLETED",
        "PILOT_ROUNDTRIP_NOT_COMPLETED",
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
        "assignment_sha256": assignment_sha256(task, assignment),
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
                prompt,
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
        target_policy,
        capability_policy,
        prompt,
        envelope,
        termination,
    )

    result = {
        "schema": "MULTIVERSE_RESEARCH_RESULT_v2",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "submission_id": f"pilot-roundtrip-{provider.lower()}-result-001",
        "snapshot_id": task["snapshot_id"],
        "produced_at": _plus_seconds(envelope["created_at"], 6),
        "model_identity": {
            "provider": assignment["target_provider"],
            "model": assignment["target_model"],
            "role": assignment["requested_role"],
        },
        "status": "COMPLETED",
        "findings": [
            {
                "finding_id": "pilot-roundtrip-finding-001",
                "claim_key": "pilot-roundtrip-synthetic-chain",
                "position": "UNKNOWN",
                "severity": "INFO",
                "assertion":
                    "Synthetic provider round-trip was parsed and bound.",
                "evidence": _synthetic_evidence(task),
                "confidence": 0.5,
                "uncertainty":
                    "Synthetic response only; not live-provider proof.",
                "recommendation":
                    "Require separate provider authority before any live call.",
                "validation_plan":
                    "Run one separately authorized synthetic provider smoke.",
            }
        ],
        "uncertainty_factors": [
            "Synthetic provider response; no external provider was called."
        ],
        "nonauthority": dict(task["nonauthority"]),
        "assignment_sha256": assignment_sha256(task, assignment),
    }
    validate_result_v2_for_assignment(task, assignment, result)

    receipt = {
        "schema": "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1",
        "receipt_id": f"pilot-roundtrip-{provider.lower()}-receipt-001",
        "task_sha256": sha256_json(task),
        "assignment_sha256": assignment_sha256(task, assignment),
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
                prompt,
                envelope,
            ),
        "termination_record_sha256":
            termination_record_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
                prompt,
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
        target_policy,
        capability_policy,
        prompt,
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
        model_target_policy=target_policy,
        capability_policy=capability_policy,
        prompt=prompt,
        request_envelope=envelope,
        termination_record=termination,
        result=result,
        receipt=receipt,
    )

    return {
        "matrix": matrix,
        "response": response,
        "observation": observation,
        "termination": termination,
        "result": result,
        "receipt": receipt,
        "binding": binding,
    }


def build_provider_pilot_roundtrip(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    artifacts = _build_artifacts(
        task,
        catalog_snapshot,
        provider,
        response_schema,
    )
    matrix = artifacts["matrix"]
    observation = artifacts["observation"]
    termination = artifacts["termination"]
    result = artifacts["result"]
    receipt = artifacts["receipt"]
    binding = artifacts["binding"]

    roundtrip = {
        "schema": PILOT_ROUNDTRIP_SCHEMA,
        "roundtrip_id": f"pilot-roundtrip-{provider.lower()}-001",
        "provider": provider,
        "model_id": matrix["assignment"]["target_model"],
        "pilot_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                matrix,
            ),
        "simulated_provider_response_sha256":
            sha256_json(artifacts["response"]),
        "provider_observation_sha256":
            sha256_json(observation),
        "termination_record_sha256":
            termination_record_sha256(
                task,
                matrix["assignment"],
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
                matrix["assignment"],
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
                assignment=matrix["assignment"],
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
        "attestation_state": receipt["attestation_state"],
        "synthetic_only": True,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }
    return validate_provider_pilot_roundtrip(
        task,
        catalog_snapshot,
        provider,
        response_schema,
        roundtrip,
    )


def validate_provider_pilot_roundtrip(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
    roundtrip: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(roundtrip, dict)
        and set(roundtrip) == PILOT_ROUNDTRIP_KEYS,
        "PILOT_ROUNDTRIP_SCHEMA_KEYS",
    )
    require(
        roundtrip["schema"] == PILOT_ROUNDTRIP_SCHEMA,
        "PILOT_ROUNDTRIP_SCHEMA_VERSION",
    )
    expected = build_provider_pilot_roundtrip_unchecked(
        task,
        catalog_snapshot,
        provider,
        response_schema,
    )
    require(
        roundtrip == expected,
        "PILOT_ROUNDTRIP_EXACT_MISMATCH",
    )
    return roundtrip


def build_provider_pilot_roundtrip_unchecked(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    artifacts = _build_artifacts(
        task,
        catalog_snapshot,
        provider,
        response_schema,
    )
    matrix = artifacts["matrix"]
    observation = artifacts["observation"]
    termination = artifacts["termination"]
    result = artifacts["result"]
    receipt = artifacts["receipt"]
    return {
        "schema": PILOT_ROUNDTRIP_SCHEMA,
        "roundtrip_id": f"pilot-roundtrip-{provider.lower()}-001",
        "provider": provider,
        "model_id": matrix["assignment"]["target_model"],
        "pilot_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                matrix,
            ),
        "simulated_provider_response_sha256":
            sha256_json(artifacts["response"]),
        "provider_observation_sha256":
            sha256_json(observation),
        "termination_record_sha256":
            termination_record_sha256(
                task,
                matrix["assignment"],
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
                matrix["assignment"],
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
                assignment=matrix["assignment"],
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
        "attestation_state": receipt["attestation_state"],
        "synthetic_only": True,
        "live_provider_execution": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }


def provider_pilot_roundtrip_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
    roundtrip: dict[str, Any],
) -> str:
    validate_provider_pilot_roundtrip(
        task,
        catalog_snapshot,
        provider,
        response_schema,
        roundtrip,
    )
    return sha256_json(roundtrip)
