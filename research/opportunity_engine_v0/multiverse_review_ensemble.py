from __future__ import annotations

import copy
from typing import Any

from automation.multimodel_research_v1.aggregator import aggregate_results_v2
from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS

from .multiverse_bridge import (
    OpportunityBridgeError,
    sha256_json,
    validate_multiverse_review_packet,
)
from .multiverse_result_bridge import ingest_multiverse_review_result

ENSEMBLE_SCHEMA = "MULTIVERSE_OPPORTUNITY_REVIEW_ENSEMBLE_v1"
SEVERITY_ORDER = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def _claim_subsystem(claim_key: str) -> str:
    key = claim_key.lower().replace("_", "-")
    mapping = (
        (("competitor", "competition", "incumbent"), "COMPETITION"),
        (("economics", "profit", "payer", "price", "conversion"), "ECONOMICS"),
        (("leverage", "loadout", "automation", "distribution"), "LEVERAGE"),
        (("forecast", "demand-life", "timing", "peak", "decay"), "FORECASTING"),
        (("legal", "safety", "deception"), "LEGAL_SAFETY"),
        (("ai-substitution", "general-ai"), "AI_SUBSTITUTION"),
        (("execution", "owner-burden", "operations", "tactic"), "EXECUTION"),
    )
    for needles, subsystem in mapping:
        if any(needle in key for needle in needles):
            return subsystem
    return "GENERAL_REVIEW"


def _classify_claim(claim: dict[str, Any]) -> dict[str, Any]:
    positions = claim["positions"]
    support = list(positions.get("SUPPORT", []))
    oppose = list(positions.get("OPPOSE", []))
    unknown = list(positions.get("UNKNOWN", []))
    severe_opposition = any(
        item["severity"] in {"HIGH", "CRITICAL"}
        for item in oppose
    )

    if severe_opposition:
        state = "BLOCKING_CHALLENGE"
    elif support and oppose:
        state = "FALSIFICATION_REQUIRED"
    elif oppose or unknown:
        state = "REVISION_OR_MORE_EVIDENCE"
    else:
        state = "NO_BLOCKER_FOUND_YET"

    all_items = support + oppose + unknown
    max_severity = max(
        (item["severity"] for item in all_items),
        key=lambda value: SEVERITY_ORDER[value],
        default=None,
    )

    action_items = []
    for position in ("OPPOSE", "UNKNOWN"):
        for item in positions.get(position, []):
            action_items.append(
                {
                    "position": position,
                    "severity": item["severity"],
                    "confidence": item["confidence"],
                    "provider": item["model_identity"]["provider"],
                    "model": item["model_identity"]["model"],
                    "role": item["model_identity"]["role"],
                    "finding_id": item["finding_id"],
                    "recommendation": item["recommendation"],
                    "validation_plan": item["validation_plan"],
                }
            )
    action_items.sort(
        key=lambda item: (
            -SEVERITY_ORDER[item["severity"]],
            -float(item["confidence"]),
            item["provider"],
            item["model"],
            item["role"],
            item["finding_id"],
        )
    )

    return {
        "claim_key": claim["claim_key"],
        "subsystem": _claim_subsystem(claim["claim_key"]),
        "state": state,
        "max_severity": max_severity,
        "support_count": len(support),
        "oppose_count": len(oppose),
        "unknown_count": len(unknown),
        "cross_provider_divergence": bool(claim.get("cross_provider_divergence")),
        "cross_model_divergence": bool(claim.get("cross_model_divergence")),
        "action_items": action_items,
        "majority_confers_truth": False,
    }


def _next_action(overall_state: str) -> str:
    return {
        "REVIEW_INCOMPLETE": "RESTORE_REVIEW_COVERAGE",
        "CHALLENGE_REQUIRED": "DOWNRANK_AND_RUN_FALSIFICATION",
        "FALSIFICATION_REQUIRED": "RUN_MECHANICAL_FALSIFICATION",
        "MORE_EVIDENCE_OR_REVISION": "RESEARCH_REVISE_AND_REFREEZE",
        "NO_BLOCKER_FOUND_YET": "HOLD_FOR_NEXT_GOVERNED_GATE",
    }[overall_state]


