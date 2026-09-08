from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.receipt import (
    validate_execution_receipt,
)
from automation.multimodel_research_v1.termination import (
    validate_termination_record,
)

OBSERVATION_BINDING_SCHEMA = "MULTIVERSE_PROVIDER_OBSERVATION_BINDING_v1"

OBSERVATION_BINDING_KEYS = {
    "schema",
    "provider",
    "provider_response_id",
    "observed_model_id",
    "normalized_state",
    "usage_metadata_sha256",
    "provider_response_sha256",
    "termination_record_sha256",
    "execution_receipt_sha256",
}


def validate_provider_observation_binding(
    *,
    provider: str,
    observation: dict[str, Any],
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    termination_record: dict[str, Any],
    result: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    require(
        provider in {"GOOGLE_GEMINI", "ANTHROPIC_CLAUDE"},
        "OBSERVATION_PROVIDER",
    )
    require(
        isinstance(observation, dict),
        "OBSERVATION_OBJECT",
    )

    expected_schema = (
        "MULTIVERSE_GEMINI_INTERACTIONS_V1_OBSERVATION_v1"
        if provider == "GOOGLE_GEMINI"
        else "MULTIVERSE_CLAUDE_MESSAGES_OBSERVATION_v1"
    )
    require(
        observation.get("schema") == expected_schema,
        "OBSERVATION_SCHEMA_MISMATCH",
    )

    validate_termination_record(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        termination_record,
    )
    validate_execution_receipt(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        termination_record,
        result,
        receipt,
    )

    require(
        observation.get("provider_response_id")
        == termination_record["provider_response_id"],
        "OBSERVATION_RESPONSE_ID_TERMINATION_MISMATCH",
    )
    require(
        observation.get("provider_response_id")
        == receipt["provider_response_id"],
        "OBSERVATION_RESPONSE_ID_RECEIPT_MISMATCH",
    )
    require(
        observation.get("normalized_state")
        == termination_record["normalized_state"],
        "OBSERVATION_NORMALIZED_STATE_MISMATCH",
    )
    require(
        observation.get("input_tokens")
        == termination_record["input_tokens"],
        "OBSERVATION_INPUT_TOKENS_MISMATCH",
    )
    require(
        observation.get("output_tokens")
        == termination_record["output_tokens"],
        "OBSERVATION_OUTPUT_TOKENS_MISMATCH",
    )
    require(
        observation.get("usage_metadata_sha256")
        == termination_record["usage_metadata_sha256"],
        "OBSERVATION_USAGE_SHA256_MISMATCH",
    )
    require(
        observation.get("provider_response_sha256")
        == receipt["provider_response_sha256"],
        "OBSERVATION_RESPONSE_SHA256_MISMATCH",
    )

    observed_model_id = observation.get("observed_model_id")
    require(
        observed_model_id == receipt["observed_model_id"],
        "OBSERVATION_MODEL_ID_RECEIPT_MISMATCH",
    )

    binding = {
        "schema": OBSERVATION_BINDING_SCHEMA,
        "provider": provider,
        "provider_response_id":
            observation["provider_response_id"],
        "observed_model_id": observed_model_id,
        "normalized_state":
            observation["normalized_state"],
        "usage_metadata_sha256":
            observation["usage_metadata_sha256"],
        "provider_response_sha256":
            observation["provider_response_sha256"],
        "termination_record_sha256":
            sha256_json(termination_record),
        "execution_receipt_sha256":
            sha256_json(receipt),
    }
    require(
        set(binding) == OBSERVATION_BINDING_KEYS,
        "OBSERVATION_BINDING_SCHEMA_KEYS",
    )
    return binding


def provider_observation_binding_sha256(
    **kwargs: Any,
) -> str:
    return sha256_json(
        validate_provider_observation_binding(**kwargs)
    )
