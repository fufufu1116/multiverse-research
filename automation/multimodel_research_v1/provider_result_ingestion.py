from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    result_v2_content_digest,
    validate_assignment,
    validate_result_v2_for_assignment,
)
from automation.multimodel_research_v1.model import (
    ResearchContractError,
    require,
    sha256_json,
)

INGESTION_SCHEMA = "MULTIVERSE_PROVIDER_RESULT_INGESTION_v1"

INGESTION_KEYS = {
    "schema",
    "provider",
    "assignment_sha256",
    "provider_response_id",
    "provider_response_sha256",
    "observed_model_id",
    "normalized_state",
    "output_text_sha256",
    "output_bytes",
    "result",
    "result_sha256",
    "result_content_digest",
    "nonauthority",
}


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ResearchContractError(
                f"PROVIDER_RESULT_JSON_DUPLICATE_KEY:{key}"
            )
        value[key] = child
    return value


def _reject_nonfinite_constant(value: str) -> None:
    raise ResearchContractError(
        f"PROVIDER_RESULT_JSON_NONFINITE:{value}"
    )


def _strict_result_object(output_text: str) -> dict[str, Any]:
    require(
        isinstance(output_text, str) and bool(output_text),
        "PROVIDER_RESULT_OUTPUT_TEXT_REQUIRED",
    )
    try:
        value = json.loads(
            output_text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise ResearchContractError(
            "PROVIDER_RESULT_JSON_INVALID"
        ) from exc
    require(
        isinstance(value, dict),
        "PROVIDER_RESULT_JSON_OBJECT_REQUIRED",
    )
    return value


def _validated_common_observation(
    assignment: dict[str, Any],
    provider: str,
    observation: dict[str, Any],
) -> tuple[str, int]:
    require(
        isinstance(provider, str)
        and provider == assignment["target_provider"],
        "PROVIDER_RESULT_PROVIDER_MISMATCH",
    )
    require(
        isinstance(observation, dict),
        "PROVIDER_RESULT_OBSERVATION_OBJECT",
    )

    response_id = observation.get("provider_response_id")
    require(
        isinstance(response_id, str) and bool(response_id),
        "PROVIDER_RESULT_RESPONSE_ID_REQUIRED",
    )
    observed_model_id = observation.get("observed_model_id")
    require(
        isinstance(observed_model_id, str)
        and observed_model_id == assignment["target_model"],
        "PROVIDER_RESULT_OBSERVED_MODEL_MISMATCH",
    )
    require(
        observation.get("normalized_state") == "COMPLETED",
        "PROVIDER_RESULT_REQUIRES_COMPLETED_OBSERVATION",
    )
    _sha256(
        observation.get("provider_response_sha256"),
        "PROVIDER_RESULT_RESPONSE_SHA256",
    )

    output_text = observation.get("output_text")
    require(
        isinstance(output_text, str) and bool(output_text),
        "PROVIDER_RESULT_OUTPUT_TEXT_REQUIRED",
    )
    output_bytes = len(output_text.encode("utf-8"))
    require(
        output_bytes <= assignment["max_output_bytes"],
        "PROVIDER_RESULT_ASSIGNMENT_OUTPUT_LIMIT_EXCEEDED",
    )
    return output_text, output_bytes


def _build_provider_result_ingestion_unchecked(
    task: dict[str, Any],
    assignment: dict[str, Any],
    provider: str,
    observation: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    output_text, output_bytes = _validated_common_observation(
        assignment,
        provider,
        observation,
    )
    result = _strict_result_object(output_text)
    validate_result_v2_for_assignment(
        task,
        assignment,
        result,
    )

    return {
        "schema": INGESTION_SCHEMA,
        "provider": provider,
        "assignment_sha256": assignment_sha256(
            task,
            assignment,
        ),
        "provider_response_id":
            observation["provider_response_id"],
        "provider_response_sha256":
            observation["provider_response_sha256"],
        "observed_model_id":
            observation["observed_model_id"],
        "normalized_state":
            observation["normalized_state"],
        "output_text_sha256":
            hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "output_bytes": output_bytes,
        "result": result,
        "result_sha256": sha256_json(result),
        "result_content_digest":
            result_v2_content_digest(
                task,
                assignment,
                result,
            ),
        "nonauthority": dict(result["nonauthority"]),
    }


def build_provider_result_ingestion(
    task: dict[str, Any],
    assignment: dict[str, Any],
    provider: str,
    observation: dict[str, Any],
) -> dict[str, Any]:
    value = _build_provider_result_ingestion_unchecked(
        task,
        assignment,
        provider,
        observation,
    )
    return validate_provider_result_ingestion(
        task,
        assignment,
        provider,
        observation,
        value,
    )


def validate_provider_result_ingestion(
    task: dict[str, Any],
    assignment: dict[str, Any],
    provider: str,
    observation: dict[str, Any],
    ingestion: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(ingestion, dict)
        and set(ingestion) == INGESTION_KEYS,
        "PROVIDER_RESULT_INGESTION_SCHEMA_KEYS",
    )
    require(
        ingestion["schema"] == INGESTION_SCHEMA,
        "PROVIDER_RESULT_INGESTION_SCHEMA_VERSION",
    )
    expected = _build_provider_result_ingestion_unchecked(
        task,
        assignment,
        provider,
        observation,
    )
    require(
        ingestion == expected,
        "PROVIDER_RESULT_INGESTION_EXACT_MISMATCH",
    )
    return ingestion


def provider_result_ingestion_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    provider: str,
    observation: dict[str, Any],
    ingestion: dict[str, Any],
) -> str:
    validate_provider_result_ingestion(
        task,
        assignment,
        provider,
        observation,
        ingestion,
    )
    return sha256_json(ingestion)
