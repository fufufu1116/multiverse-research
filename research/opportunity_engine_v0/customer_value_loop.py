"""Customer value return loop for Opportunity Engine research.

This module prevents the engine from optimizing only for seller revenue. It asks
whether customers receive durable value from participation beyond the purchased
item itself. All outputs are research-only and confer no live authority.
"""
from dataclasses import dataclass
from enum import Enum


class ValueReturnDecision(str, Enum):
    REDESIGN = "REDESIGN"
    RESEARCH = "RESEARCH"
    VALUE_LOOP_CANDIDATE = "VALUE_LOOP_CANDIDATE"


@dataclass(frozen=True)
class CustomerValueReturn:
    utility_gain: int
    learning_gain: int
    saved_money_or_time: int
    identity_or_expression_gain: int
    community_or_status_gain: int
    portable_asset_gain: int
    transparency: int
    manipulation_risk: int
    artificial_lock_in: int
    seller_subsidy_cost: int

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def assess_customer_value_return(v: CustomerValueReturn) -> dict:
    """Score non-product customer value without treating gimmicks as value."""
    benefits = (
        v.utility_gain * 6
        + v.learning_gain * 4
        + v.saved_money_or_time * 6
        + v.identity_or_expression_gain * 3
        + v.community_or_status_gain * 2
        + v.portable_asset_gain * 5
        + v.transparency * 5
    )
    penalties = (
        v.manipulation_risk * 10
        + v.artificial_lock_in * 8
        + v.seller_subsidy_cost * 3
    )
    score = max(0, min(100, benefits - penalties))

    blockers = []
    if v.manipulation_risk >= 3:
        blockers.append("MANIPULATION_RISK_TOO_HIGH")
    if v.artificial_lock_in >= 4:
        blockers.append("ARTIFICIAL_LOCK_IN_TOO_HIGH")
    if v.transparency < 3:
        blockers.append("VALUE_EXCHANGE_NOT_TRANSPARENT")
    if max(v.utility_gain, v.learning_gain, v.saved_money_or_time, v.portable_asset_gain) < 3:
        blockers.append("NO_STRONG_CUSTOMER_VALUE_BEYOND_PRODUCT")

    if blockers:
        decision = ValueReturnDecision.REDESIGN
    elif score >= 60:
        decision = ValueReturnDecision.VALUE_LOOP_CANDIDATE
    else:
        decision = ValueReturnDecision.RESEARCH

    return {
        "decision": decision.value,
        "score": score,
        "blockers": blockers,
        "principle": "customer participation should create real customer-owned or customer-felt value, not merely seller extraction",
        "acceptable_return_examples": [
            "save money or avoid a bad purchase",
            "save time or reduce decision fatigue",
            "learn a reusable skill",
            "build portable history, collection, progress or preferences",
            "receive transparent rewards for useful voluntary contribution",
            "gain expression, recognition or community without coercion",
        ],
        "automatic_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
    }
