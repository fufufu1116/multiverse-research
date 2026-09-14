from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.model import (
    ResearchContractError,
    require,
    sha256_json,
    validate_result_for_task,
    validate_task,
)

ASSIGNMENT_SCHEMA = "MULTIVERSE_RESEARCH_ASSIGNMENT_v1"
RESULT_SCHEMA_V2 = "MULTIVERSE_RESEARCH_RESULT_v2"
RECEIPT_SCHEMA = "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1"

ASSIGNMENT_KEYS = {
    "schema",
    "assignment_id",
    "task_id",
    "task_sha256",
    "snapshot_id",
    "target",
    "requested_role",
    "adapter_sha256",
    "execution_mode",
    "research_network_access",
    "provider_transport",
    "limits",
    "attestation_required",
    "nonauthority",
}

TARGET_KEYS = {"provider", "model"}
LIMIT_KEYS = {"max_compute_seconds", "max_output_bytes"}
RESULT_V2_EXTRA_KEY = "assignment_sha256"
RECEIPT_KEYS = {
    "schema",
    "task_id",
    "task_sha256",
    "assignment_sha256",
    "submission_id",
    "adapter_sha256",
    "execution_mode",
    "request_started_at",
    "response_received_at",
    "provider_reference_id",
    "observed_provider",
    "observed_model",
    "provider_response_sha256",
    "result_sha256",
    "attestation_state",
    "nonauthority",
}

EXECUTION_MODES = {"SYNTHETIC_OFFLINE", "LIVE_ADVISORY"}
NETWORK_ACCESS = {"NONE", "PUBLIC_READ_ONLY"}
PROVIDER_TRANSPORT = {"DISABLED", "ADVISORY_ONLY"}
ATTESTATION_STATES = {
    "SYNTHETIC_OFFLINE",
    "LIVE_ATTESTED",
    "LIVE_PROVIDER_ID_UNVERIFIED",
}
NONAUTHORITY_KEYS = {
    "adoption",
    "merge",
    "main_mutation",
    "ruleset_mutation",
    "workflow_dispatch_rerun",
    "runtime_activation",
    "provider_effect",
    "production",
    "protected_data",
    "live_business_effect",
    "spend",
}
FORBIDDEN_DYNAMIC_KEY_FRAGMENTS = {
    "credential",
    "password",
    "private_key",
    "secret",
    "access_token",
    "api_key",
}


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", value)),
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
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value)),
        code,
    )
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ResearchContractError(code) from exc


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict) and set(value) == NONAUTHORITY_KEYS,
        "PROVENANCE_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(flag is False, f"PROVENANCE_NONAUTHORITY_NOT_FALSE:{key}")
    return value


def _reject_sensitive_dynamic_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            for fragment in FORBIDDEN_DYNAMIC_KEY_FRAGMENTS:
                require(
                    fragment not in low,
                    f"PROVENANCE_FORBIDDEN_DYNAMIC_KEY:{key}",
                )
            _reject_sensitive_dynamic_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_dynamic_keys(child)


def _network_not_wider(task_network: str, assignment_network: str) -> bool:
    if task_network == "NONE":
        return assignment_network == "NONE"
    return assignment_network in NETWORK_ACCESS


