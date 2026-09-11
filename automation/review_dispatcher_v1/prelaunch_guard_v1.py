from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from automation.review_dispatcher_v1.model import lane_result_comment_trusted, result_marker

LEASE_SCHEMA = "MULTIVERSE_BUILD_LAUNCH_LEASE_v1"
LEASE_PREFIX = "refs/tags/multiverse-build-launch-leases/v1"


def launch_key(*, repo: str, pr: int, lane: str, request_id: str, request_sha256: str, head: str, main: str) -> str:
    payload = {"head": head, "lane": lane, "main": main, "pr": pr, "repo": repo, "request_id": request_id, "request_sha256": request_sha256}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def launch_lease_ref(**binding: Any) -> str:
    lane = str(binding["lane"]).lower()
    return f"{LEASE_PREFIX}/{lane}/{launch_key(**binding)}"


def exact_trusted_result_ids(comments: list[dict[str, Any]], *, lane: str, request_id: str, head: str, request_comment: int, request_sha256: str) -> list[int]:
    marker = result_marker(request_id, head, request_comment, request_sha256)
    return [int(c["id"]) for c in comments if marker in (c.get("body") or "") and lane_result_comment_trusted(c, lane)]


def prelaunch_decision(*, comments: list[dict[str, Any]], lane: str, request_id: str, head: str, request_comment: int, request_sha256: str, gate_request_sha256: str, current_request_sha256: str, lease_exists: bool) -> dict[str, Any]:
    """Mandatory final Fresh check immediately before telling Owner to launch.

    This function is read-only. Atomic lease acquisition must be provider-enforced by
    create-only creation of launch_lease_ref(); an existing ref means another launch
    already owns this exact request. Different lane/request bindings produce different refs.
    """
    if gate_request_sha256 != current_request_sha256:
        return {"decision": "BLOCK", "reason": "STALE_GATE"}
    results = exact_trusted_result_ids(comments, lane=lane, request_id=request_id, head=head, request_comment=request_comment, request_sha256=request_sha256)
    if results:
        return {"decision": "COMPLETE", "reason": "EXACT_RESULT_ALREADY_EXISTS", "result_ids": results}
    if lease_exists:
        return {"decision": "BLOCK", "reason": "EXACT_REQUEST_LAUNCH_ALREADY_LEASED"}
    return {"decision": "LEASE_THEN_LAUNCH", "reason": "FRESH_NO_RESULT_NO_LEASE"}


def lease_payload(**binding: Any) -> dict[str, Any]:
    return {"schema": LEASE_SCHEMA, "binding": dict(binding), "launch_key": launch_key(**binding)}
