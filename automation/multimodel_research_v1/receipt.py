from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
    validate_result_v2_for_assignment,
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
    validate_resolved_model_id,
)
from automation.multimodel_research_v1.prompting import (
    validate_provider_neutral_prompt,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)
from automation.multimodel_research_v1.termination import (
    termination_record_sha256,
    validate_termination_record,
)

RECEIPT_SCHEMA = "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1"

RECEIPT_KEYS = {
    "schema",
    "receipt_id",
    "task_sha256",
    "assignment_sha256",
    "request_envelope_sha256",
    "termination_record_sha256",
    "submission_id",
    "observed_provider",
    "observed_model_id",
    "provider_response_id",
    "provider_response_sha256",
    "result_sha256",
    "adapter_sha256",
    "request_started_at",
    "response_received_at",
    "receipt_created_at",
    "attestation_state",
    "nonauthority",
}

ATTESTATION_STATES = {
    "LIVE_ATTESTED",
    "LIVE_PROVIDER_ID_UNVERIFIED",
}

TERMINATION_TO_RESULT_STATUS = {
    "COMPLETED": "COMPLETED",
    "PROVIDER_REFUSED": "REFUSED",
    "PROVIDER_BLOCKED": "REFUSED",
    "PROVIDER_TRUNCATED": "INFRA_FAILURE",
    "PROVIDER_EMPTY": "INFRA_FAILURE",
    "TRANSPORT_FAILURE": "INFRA_FAILURE",
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
        raise RuntimeError(code) from exc


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "RECEIPT_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"RECEIPT_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_execution_receipt(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    termination_record: dict[str, Any],
    result: dict[str, Any],
    receipt: dict[str, Any],
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
    validate_termination_record(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        termination_record,
    )
    validate_result_v2_for_assignment(
        task,
        assignment,
        result,
    )

    require(
        isinstance(receipt, dict)
        and set(receipt) == RECEIPT_KEYS,
        "RECEIPT_SCHEMA_KEYS",
    )
    require(
        receipt["schema"] == RECEIPT_SCHEMA,
        "RECEIPT_SCHEMA_VERSION",
    )
    _identifier(receipt["receipt_id"], "RECEIPT_ID")
    require(
        receipt["task_sha256"] == sha256_json(task),
        "RECEIPT_TASK_SHA256_MISMATCH",
    )
    require(
        receipt["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "RECEIPT_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        receipt["request_envelope_sha256"]
        == request_envelope_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
        ),
        "RECEIPT_REQUEST_SHA256_MISMATCH",
    )
    require(
        receipt["termination_record_sha256"]
        == termination_record_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            request_envelope,
            termination_record,
        ),
        "RECEIPT_TERMINATION_SHA256_MISMATCH",
    )
    require(
        receipt["submission_id"] == result["submission_id"],
        "RECEIPT_SUBMISSION_ID_MISMATCH",
    )
    require(
        receipt["observed_provider"]
        == assignment["target_provider"],
        "RECEIPT_PROVIDER_MISMATCH",
    )

    state = receipt["attestation_state"]
    require(
        state in ATTESTATION_STATES,
        "RECEIPT_ATTESTATION_STATE",
    )
    observed_model_id = receipt["observed_model_id"]
    if state == "LIVE_ATTESTED":
        validate_resolved_model_id(
            task,
            assignment,
            model_target_policy,
            observed_model_id,
        )
    else:
        require(
            observed_model_id is None
            or (
                isinstance(observed_model_id, str)
                and bool(observed_model_id)
            ),
            "RECEIPT_OBSERVED_MODEL_ID",
        )

    require(
        receipt["provider_response_id"]
        == termination_record["provider_response_id"],
        "RECEIPT_PROVIDER_RESPONSE_ID_MISMATCH",
    )
    _sha256(
        receipt["provider_response_sha256"],
        "RECEIPT_PROVIDER_RESPONSE_SHA256",
    )
    require(
        receipt["result_sha256"] == sha256_json(result),
        "RECEIPT_RESULT_SHA256_MISMATCH",
    )
    require(
        receipt["adapter_sha256"]
        == assignment["adapter_sha256"],
        "RECEIPT_ADAPTER_SHA256_MISMATCH",
    )

    request_started = _parse_utc(
        receipt["request_started_at"],
        "RECEIPT_REQUEST_STARTED_AT",
    )
    response_received = _parse_utc(
        receipt["response_received_at"],
        "RECEIPT_RESPONSE_RECEIVED_AT",
    )
    receipt_created = _parse_utc(
        receipt["receipt_created_at"],
        "RECEIPT_CREATED_AT",
    )
    require(
        request_started
        >= _parse_utc(
            request_envelope["created_at"],
            "REQUEST_CREATED_AT",
        ),
        "RECEIPT_REQUEST_STARTED_BEFORE_ENVELOPE",
    )
    require(
        response_received >= request_started,
        "RECEIPT_RESPONSE_BEFORE_REQUEST_STARTED",
    )
    require(
        response_received
        == _parse_utc(
            termination_record["response_received_at"],
            "TERMINATION_RESPONSE_RECEIVED_AT",
        ),
        "RECEIPT_RESPONSE_TIME_MISMATCH",
    )
    result_produced = _parse_utc(
        result["produced_at"],
        "RESULT_V2_PRODUCED_AT",
    )
    require(
        result_produced >= response_received,
        "RECEIPT_RESULT_BEFORE_RESPONSE",
    )
    require(
        receipt_created >= result_produced,
        "RECEIPT_CREATED_BEFORE_RESULT",
    )

    expected_status = TERMINATION_TO_RESULT_STATUS[
        termination_record["normalized_state"]
    ]
    require(
        result["status"] == expected_status,
        "RECEIPT_TERMINATION_RESULT_STATUS_MISMATCH",
    )

    _nonauthority(receipt["nonauthority"])
    return receipt


def execution_receipt_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    termination_record: dict[str, Any],
    result: dict[str, Any],
    receipt: dict[str, Any],
) -> str:
    validate_execution_receipt(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        request_envelope,
        termination_record,
        result,
        receipt,
    )
    return sha256_json(receipt)
