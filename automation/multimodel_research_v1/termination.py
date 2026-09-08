from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
)
from automation.multimodel_research_v1.capability import (
    validate_capability_policy,
)
from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    require,
    sha256_json,
)
from automation.multimodel_research_v1.model_target import (
    validate_model_target_policy,
)
from automation.multimodel_research_v1.prompting import (
    validate_provider_neutral_prompt,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)

TERMINATION_SCHEMA = "MULTIVERSE_PROVIDER_TERMINATION_RECORD_v1"

TERMINATION_KEYS = {
    "schema",
    "assignment_sha256",
    "request_envelope_sha256",
    "provider_response_id",
    "native_reason",
    "normalized_state",
    "input_tokens",
    "output_tokens",
    "usage_metadata_sha256",
    "response_received_at",
    "nonauthority",
}

NORMALIZED_STATES = {
    "COMPLETED",
    "PROVIDER_REFUSED",
    "PROVIDER_BLOCKED",
    "PROVIDER_TRUNCATED",
    "PROVIDER_EMPTY",
    "TRANSPORT_FAILURE",
}


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
        raise RuntimeError(code) from exc


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "TERMINATION_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"TERMINATION_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_termination_record(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    record: dict[str, Any],
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
    validate_request_envelope(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
    )

    require(
        isinstance(record, dict)
        and set(record) == TERMINATION_KEYS,
        "TERMINATION_SCHEMA_KEYS",
    )
    require(
        record["schema"] == TERMINATION_SCHEMA,
        "TERMINATION_SCHEMA_VERSION",
    )
    require(
        record["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "TERMINATION_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        record["request_envelope_sha256"]
        == request_envelope_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
        ),
        "TERMINATION_REQUEST_SHA256_MISMATCH",
    )

    state = record["normalized_state"]
    require(
        state in NORMALIZED_STATES,
        "TERMINATION_NORMALIZED_STATE",
    )
    _text(
        record["native_reason"],
        "TERMINATION_NATIVE_REASON",
    )

    response_id = record["provider_response_id"]
    if state == "TRANSPORT_FAILURE":
        require(
            response_id is None
            or (
                isinstance(response_id, str)
                and bool(response_id)
            ),
            "TERMINATION_PROVIDER_RESPONSE_ID",
        )
    else:
        _text(
            response_id,
            "TERMINATION_PROVIDER_RESPONSE_ID",
        )

    for key in ("input_tokens", "output_tokens"):
        require(
            isinstance(record[key], int)
            and not isinstance(record[key], bool)
            and record[key] >= 0,
            f"TERMINATION_USAGE:{key}",
        )

    _sha256(
        record["usage_metadata_sha256"],
        "TERMINATION_USAGE_METADATA_SHA256",
    )
    require(
        _parse_utc(
            record["response_received_at"],
            "TERMINATION_RESPONSE_RECEIVED_AT",
        )
        >= _parse_utc(
            request_envelope["created_at"],
            "REQUEST_CREATED_AT",
        ),
        "TERMINATION_RESPONSE_BEFORE_REQUEST",
    )
    _nonauthority(record["nonauthority"])
    return record


def termination_record_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_termination_record(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        record,
    )
    return sha256_json(record)
