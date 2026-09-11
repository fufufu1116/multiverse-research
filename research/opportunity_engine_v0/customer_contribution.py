"""Research-only customer contribution / value-return economics.

A healthy loop may reward useful voluntary participation, but rewards must not
turn into disguised extraction, fake gamification, or an uneconomic subsidy.
"""
from dataclasses import dataclass
from enum import Enum


class ContributionDecision(str, Enum):
    REJECT = "REJECT"
    REDESIGN = "REDESIGN"
    TESTABLE = "TESTABLE"


@dataclass(frozen=True)
class ContributionLoop:
    customer_value_score: int
    contribution_usefulness: int
    contribution_verifiability: int
    consent_clarity: int
    reward_transparency: int
    portability: int
    abuse_risk: int
    manipulation_risk: int
    estimated_reward_cost_per_user: float
    estimated_incremental_value_per_user: float

    def __post_init__(self) -> None:
        for name in (
            "customer_value_score", "contribution_usefulness", "contribution_verifiability",
            "consent_clarity", "reward_transparency", "portability", "abuse_risk",
            "manipulation_risk",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be 0..5")
        if self.estimated_reward_cost_per_user < 0 or self.estimated_incremental_value_per_user < 0:
            raise ValueError("economics estimates must be non-negative")


def assess_contribution_loop(loop: ContributionLoop) -> dict:
    reasons = []
    if loop.manipulation_risk >= 3:
        reasons.append("MANIPULATION_RISK")
    if loop.consent_clarity < 3:
        reasons.append("CONSENT_NOT_CLEAR")
    if loop.reward_transparency < 3:
        reasons.append("REWARD_NOT_TRANSPARENT")
    if loop.abuse_risk >= 4:
        reasons.append("ABUSE_RISK_HIGH")
    if loop.contribution_verifiability < 2:
        reasons.append("CONTRIBUTION_TOO_HARD_TO_VERIFY")

    unit_economics_ratio = None
    if loop.estimated_reward_cost_per_user > 0:
        unit_economics_ratio = loop.estimated_incremental_value_per_user / loop.estimated_reward_cost_per_user
        if unit_economics_ratio < 1:
            reasons.append("REWARD_COST_EXCEEDS_ESTIMATED_INCREMENTAL_VALUE")

    if "MANIPULATION_RISK" in reasons or "CONSENT_NOT_CLEAR" in reasons:
        decision = ContributionDecision.REJECT
    elif reasons:
        decision = ContributionDecision.REDESIGN
    else:
        decision = ContributionDecision.TESTABLE

    return {
        "decision": decision.value,
        "reasons": reasons,
        "unit_economics_ratio_hypothesis": unit_economics_ratio,
        "reward_is_entitlement": False,
        "ranking_can_be_bought": False,
        "contribution_counts_as_independent_evidence": False,
        "requires_measured_outcome_before_learning": True,
        "automatic_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
    }