def validate_assignment(
    task: dict[str, Any],
    assignment: dict[str, Any],
) -> dict[str, Any]:
    validate_task(task)
    require(isinstance(assignment, dict), "ASSIGNMENT_OBJECT")
    require(set(assignment) == ASSIGNMENT_KEYS, "ASSIGNMENT_SCHEMA_KEYS")
    require(assignment["schema"] == ASSIGNMENT_SCHEMA, "ASSIGNMENT_SCHEMA_VERSION")

    _identifier(assignment["assignment_id"], "ASSIGNMENT_ID")
    require(assignment["task_id"] == task["task_id"], "ASSIGNMENT_TASK_ID_MISMATCH")
    require(
        assignment["task_sha256"] == sha256_json(task),
        "ASSIGNMENT_TASK_SHA256_MISMATCH",
    )
    require(
        assignment["snapshot_id"] == task["snapshot_id"],
        "ASSIGNMENT_SNAPSHOT_ID_MISMATCH",
    )

    target = assignment["target"]
    require(isinstance(target, dict) and set(target) == TARGET_KEYS, "ASSIGNMENT_TARGET_SCHEMA")
    _identifier(target["provider"], "ASSIGNMENT_PROVIDER")
    _identifier(target["model"], "ASSIGNMENT_MODEL")

    role = _identifier(assignment["requested_role"], "ASSIGNMENT_ROLE")
    require(role in task["requested_roles"], "ASSIGNMENT_ROLE_NOT_REQUESTED")
    _sha256(assignment["adapter_sha256"], "ASSIGNMENT_ADAPTER_SHA256")

    mode = assignment["execution_mode"]
    require(mode in EXECUTION_MODES, "ASSIGNMENT_EXECUTION_MODE")
    network = assignment["research_network_access"]
    require(network in NETWORK_ACCESS, "ASSIGNMENT_NETWORK_ACCESS")
    require(
        _network_not_wider(task["constraints"]["network_access"], network),
        "ASSIGNMENT_NETWORK_WIDENING",
    )

    transport = assignment["provider_transport"]
    require(transport in PROVIDER_TRANSPORT, "ASSIGNMENT_PROVIDER_TRANSPORT")
    limits = assignment["limits"]
    require(isinstance(limits, dict) and set(limits) == LIMIT_KEYS, "ASSIGNMENT_LIMIT_SCHEMA")
    require(
        isinstance(limits["max_compute_seconds"], int)
        and 1 <= limits["max_compute_seconds"] <= task["constraints"]["max_compute_seconds"],
        "ASSIGNMENT_COMPUTE_WIDENING",
    )
    require(
        isinstance(limits["max_output_bytes"], int)
        and 1 <= limits["max_output_bytes"] <= task["constraints"]["max_output_bytes"],
        "ASSIGNMENT_OUTPUT_WIDENING",
    )

    if mode == "SYNTHETIC_OFFLINE":
        require(transport == "DISABLED", "SYNTHETIC_PROVIDER_TRANSPORT_FORBIDDEN")
        require(network == "NONE", "SYNTHETIC_NETWORK_MUST_BE_NONE")
        require(assignment["attestation_required"] is False, "SYNTHETIC_ATTESTATION_NOT_REQUIRED")
    else:
        require(transport == "ADVISORY_ONLY", "LIVE_ADVISORY_TRANSPORT_REQUIRED")
        require(assignment["attestation_required"] is True, "LIVE_ADVISORY_ATTESTATION_REQUIRED")
        require(network == "PUBLIC_READ_ONLY", "LIVE_ADVISORY_NETWORK_MUST_BE_PUBLIC_READ_ONLY")

    _nonauthority(assignment["nonauthority"])
    _reject_sensitive_dynamic_keys(assignment)
    return assignment


