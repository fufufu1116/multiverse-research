from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS

from .multiverse_bridge import OpportunityBridgeError, sha256_json

ESCALATION_SCHEMA = "MULTIVERSE_OPPORTUNITY_PROVIDER_ESCALATION_v1"


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def _score(value: Any, name: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 5:
        raise OpportunityBridgeError(f"{name} must be an integer from 0 to 5")
    return value


def plan_provider_escalation(
    *,
    current_provider_count: int,
    uncertainty_score: int,
    disagreement_score: int,
    max_unresolved_severity: str | None,
    expected_upside_yen: float,
    downside_if_wrong_yen: float,
    estimated_next_review_cost_yen: float,
    max_review_budget_yen: float,
    local_falsification_available: bool,
    official_or_deterministic_check_available: bool,
    high_stakes_domain: bool = False,
) -> dict[str, Any]:
    """Recommend research escalation without authorizing provider use or spend.

    Cost is only one input. The function prefers cheaper mechanical/official checks
    when they can resolve the dispute, and it never converts a recommendation into
    credential, provider-call, spend or execution authority.
    """
    if not isinstance(current_provider_count, int) or current_provider_count < 1:
        raise OpportunityBridgeError("current_provider_count must be >= 1")
    uncertainty = _score(uncertainty_score, "uncertainty_score")
    disagreement = _score(disagreement_score, "disagreement_score")
    allowed_severity = {None, "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if max_unresolved_severity not in allowed_severity:
        raise OpportunityBridgeError("unexpected unresolved severity")
    for value, name in (
        (expected_upside_yen, "expected_upside_yen"),
        (downside_if_wrong_yen, "downside_if_wrong_yen"),
        (estimated_next_review_cost_yen, "estimated_next_review_cost_yen"),
        (max_review_budget_yen, "max_review_budget_yen"),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise OpportunityBridgeError(f"{name} must be a nonnegative number")
    if not isinstance(local_falsification_available, bool):
        raise OpportunityBridgeError("local_falsification_available must be boolean")
    if not isinstance(official_or_deterministic_check_available, bool):
        raise OpportunityBridgeError("official_or_deterministic_check_available must be boolean")
    if not isinstance(high_stakes_domain, bool):
        raise OpportunityBridgeError("high_stakes_domain must be boolean")

    severe = max_unresolved_severity in {"HIGH", "CRITICAL"}
    budget_ok = estimated_next_review_cost_yen <= max_review_budget_yen
    # A deliberately conservative heuristic: the next paid review should be cheap
    # relative to the money materially at risk, not merely affordable in isolation.
    decision_value_at_risk = max(
        float(downside_if_wrong_yen),
        float(expected_upside_yen) * 0.10,
    )
    cost_is_small_relative_to_decision = (
        estimated_next_review_cost_yen == 0
        or decision_value_at_risk >= estimated_next_review_cost_yen * 20
    )

    if high_stakes_domain and official_or_deterministic_check_available:
        state = "PRIMARY_OR_DETERMINISTIC_CHECK_FIRST"
        next_action = "RUN_OFFICIAL_OR_DETERMINISTIC_CHECK"
    elif disagreement > 0 and local_falsification_available:
        state = "LOCAL_FALSIFICATION_FIRST"
        next_action = "RUN_LOCAL_FALSIFICATION"
    elif severe and official_or_deterministic_check_available:
        state = "PRIMARY_OR_DETERMINISTIC_CHECK_FIRST"
        next_action = "RUN_OFFICIAL_OR_DETERMINISTIC_CHECK"
    elif not budget_ok:
        state = "PAID_ESCALATION_BLOCKED_BY_BUDGET"
        next_action = "CONTINUE_ZERO_OR_LOW_COST_RESEARCH"
    elif current_provider_count >= 2 and disagreement <= 1 and uncertainty <= 2 and not severe:
        state = "NO_ADDITIONAL_PROVIDER_NEEDED_YET"
        next_action = "HOLD_PROVIDER_SPEND"
    elif (
        current_provider_count < 2
        and cost_is_small_relative_to_decision
        and (uncertainty >= 3 or disagreement >= 2 or severe)
    ):
        state = "ADD_ONE_CROSS_PROVIDER_CHALLENGE"
        next_action = "PREPARE_BOUNDED_CROSS_PROVIDER_REVIEW"
    elif (
        current_provider_count >= 2
        and disagreement >= 3
        and cost_is_small_relative_to_decision
    ):
        state = "THIRD_PROVIDER_MAY_BE_WORTH_TESTING"
        next_action = "PREPARE_ONE_ADDITIONAL_INDEPENDENT_REVIEW"
    else:
        state = "CHEAPER_EVIDENCE_BEFORE_PROVIDER_SPEND"
        next_action = "CONTINUE_RESEARCH_AND_REASSESS"

    output = {
        "schema": ESCALATION_SCHEMA,
        "state": state,
        "recommended_next_action": next_action,
        "current_provider_count": current_provider_count,
        "uncertainty_score": uncertainty,
        "disagreement_score": disagreement,
        "max_unresolved_severity": max_unresolved_severity,
        "estimated_next_review_cost_yen": float(estimated_next_review_cost_yen),
        "max_review_budget_yen": float(max_review_budget_yen),
        "decision_value_at_risk_proxy_yen": decision_value_at_risk,
        "cost_small_relative_to_decision": cost_is_small_relative_to_decision,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "credential_use_authorized": False,
        "automatic_advance_authorized": False,
        "authority": _nonauthority(),
        "note": (
            "Heuristic research routing only. Fresh provider pricing/limits and exact Owner/MULTIVERSE "
            "authorization are required before any real provider call or spend."
        ),
    }
    output["escalation_sha256"] = sha256_json(output)
    return output
