from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.assignment import (
    RESULT_V2_SCHEMA,
    assignment_sha256,
    validate_assignment,
)
from automation.multimodel_research_v1.model import (
    POSITIONS,
    RESULT_STATUSES,
    SEVERITIES,
    require,
    sha256_json,
    validate_task,
)

_SHA256_PATTERN = "^[0-9a-f]{64}$"
_TIME_PATTERN = (
    "^\\d{4}-\\d{2}-\\d{2}T"
    "\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?Z$"
)


def _string(*, max_length: int = 20000) -> dict[str, Any]:
    return {
        "type": "string",
        "minLength": 1,
        "maxLength": max_length,
    }


def _exact_string(value: str) -> dict[str, Any]:
    return {"type": "string", "enum": [value]}


def build_result_v2_response_schema(
    task: dict[str, Any],
    assignment: dict[str, Any],
) -> dict[str, Any]:
    validate_task(task)
    validate_assignment(task, assignment)

    evidence = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "primitive": {
                "type": "string",
                "enum": sorted(task["allowed_primitives"]),
            },
            "ref": _string(max_length=4000),
            "sha256": {
                "type": "string",
                "pattern": _SHA256_PATTERN,
            },
        },
        "required": ["primitive", "ref", "sha256"],
    }

    finding = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "finding_id": _string(max_length=128),
            "claim_key": _string(max_length=128),
            "position": {
                "type": "string",
                "enum": sorted(POSITIONS),
            },
            "severity": {
                "type": "string",
                "enum": sorted(SEVERITIES),
            },
            "assertion": _string(),
            "evidence": evidence,
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "uncertainty": _string(),
            "recommendation": _string(),
            "validation_plan": _string(),
        },
        "required": [
            "finding_id",
            "claim_key",
            "position",
            "severity",
            "assertion",
            "evidence",
            "confidence",
            "uncertainty",
            "recommendation",
            "validation_plan",
        ],
    }

    nonauthority_properties = {
        key: {"type": "boolean", "enum": [False]}
        for key in sorted(task["nonauthority"])
    }

    properties = {
        "schema": _exact_string(RESULT_V2_SCHEMA),
        "task_id": _exact_string(task["task_id"]),
        "task_sha256": _exact_string(sha256_json(task)),
        "submission_id": _string(max_length=128),
        "snapshot_id": _exact_string(task["snapshot_id"]),
        "produced_at": {
            "type": "string",
            "pattern": _TIME_PATTERN,
        },
        "model_identity": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "provider": _exact_string(
                    assignment["target_provider"]
                ),
                "model": _exact_string(
                    assignment["target_model"]
                ),
                "role": _exact_string(
                    assignment["requested_role"]
                ),
            },
            "required": ["provider", "model", "role"],
        },
        "status": {
            "type": "string",
            "enum": sorted(RESULT_STATUSES),
        },
        "findings": {
            "type": "array",
            "maxItems": task["constraints"]["max_findings"],
            "items": finding,
        },
        "uncertainty_factors": {
            "type": "array",
            "maxItems": 100,
            "items": _string(max_length=4000),
        },
        "nonauthority": {
            "type": "object",
            "additionalProperties": False,
            "properties": nonauthority_properties,
            "required": sorted(nonauthority_properties),
        },
        "assignment_sha256": _exact_string(
            assignment_sha256(task, assignment)
        ),
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": [
            "schema",
            "task_id",
            "task_sha256",
            "submission_id",
            "snapshot_id",
            "produced_at",
            "model_identity",
            "status",
            "findings",
            "uncertainty_factors",
            "nonauthority",
            "assignment_sha256",
        ],
    }


def validate_result_v2_response_schema(
    task: dict[str, Any],
    assignment: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(response_schema, dict),
        "RESULT_V2_RESPONSE_SCHEMA_OBJECT",
    )
    expected = build_result_v2_response_schema(
        task,
        assignment,
    )
    require(
        response_schema == expected,
        "RESULT_V2_RESPONSE_SCHEMA_EXACT_MISMATCH",
    )
    return response_schema


def result_v2_response_schema_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    response_schema: dict[str, Any],
) -> str:
    validate_result_v2_response_schema(
        task,
        assignment,
        response_schema,
    )
    return sha256_json(response_schema)
