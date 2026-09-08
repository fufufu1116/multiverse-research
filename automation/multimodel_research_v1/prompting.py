from __future__ import annotations

import re
from typing import Any

from automation.multimodel_research_v1.model import (
    TASK_SCHEMA_V2,
    require,
    sha256_json,
    validate_task,
)

PROMPT_SCHEMA = "MULTIVERSE_PROVIDER_NEUTRAL_PROMPT_v1"

PROMPT_KEYS = {
    "schema",
    "task_sha256",
    "snapshot_id",
    "requested_role",
    "objective",
    "evidence_manifest",
    "response_schema_sha256",
    "nonauthority",
}


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def build_provider_neutral_prompt(
    task: dict[str, Any],
    requested_role: str,
    response_schema_sha256: str,
) -> dict[str, Any]:
    validate_task(task)
    require(
        task["schema"] == TASK_SCHEMA_V2,
        "PROMPT_REQUIRES_TASK_V2",
    )
    require(
        requested_role in task["requested_roles"],
        "PROMPT_ROLE_NOT_REQUESTED",
    )
    _sha256(
        response_schema_sha256,
        "PROMPT_RESPONSE_SCHEMA_SHA256",
    )

    evidence = sorted(
        [
            {
                "primitive": item["primitive"],
                "ref": item["ref"],
                "sha256": item["sha256"],
                "observed_at": item["observed_at"],
            }
            for item in task["evidence_manifest"]
        ],
        key=lambda item: (
            item["primitive"],
            item["ref"],
            item["sha256"],
            item["observed_at"],
        ),
    )

    return {
        "schema": PROMPT_SCHEMA,
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "requested_role": requested_role,
        "objective": task["objective"],
        "evidence_manifest": evidence,
        "response_schema_sha256": response_schema_sha256,
        "nonauthority": dict(task["nonauthority"]),
    }


def validate_provider_neutral_prompt(
    task: dict[str, Any],
    prompt: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(prompt, dict)
        and set(prompt) == PROMPT_KEYS,
        "PROMPT_SCHEMA_KEYS",
    )
    require(
        prompt["schema"] == PROMPT_SCHEMA,
        "PROMPT_SCHEMA_VERSION",
    )
    expected = build_provider_neutral_prompt(
        task,
        prompt["requested_role"],
        prompt["response_schema_sha256"],
    )
    require(
        prompt == expected,
        "PROMPT_EXACT_BINDING_MISMATCH",
    )
    return prompt


def provider_neutral_prompt_sha256(
    task: dict[str, Any],
    prompt: dict[str, Any],
) -> str:
    validate_provider_neutral_prompt(task, prompt)
    return sha256_json(prompt)
