from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.claude_adapter import (
    render_claude_messages_request,
)
from automation.multimodel_research_v1.gemini_adapter import (
    render_gemini_interactions_v1,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)

TRANSPORT_BINDING_SCHEMA = "MULTIVERSE_PROVIDER_TRANSPORT_BINDING_v1"

TRANSPORT_BINDING_KEYS = {
    "schema",
    "provider",
    "request_envelope_sha256",
    "render_sha256",
    "outbound_payload_sha256",
    "credential_material_included",
}


def _expected_render(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    response_schema: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    if provider == "GOOGLE_GEMINI":
        return render_gemini_interactions_v1(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    if provider == "ANTHROPIC_CLAUDE":
        return render_claude_messages_request(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    raise RuntimeError("UNSUPPORTED_PROVIDER_RENDER")


def validate_transport_binding(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    response_schema: dict[str, Any],
    render: dict[str, Any],
) -> dict[str, Any]:
    validate_request_envelope(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
    )

    require(
        isinstance(render, dict),
        "TRANSPORT_RENDER_OBJECT",
    )
    provider = render.get("provider")
    require(
        provider in {
            "GOOGLE_GEMINI",
            "ANTHROPIC_CLAUDE",
        },
        "TRANSPORT_PROVIDER",
    )

    expected = _expected_render(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        response_schema,
        provider,
    )
    require(
        render == expected,
        "TRANSPORT_RENDER_EXACT_MISMATCH",
    )
    require(
        render.get("credential_material_included") is False,
        "TRANSPORT_CREDENTIAL_MATERIAL_FORBIDDEN",
    )

    body_sha256 = sha256_json(render["body"])
    require(
        request_envelope["outbound_payload_sha256"]
        == body_sha256,
        "TRANSPORT_OUTBOUND_PAYLOAD_SHA256_MISMATCH",
    )

    binding = {
        "schema": TRANSPORT_BINDING_SCHEMA,
        "provider": provider,
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                model_target_policy,
                capability_policy,
                prompt,
                request_envelope,
            ),
        "render_sha256": sha256_json(render),
        "outbound_payload_sha256": body_sha256,
        "credential_material_included": False,
    }
    require(
        set(binding) == TRANSPORT_BINDING_KEYS,
        "TRANSPORT_BINDING_SCHEMA_KEYS",
    )
    return binding


def transport_binding_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    response_schema: dict[str, Any],
    render: dict[str, Any],
) -> str:
    return sha256_json(
        validate_transport_binding(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
            response_schema,
            render,
        )
    )
