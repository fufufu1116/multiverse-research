from __future__ import annotations

import json
import re
from typing import Any

from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    AUDITOR_LOGIN,
    LAB_APP_ID,
    LAB_LOGIN,
    ReviewContractError,
    github_comment_id,
    lane_result_comment_trusted,
    result_marker,
)

RECEIPT_SCHEMA = "MULTIVERSE_FIXED_REVIEW_PUBLISH_RECEIPT_v1"


def _json_block(body: str) -> dict[str, Any]:
    fence = r"\x60\x60\x60"
    match = re.search(fence + r"json\s*(\{.*?\})\s*" + fence, body, re.S)
    if match is None:
        raise ReviewContractError("RESULT_JSON_BLOCK_MISSING")
    payload = json.loads(match.group(1))
    if not isinstance(payload, dict):
        raise ReviewContractError("RESULT_JSON_OBJECT_REQUIRED")
    return payload


def recover_publish_receipt(
    *,
    job: dict[str, Any],
    artifact: dict[str, Any],
    canonical_result_comment: dict[str, Any],
) -> dict[str, Any]:
    lane = job["lane"]
    if lane == "LAB":
        expected_login = LAB_LOGIN
        expected_app_id = LAB_APP_ID
    elif lane == "AUDITOR":
        expected_login = AUDITOR_LOGIN
        expected_app_id = AUDITOR_APP_ID
    else:
        raise ReviewContractError("LANE_UNKNOWN")

    if not lane_result_comment_trusted(canonical_result_comment, lane):
        raise ReviewContractError("RECOVERY_RESULT_PRODUCER_NOT_TRUSTED")

    marker = result_marker(
        job["request_id"],
        job["head"],
        job["request_comment"],
        job["request_sha256"],
    )
    body = canonical_result_comment.get("body") or ""
    if marker not in body:
        raise ReviewContractError("RECOVERY_RESULT_MARKER_MISMATCH")

    published_artifact = _json_block(body)
    if published_artifact != artifact:
        raise ReviewContractError("RECOVERY_RESULT_ARTIFACT_DRIFT")

    exact = {
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
    }
    for key, expected in exact.items():
        if artifact.get(key) != expected:
            raise ReviewContractError(f"RECOVERY_ARTIFACT_{key.upper()}_MISMATCH")

    if artifact.get("verdict") != "PASS" or artifact.get("findings") != []:
        raise ReviewContractError("RECOVERY_ARTIFACT_NOT_CLEAN_PASS")

    return {
        "schema": RECEIPT_SCHEMA,
        "lane": lane,
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "published_comment_id": github_comment_id(
            canonical_result_comment,
            "PUBLISHED_COMMENT_ID",
        ),
        "published_by": expected_login,
        "github_app_id": expected_app_id,
        "verdict": "PASS",
        "recovered": True,
    }
