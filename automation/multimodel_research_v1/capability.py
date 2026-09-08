from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
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

CAPABILITY_POLICY_SCHEMA = "MULTIVERSE_PROVIDER_CAPABILITY_POLICY_v1"

CAPABILITY_POLICY_KEYS = {
    "schema",
    "policy_id",
    "assignment_sha256",
    "model_target_policy_sha256",
    "tools",
    "provider_retrieval_search",
    "code_execution",
    "file_access",
    "provider_memory",
    "function_calling",
    "structured_output",
    "streaming",
    "nonauthority",
}


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "CAPABILITY_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"CAPABILITY_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_capability_policy(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    validate_model_target_policy(
        task,
        assignment,
        model_target_policy,
    )

    require(
        isinstance(policy, dict)
        and set(policy) == CAPABILITY_POLICY_KEYS,
        "CAPABILITY_POLICY_SCHEMA_KEYS",
    )
    require(
        policy["schema"] == CAPABILITY_POLICY_SCHEMA,
        "CAPABILITY_POLICY_SCHEMA_VERSION",
    )
    require(
        isinstance(policy["policy_id"], str)
        and 3 <= len(policy["policy_id"]) <= 127,
        "CAPABILITY_POLICY_ID",
    )
    require(
        policy["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "CAPABILITY_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        policy["model_target_policy_sha256"]
        == model_target_policy_sha256(
            task,
            assignment,
            model_target_policy,
        ),
        "CAPABILITY_MODEL_TARGET_SHA256_MISMATCH",
    )

    require(
        policy["tools"] == "NONE",
        "CAPABILITY_TOOLS_FORBIDDEN",
    )
    require(
        policy["provider_retrieval_search"] == "NONE",
        "CAPABILITY_PROVIDER_RETRIEVAL_FORBIDDEN",
    )
    require(
        policy["code_execution"] == "NONE",
        "CAPABILITY_CODE_EXECUTION_FORBIDDEN",
    )
    require(
        policy["file_access"] == "NONE",
        "CAPABILITY_FILE_ACCESS_FORBIDDEN",
    )
    require(
        policy["provider_memory"] == "NONE",
        "CAPABILITY_PROVIDER_MEMORY_FORBIDDEN",
    )
    require(
        policy["function_calling"] == "NONE",
        "CAPABILITY_FUNCTION_CALLING_FORBIDDEN",
    )
    require(
        policy["structured_output"] == "JSON_ONLY",
        "CAPABILITY_STRUCTURED_OUTPUT_JSON_REQUIRED",
    )
    require(
        policy["streaming"] is False,
        "CAPABILITY_STREAMING_FORBIDDEN",
    )

    _nonauthority(policy["nonauthority"])
    return policy


def capability_policy_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    validate_capability_policy(
        task,
        assignment,
        model_target_policy,
        policy,
    )
    return sha256_json(policy)
