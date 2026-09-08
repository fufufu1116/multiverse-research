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

CLAUDE_TRANSPORT_SCHEMA = "MULTIVERSE_CLAUDE_MESSAGES_RENDER_v1"
CLAUDE_OBSERVATION_SCHEMA = "MULTIVERSE_CLAUDE_MESSAGES_OBSERVATION_v1"

SMOKE_MAX_TOKENS = 4096

CLAUDE_RENDER_KEYS = {
    "schema",
    "provider",
    "sdk_surface",
    "stateless",
    "credential_material_included",
    "body",
}

CLAUDE_OBSERVATION_KEYS = {
    "schema",
    "provider_response_id",
    "observed_model_id",
    "native_stop_reason",
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


def render_claude_messages_request(
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
        "CLAUDE_RENDER_REQUIRES_LIVE_ASSIGNMENT",
    )
    require(
        isinstance(response_schema, dict)
        and bool(response_schema),
        "CLAUDE_RESPONSE_SCHEMA_OBJECT",
    )
    require(
        sha256_json(response_schema)
        == prompt["response_schema_sha256"],
        "CLAUDE_RESPONSE_SCHEMA_SHA256_MISMATCH",
    )
    require(
        capability_policy["structured_output"] == "JSON_ONLY",
        "CLAUDE_JSON_ONLY_REQUIRED",
    )
    require(
        capability_policy["streaming"] is False,
        "CLAUDE_STREAMING_FORBIDDEN",
    )

    body = {
        "model": assignment["target_model"],
        "max_tokens": SMOKE_MAX_TOKENS,
        "messages": [
            {
                "role": "user",
                "content": _canonical_json(prompt),
            }
        ],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": response_schema,
            }
        },
        "stream": False,
    }

    return {
        "schema": CLAUDE_TRANSPORT_SCHEMA,
        "provider": "ANTHROPIC_CLAUDE",
        "sdk_surface": "messages.create",
        "stateless": True,
        "credential_material_included": False,
        "body": body,
    }


def claude_render_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    response_schema: dict[str, Any],
) -> str:
    return sha256_json(
        render_claude_messages_request(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    )


def parse_claude_messages_response(
    response: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(response, dict),
        "CLAUDE_RESPONSE_OBJECT",
    )

    response_id = response.get("id")
    require(
        isinstance(response_id, str)
        and bool(response_id),
        "CLAUDE_RESPONSE_ID_REQUIRED",
    )
    model = response.get("model")
    require(
        isinstance(model, str) and bool(model),
        "CLAUDE_RESPONSE_MODEL_REQUIRED",
    )
    stop_reason = response.get("stop_reason")
    require(
        stop_reason in {
            "end_turn",
            "max_tokens",
            "stop_sequence",
            "refusal",
            "model_context_window_exceeded",
            "tool_use",
            "pause_turn",
        },
        "CLAUDE_STOP_REASON",
    )

    usage = response.get("usage")
    require(
        isinstance(usage, dict),
        "CLAUDE_RESPONSE_USAGE_REQUIRED",
    )
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    for key, value in (
        ("input", input_tokens),
        ("output", output_tokens),
    ):
        require(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0,
            f"CLAUDE_RESPONSE_{key.upper()}_TOKENS",
        )

    server_tool_use = usage.get("server_tool_use")
    if server_tool_use is not None:
        require(
            isinstance(server_tool_use, dict),
            "CLAUDE_SERVER_TOOL_USE_OBJECT",
        )
        for value in server_tool_use.values():
            require(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value == 0,
                "CLAUDE_UNEXPECTED_SERVER_TOOL_USE",
            )

    content = response.get("content")
    require(
        isinstance(content, list),
        "CLAUDE_RESPONSE_CONTENT",
    )
    texts = [
        item["text"]
        for item in content
        if (
            isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        )
    ]
    output_text = "".join(texts)

    stop_details = response.get("stop_details")
    refusal_detail = (
        isinstance(stop_details, dict)
        and stop_details.get("type") == "refusal"
    )

    if stop_reason == "refusal" or refusal_detail:
        normalized = "PROVIDER_REFUSED"
    elif stop_reason == "end_turn":
        normalized = (
            "COMPLETED"
            if output_text
            else "PROVIDER_EMPTY"
        )
    elif stop_reason in {
        "max_tokens",
        "model_context_window_exceeded",
        "stop_sequence",
    }:
        normalized = "PROVIDER_TRUNCATED"
    else:
        raise RuntimeError(
            "CLAUDE_UNEXPECTED_TOOL_OR_PAUSE_STOP"
        )

    observation = {
        "schema": CLAUDE_OBSERVATION_SCHEMA,
        "provider_response_id": response_id,
        "observed_model_id": model,
        "native_stop_reason": stop_reason,
        "normalized_state": normalized,
        "output_text": output_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "usage_metadata_sha256": sha256_json(usage),
        "provider_response_sha256": sha256_json(response),
    }
    require(
        set(observation) == CLAUDE_OBSERVATION_KEYS,
        "CLAUDE_OBSERVATION_SCHEMA_KEYS",
    )
    return observation