def validate_result_v2(
    task: dict[str, Any],
    assignment: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    validate_assignment(task, assignment)
    require(isinstance(result, dict), "RESULT_V2_OBJECT")
    require(result.get("schema") == RESULT_SCHEMA_V2, "RESULT_V2_SCHEMA_VERSION")
    require(RESULT_V2_EXTRA_KEY in result, "RESULT_V2_ASSIGNMENT_SHA256_REQUIRED")

    legacy = dict(result)
    legacy["schema"] = "MULTIVERSE_RESEARCH_RESULT_v1"
    assignment_sha = legacy.pop(RESULT_V2_EXTRA_KEY)
    validate_result_for_task(task, legacy)

    require(
        assignment_sha == sha256_json(assignment),
        "RESULT_V2_ASSIGNMENT_SHA256_MISMATCH",
    )
    identity = result["model_identity"]
    require(identity["provider"] == assignment["target"]["provider"], "RESULT_V2_PROVIDER_MISMATCH")
    require(identity["model"] == assignment["target"]["model"], "RESULT_V2_MODEL_MISMATCH")
    require(identity["role"] == assignment["requested_role"], "RESULT_V2_ROLE_MISMATCH")
    _reject_sensitive_dynamic_keys(result)
    return result


def validate_execution_receipt(
    task: dict[str, Any],
    assignment: dict[str, Any],
    result: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    validate_result_v2(task, assignment, result)
    require(isinstance(receipt, dict), "RECEIPT_OBJECT")
    require(set(receipt) == RECEIPT_KEYS, "RECEIPT_SCHEMA_KEYS")
    require(receipt["schema"] == RECEIPT_SCHEMA, "RECEIPT_SCHEMA_VERSION")
    require(receipt["task_id"] == task["task_id"], "RECEIPT_TASK_ID_MISMATCH")
    require(receipt["task_sha256"] == sha256_json(task), "RECEIPT_TASK_SHA256_MISMATCH")
    require(
        receipt["assignment_sha256"] == sha256_json(assignment),
        "RECEIPT_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(receipt["submission_id"] == result["submission_id"], "RECEIPT_SUBMISSION_ID_MISMATCH")
    require(receipt["adapter_sha256"] == assignment["adapter_sha256"], "RECEIPT_ADAPTER_SHA256_MISMATCH")
    require(receipt["execution_mode"] == assignment["execution_mode"], "RECEIPT_EXECUTION_MODE_MISMATCH")
    _sha256(receipt["provider_response_sha256"], "RECEIPT_PROVIDER_RESPONSE_SHA256")
    require(receipt["result_sha256"] == sha256_json(result), "RECEIPT_RESULT_SHA256_MISMATCH")

    started = _parse_utc(receipt["request_started_at"], "RECEIPT_REQUEST_STARTED_AT")
    received = _parse_utc(receipt["response_received_at"], "RECEIPT_RESPONSE_RECEIVED_AT")
    task_created = _parse_utc(task["created_at"], "TASK_CREATED_AT")
    require(started >= task_created, "RECEIPT_STARTED_BEFORE_TASK")
    require(received >= started, "RECEIPT_RESPONSE_BEFORE_REQUEST")

    state = receipt["attestation_state"]
    require(state in ATTESTATION_STATES, "RECEIPT_ATTESTATION_STATE")
    provider_ref = receipt["provider_reference_id"]
    require(provider_ref is None or isinstance(provider_ref, str), "RECEIPT_PROVIDER_REFERENCE_ID")
    if isinstance(provider_ref, str):
        require(0 < len(provider_ref) <= 512, "RECEIPT_PROVIDER_REFERENCE_ID")

    expected_provider = assignment["target"]["provider"]
    expected_model = assignment["target"]["model"]
    require(isinstance(receipt["observed_provider"], str), "RECEIPT_OBSERVED_PROVIDER")
    require(isinstance(receipt["observed_model"], str), "RECEIPT_OBSERVED_MODEL")

    if assignment["execution_mode"] == "SYNTHETIC_OFFLINE":
        require(state == "SYNTHETIC_OFFLINE", "SYNTHETIC_RECEIPT_ATTESTATION_STATE")
        require(provider_ref is None, "SYNTHETIC_PROVIDER_REFERENCE_FORBIDDEN")
        require(receipt["observed_provider"] == expected_provider, "SYNTHETIC_PROVIDER_MISMATCH")
        require(receipt["observed_model"] == expected_model, "SYNTHETIC_MODEL_MISMATCH")
    else:
        require(state in {"LIVE_ATTESTED", "LIVE_PROVIDER_ID_UNVERIFIED"}, "LIVE_RECEIPT_ATTESTATION_STATE")
        if state == "LIVE_ATTESTED":
            require(provider_ref is not None, "LIVE_ATTESTED_PROVIDER_REFERENCE_REQUIRED")
            require(receipt["observed_provider"] == expected_provider, "LIVE_ATTESTED_PROVIDER_MISMATCH")
            require(receipt["observed_model"] == expected_model, "LIVE_ATTESTED_MODEL_MISMATCH")

    _nonauthority(receipt["nonauthority"])
    _reject_sensitive_dynamic_keys(receipt)
    return receipt


def receipt_authenticates_external_provider(receipt: dict[str, Any]) -> bool:
    return receipt.get("attestation_state") == "LIVE_ATTESTED"
