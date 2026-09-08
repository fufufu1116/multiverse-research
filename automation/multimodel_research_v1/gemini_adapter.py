from __future__ import annotations

import json
from typing import Any

from automation.multimodel_research_v1.assignment import (
    validate_assignment,
)
from automation.multimodel_research_v1.capability import (
    validate_capability_policy,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.model_target import (
    validate_model_target_policy,
)
from automation.multimodel_research_v1.prompting import (
    validate_provider_neutral_prompt,
)

GEMINI_TRANSPORT_SCHEMA = "MULTIVERSE_GEMINI_INTERACTIONS_V1_RENDER_v1"
GEMINI_OBSERVATION_SCHEMA = "MULTIVERSE_GEMINI_INTERACTIONS_V1_OBSERVATION_v1"

SMOKE_MAX_OUTPUT_TOKENS = 4096

GEMINI_RENDER_KEYS = {
    "schema",
    "provider",
    "sdk_surface",
    "api_version",
    "credential_material_included",
    "body",
}

GEMINI_OBSERVATION_KEYS = {
    "schema",
    "provider_response_id",
    "observed_model_id",
    "native_status",
    "normalized_state",
    "output_text",
    "input_tokens",
    "output_tokens",
    "usage_metadata_sha256",
    "provider_response_sha256",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def render_gemini_interactions_v1(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    validate_model_target_policy(
        task,
        assignment,
        model_target_policy,
    )
    validate_capability_policy(
        task,
        assignment,
        model_target_policy,
        capability_policy,
    )
    validate_provider_neutral_prompt(task, prompt)

    require(
        assignment["execution_mode"] == "LIVE_ADVISORY",
        "GEMINI_RENDER_REQUIRES_LIVE_ASSIGNMENT",
    )
    require(
        isinstance(response_schema, dict)
        and bool(response_schema),
        "GEMINI_RESPONSE_SCHEMA_OBJECT",
    )
    require(
        sha256_json(response_schema)
        == prompt["response_schema_sha256"],
        "GEMINI_RESPONSE_SCHEMA_SHA256_MISMATCH",
    )
    require(
        capability_policy["structured_output"] == "JSON_ONLY",
        "GEMINI_JSON_ONLY_REQUIRED",
    )
    require(
        capability_policy["streaming"] is False,
        "GEMINI_STREAMING_FORBIDDEN",
    )

    body = {
        "model": assignment["target_model"],
        "input": _canonical_json(prompt),
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema,
        },
        "stream": False,
        "store": False,
        "background": False,
        "generation_config": {
            "max_output_tokens": SMOKE_MAX_OUTPUT_TOKENS,
        },
    }

    return {
        "schema": GEMINI_TRANSPORT_SCHEMA,
        "provider": "GOOGLE_GEMINI",
        "sdk_surface": "interactions.create",
        "api_version": "v1",
        "credential_material_included": False,
        "body": body,
    }


def gemini_render_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    response_schema: dict[str, Any],
) -> str:
    return sha256_json(
        render_gemini_interactions_v1(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    )


def parse_gemini_interactions_v1_response(
    response: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(response, dict),
        "GEMINI_RESPONSE_OBJECT",
    )

    response_id = response.get("id")
    require(
        isinstance(response_id, str)
        and bool(response_id),
        "GEMINI_RESPONSE_ID_REQUIRED",
    )
    model = response.get("model")
    require(
        isinstance(model, str) and bool(model),
        "GEMINI_RESPONSE_MODEL_REQUIRED",
    )
    status = response.get("status")
    require(
        status in {
            "completed",
            "failed",
            "cancelled",
            "incomplete",
        },
        "GEMINI_RESPONSE_TERMINAL_STATUS",
    )

    usage = response.get("usage")
    require(
        isinstance(usage, dict),
        "GEMINI_RESPONSE_USAGE_REQUIRED",
    )
    input_tokens = usage.get("total_input_tokens")
    output_tokens = usage.get("total_output_tokens")
    for key, value in (
        ("input", input_tokens),
        ("output", output_tokens),
    ):
        require(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0,
            f"GEMINI_RESPONSE_{key.upper()}_TOKENS",
        )

    steps = response.get("steps", [])
    require(
        isinstance(steps, list),
        "GEMINI_RESPONSE_STEPS",
    )
    texts: list[str] = []
    for step in steps:
        require(
            isinstance(step, dict),
            "GEMINI_RESPONSE_STEP_OBJECT",
        )
        if step.get("type") != "model_output":
            continue
        content = step.get("content", [])
        require(
            isinstance(content, list),
            "GEMINI_RESPONSE_CONTENT",
        )
        for item in content:
            if (
                isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ):
                texts.append(item["text"])

    output_text = "".join(texts)

    if status == "completed":
        normalized = (
            "COMPLETED"
            if output_text
            else "PROVIDER_EMPTY"
        )
    elif status == "incomplete":
        normalized = "PROVIDER_TRUNCATED"
    else:
        normalized = "TRANSPORT_FAILURE"

    observation = {
        "schema": GEMINI_OBSERVATION_SCHEMA,
        "provider_response_id": response_id,
        "observed_model_id": model,
        "native_status": status,
        "normalized_state": normalized,
        "output_text": output_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "usage_metadata_sha256": sha256_json(usage),
        "provider_response_sha256": sha256_json(response),
    }
    require(
        set(observation) == GEMINI_OBSERVATION_KEYS,
        "GEMINI_OBSERVATION_SCHEMA_KEYS",
    )
    return observation
