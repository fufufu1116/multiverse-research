from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    RESULT_KEYS,
    RESULT_SCHEMA,
    TASK_SCHEMA_V2,
    ResearchContractError,
    require,
    sha256_json,
    validate_result_for_task,
    validate_task,
)

ASSIGNMENT_SCHEMA = "MULTIVERSE_RESEARCH_ASSIGNMENT_v1"
RESULT_V2_SCHEMA = "MULTIVERSE_RESEARCH_RESULT_v2"

ASSIGNMENT_KEYS = {
    "schema",
    "assignment_id",
    "task_sha256",
    "snapshot_id",
    "created_at",
    "target_provider",
    "target_model",
    "requested_role",
    "adapter_sha256",
    "execution_mode",
    "research_network_access",
    "provider_transport_policy_ref",
    "max_compute_seconds",
    "max_output_bytes",
    "attestation_required",
    "nonauthority",
}

RESULT_V2_KEYS = RESULT_KEYS | {"assignment_sha256"}

EXECUTION_MODES = {
    "SYNTHETIC_OFFLINE",
    "LIVE_ADVISORY",
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


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def _parse_utc(value: Any, code: str) -> datetime:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                value,
            )
        ),
        code,
    )
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ResearchContractError(code) from exc


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "ASSIGNMENT_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"ASSIGNMENT_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_assignment(
    task: dict[str, Any],
    assignment: dict[str, Any],
) -> dict[str, Any]:
    validate_task(task)
    require(
        task["schema"] == TASK_SCHEMA_V2,
        "ASSIGNMENT_REQUIRES_TASK_V2",
    )
    require(
        isinstance(assignment, dict)
        and set(assignment) == ASSIGNMENT_KEYS,
        "ASSIGNMENT_SCHEMA_KEYS",
    )
    require(
        assignment["schema"] == ASSIGNMENT_SCHEMA,
        "ASSIGNMENT_SCHEMA_VERSION",
    )

    _identifier(
        assignment["assignment_id"],
        "ASSIGNMENT_ID",
    )
    require(
        assignment["task_sha256"] == sha256_json(task),
        "ASSIGNMENT_TASK_SHA256_MISMATCH",
    )
    require(
        assignment["snapshot_id"] == task["snapshot_id"],
        "ASSIGNMENT_SNAPSHOT_ID_MISMATCH",
    )
    assignment_created_at = _parse_utc(
        assignment["created_at"],
        "ASSIGNMENT_CREATED_AT",
    )
    task_created_at = _parse_utc(
        task["created_at"],
        "TASK_CREATED_AT",
    )
    require(
        assignment_created_at >= task_created_at,
        "ASSIGNMENT_CREATED_BEFORE_TASK",
    )

    _identifier(
        assignment["target_provider"],
        "ASSIGNMENT_TARGET_PROVIDER",
    )
    _identifier(
        assignment["target_model"],
        "ASSIGNMENT_TARGET_MODEL",
    )
    _identifier(
        assignment["requested_role"],
        "ASSIGNMENT_REQUESTED_ROLE",
    )
    require(
        assignment["requested_role"] in task["requested_roles"],
        "ASSIGNMENT_ROLE_NOT_REQUESTED",
    )
    _sha256(
        assignment["adapter_sha256"],
        "ASSIGNMENT_ADAPTER_SHA256",
    )

    mode = assignment["execution_mode"]
    require(
        mode in EXECUTION_MODES,
        "ASSIGNMENT_EXECUTION_MODE",
    )

    network = assignment["research_network_access"]
    require(
        network in {"NONE", "PUBLIC_READ_ONLY"},
        "ASSIGNMENT_RESEARCH_NETWORK_ACCESS",
    )
    if task["constraints"]["network_access"] == "NONE":
        require(
            network == "NONE",
            "ASSIGNMENT_RESEARCH_NETWORK_WIDENED",
        )

    transport = assignment[
        "provider_transport_policy_ref"
    ]
    _identifier(
        transport,
        "ASSIGNMENT_PROVIDER_TRANSPORT_POLICY_REF",
    )

    require(
        isinstance(assignment["max_compute_seconds"], int)
        and not isinstance(
            assignment["max_compute_seconds"],
            bool,
        )
        and 1 <= assignment["max_compute_seconds"]
        <= task["constraints"]["max_compute_seconds"],
        "ASSIGNMENT_MAX_COMPUTE_WIDENED",
    )
    require(
        isinstance(assignment["max_output_bytes"], int)
        and not isinstance(
            assignment["max_output_bytes"],
            bool,
        )
        and 1024 <= assignment["max_output_bytes"]
        <= task["constraints"]["max_output_bytes"],
        "ASSIGNMENT_MAX_OUTPUT_WIDENED",
    )
    require(
        isinstance(assignment["attestation_required"], bool),
        "ASSIGNMENT_ATTESTATION_REQUIRED",
    )

    if mode == "SYNTHETIC_OFFLINE":
        require(
            transport == "NONE",
            "SYNTHETIC_ASSIGNMENT_PROVIDER_TRANSPORT_FORBIDDEN",
        )
        require(
            assignment["attestation_required"] is False,
            "SYNTHETIC_ASSIGNMENT_ATTESTATION_FORBIDDEN",
        )
    else:
        require(
            transport != "NONE",
            "LIVE_ASSIGNMENT_PROVIDER_TRANSPORT_REQUIRED",
        )
        require(
            assignment["attestation_required"] is True,
            "LIVE_ASSIGNMENT_ATTESTATION_REQUIRED",
        )

    _nonauthority(assignment["nonauthority"])
    return assignment


