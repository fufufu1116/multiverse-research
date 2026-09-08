from __future__ import annotations

import re
from typing import Any

from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.smoke_profile import (
    live_smoke_profile_sha256,
    validate_live_smoke_profile,
)
from automation.multimodel_research_v1.transport_binding import (
    transport_binding_sha256,
    validate_transport_binding,
)

EXECUTION_PREP_SCHEMA = "MULTIVERSE_LIVE_PROVIDER_EXECUTION_PREP_v1"

EXECUTION_PREP_KEYS = {
    "schema",
    "prep_id",
    "provider",
    "smoke_profile_sha256",
    "transport_binding_sha256",
    "allowed_host",
    "allowed_operation",
    "network_scope",
    "credential_handle_ref",
    "credential_material_in_repository",
    "max_attempts",
    "max_input_tokens",
    "max_output_tokens",
    "proposed_max_cost_usd_micros",
    "provider_call_authority_required",
    "credential_authority_required",
    "spend_authority_required",
    "runtime_activation",
    "live_business_effect",
    "protected_data",
}

PROVIDER_TARGETS = {
    "GOOGLE_GEMINI": {
        "host": "generativelanguage.googleapis.com",
        "operation": "INTERACTIONS_CREATE_V1",
    },
    "ANTHROPIC_CLAUDE": {
        "host": "api.anthropic.com",
        "operation": "MESSAGES_CREATE_V1",
    },
}

FIRST_SMOKE_MAX_OUTPUT_TOKENS = 4096
FIRST_SMOKE_MAX_INPUT_TOKENS = 32768
FIRST_SMOKE_MAX_COST_USD_MICROS = 1_000_000


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}",
                value,
            )
        ),
        code,
    )
    return value


def validate_live_execution_prep(
    *,
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    fanout_plan: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    smoke_profile: dict[str, Any],
    response_schema: dict[str, Any],
    render: dict[str, Any],
    prep: dict[str, Any],
) -> dict[str, Any]:
    validate_live_smoke_profile(
        task,
        assignments,
        fanout_plan,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        smoke_profile,
    )
    binding = validate_transport_binding(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        response_schema,
        render,
    )

    require(
        isinstance(prep, dict)
        and set(prep) == EXECUTION_PREP_KEYS,
        "EXECUTION_PREP_SCHEMA_KEYS",
    )
    require(
        prep["schema"] == EXECUTION_PREP_SCHEMA,
        "EXECUTION_PREP_SCHEMA_VERSION",
    )
    _identifier(prep["prep_id"], "EXECUTION_PREP_ID")

    provider = prep["provider"]
    require(
        provider in PROVIDER_TARGETS,
        "EXECUTION_PREP_PROVIDER",
    )
    require(
        provider == binding["provider"],
        "EXECUTION_PREP_PROVIDER_MISMATCH",
    )
    require(
        prep["smoke_profile_sha256"]
        == live_smoke_profile_sha256(
            task,
            assignments,
            fanout_plan,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
            smoke_profile,
        ),
        "EXECUTION_PREP_SMOKE_SHA256_MISMATCH",
    )
    require(
        prep["transport_binding_sha256"]
        == transport_binding_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
            response_schema,
            render,
        ),
        "EXECUTION_PREP_TRANSPORT_SHA256_MISMATCH",
    )

    expected = PROVIDER_TARGETS[provider]
    require(
        prep["allowed_host"] == expected["host"],
        "EXECUTION_PREP_HOST_MISMATCH",
    )
    require(
        prep["allowed_operation"] == expected["operation"],
        "EXECUTION_PREP_OPERATION_MISMATCH",
    )
    require(
        prep["network_scope"] == "PROVIDER_API_ONLY",
        "EXECUTION_PREP_NETWORK_SCOPE",
    )

    _identifier(
        prep["credential_handle_ref"],
        "EXECUTION_PREP_CREDENTIAL_HANDLE_REF",
    )
    require(
        prep["credential_material_in_repository"] is False,
        "EXECUTION_PREP_CREDENTIAL_MATERIAL_FORBIDDEN",
    )
    require(
        prep["max_attempts"] == 1,
        "EXECUTION_PREP_SINGLE_ATTEMPT_REQUIRED",
    )

    max_input = prep["max_input_tokens"]
    max_output = prep["max_output_tokens"]
    require(
        isinstance(max_input, int)
        and not isinstance(max_input, bool)
        and 1 <= max_input <= FIRST_SMOKE_MAX_INPUT_TOKENS,
        "EXECUTION_PREP_INPUT_TOKEN_CEILING",
    )
    require(
        isinstance(max_output, int)
        and not isinstance(max_output, bool)
        and 1 <= max_output <= FIRST_SMOKE_MAX_OUTPUT_TOKENS,
        "EXECUTION_PREP_OUTPUT_TOKEN_CEILING",
    )

    max_cost = prep["proposed_max_cost_usd_micros"]
    require(
        isinstance(max_cost, int)
        and not isinstance(max_cost, bool)
        and 1 <= max_cost <= FIRST_SMOKE_MAX_COST_USD_MICROS,
        "EXECUTION_PREP_COST_CEILING",
    )

    for key in (
        "provider_call_authority_required",
        "credential_authority_required",
        "spend_authority_required",
    ):
        require(
            prep[key] is True,
            f"EXECUTION_PREP_AUTHORITY_REQUIRED:{key}",
        )

    require(
        prep["runtime_activation"] is False,
        "EXECUTION_PREP_RUNTIME_FORBIDDEN",
    )
    require(
        prep["live_business_effect"] is False,
        "EXECUTION_PREP_LIVE_EFFECT_FORBIDDEN",
    )
    require(
        prep["protected_data"] is False,
        "EXECUTION_PREP_PROTECTED_DATA_FORBIDDEN",
    )
    return prep


def live_execution_prep_sha256(**kwargs: Any) -> str:
    return sha256_json(
        validate_live_execution_prep(**kwargs)
    )
