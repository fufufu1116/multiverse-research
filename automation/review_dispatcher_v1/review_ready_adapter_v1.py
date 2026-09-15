from __future__ import annotations

from typing import Any

PACKAGE_PASS = "PACKAGE_READY_NONAUTHORITY"
TRANSPORT_PASS = "TRANSPORT_READY_NONAUTHORITY"
READY = "READY_FOR_CONTROL_AUTHORITY_EVALUATION"
FAIL = "REVIEW_READY_ADAPTER_FAIL_CLOSED"


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": "MULTIVERSE_REVIEW_READY_ADAPTER_RESULT_v1",
        "state": FAIL,
        "reason": reason,
        "authority_created": False,
        "owner_marker_created": False,
        "runtime_authority": False,
    }


def combine(package_result: dict[str, Any], transport_result: dict[str, Any]) -> dict[str, Any]:
    """Combine two NONAUTHORITY validations. Never creates an Owner request or authority."""
    if package_result.get("state") != PACKAGE_PASS:
        return _fail("PACKAGE_NOT_READY")
    if transport_result.get("state") != TRANSPORT_PASS:
        return _fail("TRANSPORT_NOT_READY")
    for result in (package_result, transport_result):
        if result.get("authority_created") is not False:
            return _fail("AUTHORITY_FLAG_NOT_FALSE")
        if result.get("owner_marker_created") is not False:
            return _fail("OWNER_MARKER_FLAG_NOT_FALSE")
        if result.get("runtime_authority") is not False:
            return _fail("RUNTIME_FLAG_NOT_FALSE")
    return {
        "schema": "MULTIVERSE_REVIEW_READY_ADAPTER_RESULT_v1",
        "state": READY,
        "package_idempotency_key": package_result.get("idempotency_key"),
        "transport_binding": [transport_result.get(k) for k in ("repo", "pr", "head", "tree", "base", "main")],
        "authority_created": False,
        "owner_marker_created": False,
        "runtime_authority": False,
    }


def same_identity_payload_consistent(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """Fail-closed helper for queue/storage layers: same stable identity may not change ready_sha256."""
    stable = ("lane_id", "candidate_id", "candidate_head", "package_blob_sha")
    same = all(first.get(k) == second.get(k) for k in stable)
    if not same:
        return True
    return first.get("ready_sha256") == second.get("ready_sha256")
