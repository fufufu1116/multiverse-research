from __future__ import annotations

import json
import re
from typing import Any

from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    AUDITOR_LOGIN,
    ReviewContractError,
    github_comment_id,
    lane_result_comment_trusted,
    t2_marker,
)

T2_RECEIPT_SCHEMA = "MULTIVERSE_FIXED_T2_PUBLISH_RECEIPT_v1"


def _json_block(body: str) -> dict[str, Any]:
    fence = r"\x60\x60\x60"
    match = re.search(fence + r"json\s*(\{.*?\})\s*" + fence, body, re.S)
    if match is None:
        raise ReviewContractError("T2_JSON_BLOCK_MISSING")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ReviewContractError("T2_JSON_OBJECT_REQUIRED")
    return payload


def recover_t2_receipt(
    *,
    job: dict[str, Any],
    auditor_comment_id: int,
    expected_t2_artifact: dict[str, Any],
    canonical_t2_comment: dict[str, Any],
) -> dict[str, Any]:
    if not lane_result_comment_trusted(canonical_t2_comment, "AUDITOR"):
        raise ReviewContractError("T2_RECOVERY_PRODUCER_NOT_TRUSTED")

    marker = t2_marker(
        job["request_id"],
        job["head"],
        auditor_comment_id,
        job["request_sha256"],
    )
    body = canonical_t2_comment.get("body") or ""
    if marker not in body:
        raise ReviewContractError("T2_RECOVERY_MARKER_MISMATCH")

    published = _json_block(body)
    if published != expected_t2_artifact:
        raise ReviewContractError("T2_RECOVERY_ARTIFACT_DRIFT")

    exact = {
        "request_id": job["request_id"],
        "request_sha256": job["request_sha256"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "auditor_pass_comment": auditor_comment_id,
    }
    for key, expected in exact.items():
        if expected_t2_artifact.get(key) != expected:
            raise ReviewContractError(f"T2_RECOVERY_{key.upper()}_MISMATCH")

    if expected_t2_artifact.get("gate") != "T2":
        raise ReviewContractError("T2_RECOVERY_GATE_MISMATCH")
    if expected_t2_artifact.get("verdict") != "PASS":
        raise ReviewContractError("T2_RECOVERY_NOT_PASS")
    if expected_t2_artifact.get("auditor_producer") != AUDITOR_LOGIN:
        raise ReviewContractError("T2_RECOVERY_AUDITOR_LOGIN_MISMATCH")
    if expected_t2_artifact.get("auditor_app_id") != AUDITOR_APP_ID:
        raise ReviewContractError("T2_RECOVERY_AUDITOR_APP_MISMATCH")

    return {
        "schema": T2_RECEIPT_SCHEMA,
        "request_id": job["request_id"],
        "request_sha256": job["request_sha256"],
        "auditor_comment_id": auditor_comment_id,
        "t2_comment_id": github_comment_id(
            canonical_t2_comment,
            "PUBLISHED_T2_COMMENT_ID",
        ),
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "verdict": "PASS",
        "recovered": True,
    }
