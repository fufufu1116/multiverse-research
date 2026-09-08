from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
)
from automation.multimodel_research_v1.capability import (
    capability_policy_sha256,
    validate_capability_policy,
)
from automation.multimodel_research_v1.fanout import (
    fanout_plan_sha256,
    validate_fanout_plan,
)
from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    require,
    sha256_json,
)
from automation.multimodel_research_v1.model_target import (
    model_target_policy_sha256,
    validate_model_target_policy,
)
from automation.multimodel_research_v1.prompting import (
    validate_provider_neutral_prompt,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)

SMOKE_PROFILE_SCHEMA = "MULTIVERSE_LIVE_PROVIDER_SMOKE_PROFILE_v1"

SMOKE_PROFILE_KEYS = {
    "schema",
    "profile_id",
    "fanout_plan_sha256",
    "assignment_sha256",
    "model_target_policy_sha256",
    "capability_policy_sha256",
    "request_envelope_sha256",
    "planned_provider_count",
    "planned_assignment_count",
    "max_attempts_per_assignment",
    "data_ceiling",
    "structured_output",
    "streaming",
    "protected_data",
    "live_business_effect",
    "runtime_activation",
    "adoption_authority",
    "nonauthority",
}


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "SMOKE_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"SMOKE_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_live_smoke_profile(
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    fanout_plan: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    validate_fanout_plan(
        task,
        assignments,
        fanout_plan,
    )
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
    validate_request_envelope(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
    )

    require(
        len(assignments) == 1,
        "SMOKE_EXACTLY_ONE_ASSIGNMENT_REQUIRED",
    )
    require(
        assignments[0] == assignment,
        "SMOKE_ASSIGNMENT_OBJECT_MISMATCH",
    )
    require(
        assignment["execution_mode"] == "LIVE_ADVISORY",
        "SMOKE_REQUIRES_LIVE_ASSIGNMENT",
    )

    require(
        isinstance(profile, dict)
        and set(profile) == SMOKE_PROFILE_KEYS,
        "SMOKE_PROFILE_SCHEMA_KEYS",
    )
    require(
        profile["schema"] == SMOKE_PROFILE_SCHEMA,
        "SMOKE_PROFILE_SCHEMA_VERSION",
    )
    require(
        isinstance(profile["profile_id"], str)
        and 3 <= len(profile["profile_id"]) <= 127,
        "SMOKE_PROFILE_ID",
    )
    require(
        profile["fanout_plan_sha256"]
        == fanout_plan_sha256(
            task,
            assignments,
            fanout_plan,
        ),
        "SMOKE_FANOUT_SHA256_MISMATCH",
    )
    require(
        profile["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "SMOKE_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        profile["model_target_policy_sha256"]
        == model_target_policy_sha256(
            task,
            assignment,
            model_target_policy,
        ),
        "SMOKE_MODEL_TARGET_SHA256_MISMATCH",
    )
    require(
        profile["capability_policy_sha256"]
        == capability_policy_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
        ),
        "SMOKE_CAPABILITY_SHA256_MISMATCH",
    )
    require(
        profile["request_envelope_sha256"]
        == request_envelope_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
        ),
        "SMOKE_REQUEST_SHA256_MISMATCH",
    )

    unique_providers = {
        item["target_provider"]
        for item in assignments
    }
    require(
        profile["planned_provider_count"] == 1
        and len(unique_providers) == 1,
        "SMOKE_EXACTLY_ONE_PROVIDER_REQUIRED",
    )
    require(
        profile["planned_assignment_count"] == 1,
        "SMOKE_PLANNED_ASSIGNMENT_COUNT",
    )
    require(
        profile["max_attempts_per_assignment"] == 1,
        "SMOKE_SINGLE_ATTEMPT_REQUIRED",
    )
    require(
        profile["data_ceiling"] == "SYNTHETIC_ONLY",
        "SMOKE_SYNTHETIC_ONLY_REQUIRED",
    )
    require(
        request_envelope["objective_classification"]
        == "SYNTHETIC",
        "SMOKE_REQUEST_OBJECTIVE_NOT_SYNTHETIC",
    )
    require(
        all(
            item["classification"] == "SYNTHETIC"
            for item in request_envelope["egress_items"]
        ),
        "SMOKE_REQUEST_EGRESS_NOT_SYNTHETIC",
    )
    require(
        profile["structured_output"] == "JSON_ONLY",
        "SMOKE_JSON_ONLY_REQUIRED",
    )
    require(
        profile["streaming"] is False,
        "SMOKE_STREAMING_FORBIDDEN",
    )
    require(
        profile["protected_data"] is False,
        "SMOKE_PROTECTED_DATA_FORBIDDEN",
    )
    require(
        profile["live_business_effect"] is False,
        "SMOKE_LIVE_BUSINESS_EFFECT_FORBIDDEN",
    )
    require(
        profile["runtime_activation"] is False,
        "SMOKE_RUNTIME_ACTIVATION_FORBIDDEN",
    )
    require(
        profile["adoption_authority"] is False,
        "SMOKE_ADOPTION_AUTHORITY_FORBIDDEN",
    )
    _nonauthority(profile["nonauthority"])
    return profile


def live_smoke_profile_sha256(
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    fanout_plan: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    validate_live_smoke_profile(
        task,
        assignments,
        fanout_plan,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        profile,
    )
    return sha256_json(profile)
