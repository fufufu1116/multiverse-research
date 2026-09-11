from __future__ import annotations

import copy
from typing import Any

from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    sha256_json,
    validate_result,
)

from .multiverse_bridge import (
    OpportunityBridgeError,
    sha256_json as bridge_sha256_json,
    validate_multiverse_review_packet,
)

FEEDBACK_SCHEMA = "MULTIVERSE_OPPORTUNITY_REVIEW_FEEDBACK_v1"
SEVERITY_ORDER = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def _verify_finding_evidence(task: dict[str, Any], result: dict[str, Any]) -> None:
    manifest = {
        (item["primitive"], item["ref"]): item["sha256"]
        for item in task["evidence_manifest"]
    }
    allowed = set(task["allowed_primitives"])
    for finding in result["findings"]:
        evidence = finding["evidence"]
        primitive = evidence["primitive"]
        ref = evidence["ref"]
        if primitive not in allowed:
            raise OpportunityBridgeError("review finding used a primitive not allowed by task")
        key = (primitive, ref)
        if key not in manifest:
            raise OpportunityBridgeError("review finding cited evidence outside frozen manifest")
        if evidence["sha256"] != manifest[key]:
            raise OpportunityBridgeError("review finding evidence hash mismatch")


def ingest_multiverse_review_result(
    *,
    review_packet: dict[str, Any],
    research_result: dict[str, Any],
) -> dict[str, Any]:
    """Convert one existing MULTIVERSE research result into advisory OE feedback.

    A supportive review is never translated into execution/adoption authority. The
    return path only records challenges, uncertainty and evidence-bound findings.
    """
    validate_multiverse_review_packet(review_packet)
    validate_result(research_result)

    task = review_packet["research_task"]
    if research_result["task_id"] != task["task_id"]:
        raise OpportunityBridgeError("review result task_id mismatch")
    if research_result["snapshot_id"] != task["snapshot_id"]:
        raise OpportunityBridgeError("review result snapshot_id mismatch")
    if research_result["task_sha256"] != sha256_json(task):
        raise OpportunityBridgeError("review result task hash mismatch")
    if research_result["nonauthority"] != _nonauthority():
        raise OpportunityBridgeError("review result cannot grant authority")

    if research_result["status"] != "COMPLETED":
        feedback = {
            "schema": FEEDBACK_SCHEMA,
            "case_id": review_packet["case_id"],
            "task_id": task["task_id"],
            "submission_id": research_result["submission_id"],
            "model_identity": copy.deepcopy(research_result["model_identity"]),
            "review_state": "REVIEW_UNAVAILABLE",
            "support_count": 0,
            "oppose_count": 0,
            "unknown_count": 0,
            "max_severity": None,
            "findings": [],
            "uncertainty_factors": copy.deepcopy(research_result["uncertainty_factors"]),
            "authority": _nonauthority(),
            "note": "Advisory only. Non-completed review cannot advance an opportunity.",
        }
        feedback["feedback_sha256"] = bridge_sha256_json(feedback)
        return feedback

    _verify_finding_evidence(task, research_result)

    findings = copy.deepcopy(research_result["findings"])
    support_count = sum(item["position"] == "SUPPORT" for item in findings)
    oppose_count = sum(item["position"] == "OPPOSE" for item in findings)
    unknown_count = sum(item["position"] == "UNKNOWN" for item in findings)
    max_severity = max(
        (item["severity"] for item in findings),
        key=lambda value: SEVERITY_ORDER[value],
        default=None,
    )

    severe_opposition = any(
        item["position"] == "OPPOSE" and item["severity"] in {"HIGH", "CRITICAL"}
        for item in findings
    )
    if severe_opposition:
        state = "CHALLENGE_REQUIRED"
    elif oppose_count or unknown_count or research_result["uncertainty_factors"]:
        state = "MORE_EVIDENCE"
    else:
        state = "NO_BLOCKER_FOUND_YET"

    feedback = {
        "schema": FEEDBACK_SCHEMA,
        "case_id": review_packet["case_id"],
        "task_id": task["task_id"],
        "submission_id": research_result["submission_id"],
        "model_identity": copy.deepcopy(research_result["model_identity"]),
        "review_state": state,
        "support_count": support_count,
        "oppose_count": oppose_count,
        "unknown_count": unknown_count,
        "max_severity": max_severity,
        "findings": findings,
        "uncertainty_factors": copy.deepcopy(research_result["uncertainty_factors"]),
        "authority": _nonauthority(),
        "note": (
            "Advisory only. NO_BLOCKER_FOUND_YET is not approval; formal testing, "
            "Lab/Auditor gates and Owner authority remain external to this bridge."
        ),
    }
    feedback["feedback_sha256"] = bridge_sha256_json(feedback)
    return feedback
