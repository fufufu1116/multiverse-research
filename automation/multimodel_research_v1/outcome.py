from __future__ import annotations

from typing import Any

REVIEW_OUTCOMES = {
    "PASS",
    "FIX_REQUIRED",
    "INFRA_FAILURE",
}


def classify_review_outcome(
    *,
    candidate_findings: list[str],
    infrastructure_errors: list[str],
    required_review_complete: bool,
) -> dict[str, Any]:
    if candidate_findings:
        outcome = "FIX_REQUIRED"
    elif infrastructure_errors or not required_review_complete:
        outcome = "INFRA_FAILURE"
    else:
        outcome = "PASS"

    return {
        "schema": "MULTIVERSE_REVIEW_OUTCOME_CLASSIFICATION_v1",
        "outcome": outcome,
        "candidate_findings": list(candidate_findings),
        "infrastructure_errors": list(infrastructure_errors),
        "required_review_complete": bool(required_review_complete),
        "authoritative_pass": outcome == "PASS",
    }
