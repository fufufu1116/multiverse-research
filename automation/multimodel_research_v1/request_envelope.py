from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
)
from automation.multimodel_research_v1.capability import (
    capability_policy_sha256,
    validate_capability_policy,
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
    provider_neutral_prompt_sha256,
    validate_provider_neutral_prompt,
)

REQUEST_ENVELOPE_SCHEMA = "MULTIVERSE_PROVIDER_REQUEST_ENVELOPE_v1"

REQUEST_ENVELOPE_KEYS = {
    "schema",
    "request_id",
    "task_sha256",
    "assignment_sha256",
    "model_target_policy_sha256",
    "capability_policy_sha256",
    "provider_neutral_prompt_sha256",
    "provider_transport_policy_ref",
    "created_at",
    "objective_classification",
    "classification_evidence_ref",
    "classification_evidence_sha256",
    "egress_items",
    "outbound_payload_sha256",
    "nonauthority",
}

EGRESS_ITEM_KEYS = {
    "primitive",
    "ref",
    "sha256",
    "classification",
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
        "REQUEST_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"REQUEST_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_request_envelope(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    envelope: dict[str, Any],
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

    require(
        assignment["execution_mode"] == "LIVE_ADVISORY",
        "REQUEST_REQUIRES_LIVE_ASSIGNMENT",
    )
    require(
        isinstance(envelope, dict)
        and set(envelope) == REQUEST_ENVELOPE_KEYS,
        "REQUEST_ENVELOPE_SCHEMA_KEYS",
    )
    require(
        envelope["schema"] == REQUEST_ENVELOPE_SCHEMA,
        "REQUEST_ENVELOPE_SCHEMA_VERSION",
    )
    _identifier(
        envelope["request_id"],
        "REQUEST_ENVELOPE_ID",
    )
    require(
        envelope["task_sha256"] == sha256_json(task),
        "REQUEST_TASK_SHA256_MISMATCH",
    )
    require(
        envelope["assignment_sha256"]
        == assignment_sha256(task, assignment),
        "REQUEST_ASSIGNMENT_SHA256_MISMATCH",
    )
    require(
        envelope["model_target_policy_sha256"]
        == model_target_policy_sha256(
            task,
            assignment,
            model_target_policy,
        ),
        "REQUEST_MODEL_TARGET_SHA256_MISMATCH",
    )
    require(
        envelope["capability_policy_sha256"]
        == capability_policy_sha256(
            task,
            assignment,
            model_target_policy,
            capability_policy,
        ),
        "REQUEST_CAPABILITY_SHA256_MISMATCH",
    )
    require(
        envelope["provider_neutral_prompt_sha256"]
        == provider_neutral_prompt_sha256(
            task,
            prompt,
        ),
        "REQUEST_PROMPT_SHA256_MISMATCH",
    )
    require(
        prompt["requested_role"]
        == assignment["requested_role"],
        "REQUEST_PROMPT_ROLE_MISMATCH",
    )

    transport = envelope[
        "provider_transport_policy_ref"
    ]
    _identifier(
        transport,
        "REQUEST_PROVIDER_TRANSPORT_POLICY_REF",
    )
    require(
        transport
        == assignment["provider_transport_policy_ref"],
        "REQUEST_PROVIDER_TRANSPORT_POLICY_MISMATCH",
    )
    require(
        transport != "NONE",
        "REQUEST_PROVIDER_TRANSPORT_REQUIRED",
    )

    require(
        _parse_utc(
            envelope["created_at"],
            "REQUEST_CREATED_AT",
        )
        >= _parse_utc(
            assignment["created_at"],
            "ASSIGNMENT_CREATED_AT",
        ),
        "REQUEST_CREATED_BEFORE_ASSIGNMENT",
    )

    require(
        envelope["objective_classification"] == "SYNTHETIC",
        "REQUEST_OBJECTIVE_NOT_SYNTHETIC",
    )
    _text(
        envelope["classification_evidence_ref"],
        "REQUEST_CLASSIFICATION_EVIDENCE_REF",
    )
    _sha256(
        envelope["classification_evidence_sha256"],
        "REQUEST_CLASSIFICATION_EVIDENCE_SHA256",
    )

    egress = envelope["egress_items"]
    require(
        isinstance(egress, list) and bool(egress),
        "REQUEST_EGRESS_ITEMS",
    )
    for item in egress:
        require(
            isinstance(item, dict)
            and set(item) == EGRESS_ITEM_KEYS,
            "REQUEST_EGRESS_ITEM_SCHEMA",
        )
        require(
            item["classification"] == "SYNTHETIC",
            "REQUEST_EGRESS_NOT_SYNTHETIC",
        )
        _sha256(
            item["sha256"],
            "REQUEST_EGRESS_SHA256",
        )

    expected_egress = sorted(
        [
            {
                "primitive": item["primitive"],
                "ref": item["ref"],
                "sha256": item["sha256"],
                "classification": "SYNTHETIC",
            }
            for item in task["evidence_manifest"]
        ],
        key=lambda item: (
            item["primitive"],
            item["ref"],
            item["sha256"],
        ),
    )
    require(
        egress == expected_egress,
        "REQUEST_EGRESS_MANIFEST_MISMATCH",
    )

    _sha256(
        envelope["outbound_payload_sha256"],
        "REQUEST_OUTBOUND_PAYLOAD_SHA256",
    )
    _nonauthority(envelope["nonauthority"])
    return envelope


def request_envelope_sha256(
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    envelope: dict[str, Any],
) -> str:
    validate_request_envelope(
        task,
        assignment,
        model_target_policy,
        capability_policy,
        prompt,
        envelope,
    )
    return sha256_json(envelope)
