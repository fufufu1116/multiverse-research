from __future__ import annotations

import re
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

MODEL_TARGET_POLICY_SCHEMA = "MULTIVERSE_MODEL_TARGET_POLICY_v1"

MODEL_TARGET_POLICY_KEYS = {
    "schema",
    "policy_id",
    "assignment_sha256",
    "provider",
    "requested_model_id",
    "model_id_classification",
    "classification_evidence_ref",
    "classification_evidence_sha256",
    "alias_allowed",
    "preview_allowed",
    "experimental_allowed",
    "resolved_model_id_required",
    "stable_provider_api_required",
    "nonauthority",
}

MODEL_ID_CLASSIFICATIONS = {
    "PINNED_OR_STABLE",
    "ALIAS",
    "PREVIEW",
    "EXPERIMENTAL",
    "UNKNOWN",
}


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


def _text(value: Any, code: str, max_len: int = 4000) -> str:
    require(
        isinstance(value, str)
        and 0 < len(value) <= max_len,
        code,
    )
    return value


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "MODEL_TARGET_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"MODEL_TARGET_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_model_target_policy(
    task: dict[str, Any],
    assignment: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    require(
        isinstance(policy, dict)
        and set(policy) == MODEL_TARGET_POLICY_KEYS,
        "MODEL_TARGET_POLICY_SCHEMA_KEYS",
    )
    require(
        policy["schema"] == MODEL_TARGET_POLICY_SCHEMA,
        "MODEL_TARGET_POLICY_SCHEMA_VERSION",
    )
    _identifier(
        policy["policy_id"],
        "MODEL_TARGET_POLICY_ID",
    )
    require(
        policy["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "MODEL_TARGET_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        policy["provider"] == assignment["target_provider"],
        "MODEL_TARGET_PROVIDER_MISMATCH",
    )
    require(
        policy["requested_model_id"]
        == assignment["target_model"],
        "MODEL_TARGET_MODEL_ID_MISMATCH",
    )

    classification = policy["model_id_classification"]
    require(
        classification in MODEL_ID_CLASSIFICATIONS,
        "MODEL_TARGET_CLASSIFICATION",
    )
    _text(
        policy["classification_evidence_ref"],
        "MODEL_TARGET_CLASSIFICATION_EVIDENCE_REF",
    )
    _sha256(
        policy["classification_evidence_sha256"],
        "MODEL_TARGET_CLASSIFICATION_EVIDENCE_SHA256",
    )

    for key in (
        "alias_allowed",
        "preview_allowed",
        "experimental_allowed",
        "resolved_model_id_required",
        "stable_provider_api_required",
    ):
        require(
            isinstance(policy[key], bool),
            f"MODEL_TARGET_POLICY_BOOL:{key}",
        )

    require(
        policy["alias_allowed"] is False,
        "MODEL_TARGET_ALIAS_FORBIDDEN",
    )
    require(
        policy["preview_allowed"] is False,
        "MODEL_TARGET_PREVIEW_FORBIDDEN",
    )
    require(
        policy["experimental_allowed"] is False,
        "MODEL_TARGET_EXPERIMENTAL_FORBIDDEN",
    )
    require(
        policy["resolved_model_id_required"] is True,
        "MODEL_TARGET_RESOLVED_ID_REQUIRED",
    )
    require(
        policy["stable_provider_api_required"] is True,
        "MODEL_TARGET_STABLE_API_REQUIRED",
    )
    require(
        classification == "PINNED_OR_STABLE",
        "MODEL_TARGET_NOT_PINNED_OR_STABLE",
    )

    _nonauthority(policy["nonauthority"])
    return policy


def model_target_policy_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    policy: dict[str, Any],
) -> str:
    validate_model_target_policy(
        task,
        assignment,
        policy,
    )
    return sha256_json(policy)


def validate_resolved_model_id(
    task: dict[str, Any],
    assignment: dict[str, Any],
    policy: dict[str, Any],
    observed_model_id: str,
) -> str:
    validate_model_target_policy(
        task,
        assignment,
        policy,
    )
    _identifier(
        observed_model_id,
        "OBSERVED_MODEL_ID",
    )
    require(
        observed_model_id == policy["requested_model_id"],
        "OBSERVED_MODEL_ID_MISMATCH",
    )
    return observed_model_id