def assignment_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
) -> str:
    validate_assignment(task, assignment)
    return sha256_json(assignment)


def _legacy_result_v1(
    result_v2: dict[str, Any],
) -> dict[str, Any]:
    legacy = dict(result_v2)
    legacy.pop("assignment_sha256", None)
    legacy["schema"] = RESULT_SCHEMA
    return legacy


def validate_result_v2_for_assignment(
    task: dict[str, Any],
    assignment: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    require(
        isinstance(result, dict)
        and set(result) == RESULT_V2_KEYS,
        "RESULT_V2_SCHEMA_KEYS",
    )
    require(
        result["schema"] == RESULT_V2_SCHEMA,
        "RESULT_V2_SCHEMA_VERSION",
    )
    _sha256(
        result["assignment_sha256"],
        "RESULT_V2_ASSIGNMENT_SHA256",
    )
    require(
        result["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "RESULT_V2_ASSIGNMENT_SHA256_MISMATCH",
    )

    legacy = _legacy_result_v1(result)
    validate_result_for_task(task, legacy)

    identity = result["model_identity"]
    require(
        identity["provider"]
        == assignment["target_provider"],
        "RESULT_V2_PROVIDER_MISMATCH",
    )
    require(
        identity["model"] == assignment["target_model"],
        "RESULT_V2_MODEL_MISMATCH",
    )
    require(
        identity["role"] == assignment["requested_role"],
        "RESULT_V2_ROLE_MISMATCH",
    )
    require(
        _parse_utc(
            result["produced_at"],
            "RESULT_V2_PRODUCED_AT",
        )
        >= _parse_utc(
            assignment["created_at"],
            "ASSIGNMENT_CREATED_AT",
        ),
        "RESULT_V2_PRODUCED_BEFORE_ASSIGNMENT",
    )
    return result


def result_v2_content_digest(
    task: dict[str, Any],
    assignment: dict[str, Any],
    result: dict[str, Any],
) -> str:
    validate_result_v2_for_assignment(
        task,
        assignment,
        result,
    )
    content = dict(result)
    content.pop("submission_id", None)
    return hashlib.sha256(
        json.dumps(
            content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
