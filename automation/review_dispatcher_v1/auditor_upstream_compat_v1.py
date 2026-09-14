from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1.model_legacy_v1 import (
    ReviewContractError,
    sha256_hex,
)

LEGACY_KEYS = {"lab_pass_comment", "lab_request_sha256", "t1_comment"}
CURRENT_MINIMAL_KEYS = {"lab_result_comment"}


def normalize_auditor_upstream_v1(upstream: Any) -> dict[str, Any]:
    """Normalize the one known historical/current Auditor upstream shape.

    This does not invent missing authority. Legacy canonical requests pass
    through unchanged. The current minimal shape is admitted only when it is
    exactly {lab_result_comment: positive int}; downstream review then derives
    and verifies the exact latest LAB request/result binding and T1 evidence
    from durable comments rather than trusting request-supplied duplicates.
    Any other shape fails closed.
    """
    if not isinstance(upstream, dict):
        raise ReviewContractError("UPSTREAM_OBJECT")

    keys = set(upstream)
    if keys == LEGACY_KEYS:
        if not (
            isinstance(upstream["lab_pass_comment"], int)
            and not isinstance(upstream["lab_pass_comment"], bool)
            and upstream["lab_pass_comment"] > 0
        ):
            raise ReviewContractError("AUDITOR_UPSTREAM_LAB_PASS_COMMENT")
        if not (
            isinstance(upstream["t1_comment"], int)
            and not isinstance(upstream["t1_comment"], bool)
            and upstream["t1_comment"] > 0
        ):
            raise ReviewContractError("AUDITOR_UPSTREAM_T1_COMMENT")
        if not sha256_hex(upstream["lab_request_sha256"]):
            raise ReviewContractError("AUDITOR_UPSTREAM_LAB_REQUEST_SHA256")
        return dict(upstream)

    if keys == CURRENT_MINIMAL_KEYS:
        value = upstream["lab_result_comment"]
        if not (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        ):
            raise ReviewContractError("AUDITOR_UPSTREAM_LAB_RESULT_COMMENT")
        return {"lab_result_comment": value}

    raise ReviewContractError("AUDITOR_UPSTREAM_SCHEMA")