def aggregate_opportunity_reviews(
    *,
    review_packet: dict[str, Any],
    research_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate multiple MULTIVERSE reviews without turning votes into truth.

    Existing MULTIVERSE aggregation remains the canonical descriptive aggregation
    mechanism. This adapter only translates that evidence-bound aggregate into
    Opportunity Engine challenge/revision states. It never grants execution,
    adoption, spend, publication, provider-effect or Runtime authority.
    """
    validate_multiverse_review_packet(review_packet)
    if not isinstance(research_results, list) or not research_results:
        raise OpportunityBridgeError("at least one research result is required")

    # Verify every individual result against the frozen Opportunity Engine manifest
    # before using the existing MULTIVERSE aggregate layer.
    feedbacks = [
        ingest_multiverse_review_result(
            review_packet=review_packet,
            research_result=result,
        )
        for result in research_results
    ]

    task = review_packet["research_task"]
    aggregate = aggregate_results_v2(task, research_results)
    claim_states = [_classify_claim(claim) for claim in aggregate["claims"]]

    coverage_complete = bool(
        aggregate["requested_role_completed_coverage_complete"]
    )
    has_blocking = any(
        claim["state"] == "BLOCKING_CHALLENGE"
        for claim in claim_states
    )
    has_divergence = any(
        claim["state"] == "FALSIFICATION_REQUIRED"
        for claim in claim_states
    )
    has_revision = any(
        claim["state"] == "REVISION_OR_MORE_EVIDENCE"
        for claim in claim_states
    )
    has_uncertainty = any(
        feedback["uncertainty_factors"]
        for feedback in feedbacks
    )

    if not coverage_complete:
        overall_state = "REVIEW_INCOMPLETE"
    elif has_blocking:
        overall_state = "CHALLENGE_REQUIRED"
    elif has_divergence:
        overall_state = "FALSIFICATION_REQUIRED"
    elif has_revision or has_uncertainty:
        overall_state = "MORE_EVIDENCE_OR_REVISION"
    else:
        overall_state = "NO_BLOCKER_FOUND_YET"

    affected_subsystems = sorted(
        {
            claim["subsystem"]
            for claim in claim_states
            if claim["state"] != "NO_BLOCKER_FOUND_YET"
        }
    )
    individual_feedback = sorted(
        (
            {
                "submission_id": feedback["submission_id"],
                "review_state": feedback["review_state"],
                "feedback_sha256": feedback["feedback_sha256"],
                "model_identity": copy.deepcopy(feedback["model_identity"]),
            }
            for feedback in feedbacks
        ),
        key=lambda item: (
            item["model_identity"]["provider"],
            item["model_identity"]["model"],
            item["model_identity"]["role"],
            item["submission_id"],
        ),
    )

    output = {
        "schema": ENSEMBLE_SCHEMA,
        "case_id": review_packet["case_id"],
        "task_id": task["task_id"],
        "snapshot_id": task["snapshot_id"],
        "review_packet_sha256": review_packet["packet_sha256"],
        "multiverse_aggregate_sha256": aggregate["aggregate_sha256"],
        "overall_state": overall_state,
        "recommended_next_action": _next_action(overall_state),
        "claim_states": claim_states,
        "affected_subsystems": affected_subsystems,
        "review_coverage": {
            "requested_role_completed_coverage_complete": coverage_complete,
            "roles_without_completed_result": copy.deepcopy(
                aggregate["roles_without_completed_result"]
            ),
            "completed_unique_advisory_identity_count": aggregate[
                "completed_unique_advisory_identity_count"
            ],
            "completed_unique_provider_model_count": aggregate[
                "completed_unique_provider_model_count"
            ],
            "completed_unique_provider_count": aggregate[
                "completed_unique_provider_count"
            ],
        },
        "individual_feedback": individual_feedback,
        "majority_confers_truth": False,
        "support_confers_approval": False,
        "automatic_advance_authorized": False,
        "authority": _nonauthority(),
        "note": (
            "Advisory synthesis only. Even unanimous support only means no blocker "
            "was found in this bounded review. Formal gates and Owner authority remain external."
        ),
    }
    output["ensemble_sha256"] = sha256_json(output)
    return output
