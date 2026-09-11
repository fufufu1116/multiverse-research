from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class Decision(str, Enum):
    REJECT = "REJECT"
    WATCH = "WATCH"
    MICRO_TEST = "MICRO_TEST"
    BUILD_CANDIDATE = "BUILD_CANDIDATE"


class RevenueRoute(str, Enum):
    ADVERTISING = "ADVERTISING"
    AFFILIATE = "AFFILIATE"
    ONE_TIME = "ONE_TIME"
    SUBSCRIPTION = "SUBSCRIPTION"
    TRANSACTION_FEE = "TRANSACTION_FEE"
    INTERNAL_ASSET = "INTERNAL_ASSET"


@dataclass(frozen=True)
class CompetitorResearch:
    direct_competitors_checked: bool
    substitutes_checked: bool
    bigtech_replacement_checked: bool
    why_not_already_common_explained: bool
    existing_systems_to_reuse: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return all(
            (
                self.direct_competitors_checked,
                self.substitutes_checked,
                self.bigtech_replacement_checked,
                self.why_not_already_common_explained,
            )
        )


@dataclass(frozen=True)
class OpportunityCandidate:
    name: str
    evidence_verified: bool
    buyer_clarity: int
    attention: int
    purchase_intent: int
    why_now: int
    why_not_before: int
    competitor_pressure: int
    incumbent_crush_risk: int
    ai_substitutability: int
    proprietary_edge: int
    action_completion: int
    reusable_asset: int
    distribution: int
    legal_risk: int
    human_burden: int
    initial_cost_yen: int
    build_days: float
    demand_life_days: Optional[float]
    expected_profit_low_yen: int
    expected_profit_base_yen: int
    expected_profit_high_yen: int
    deceptive_tactics_required: bool = False
    unverified_personal_claims_required: bool = False
    future_steps: Tuple[str, ...] = ()
    exit_trigger: str = ""
    competitor_research: CompetitorResearch = field(
        default_factory=lambda: CompetitorResearch(False, False, False, False)
    )

    def __post_init__(self) -> None:
        score_fields = (
            "buyer_clarity",
            "attention",
            "purchase_intent",
            "why_now",
            "why_not_before",
            "competitor_pressure",
            "incumbent_crush_risk",
            "ai_substitutability",
            "proprietary_edge",
            "action_completion",
            "reusable_asset",
            "distribution",
            "legal_risk",
            "human_burden",
        )
        for field_name in score_fields:
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")
        if self.initial_cost_yen < 0:
            raise ValueError("initial_cost_yen must be non-negative")
        if self.build_days < 0:
            raise ValueError("build_days must be non-negative")
        if self.demand_life_days is not None and self.demand_life_days <= 0:
            raise ValueError("demand_life_days must be positive when supplied")
        if not (
            self.expected_profit_low_yen
            <= self.expected_profit_base_yen
            <= self.expected_profit_high_yen
        ):
            raise ValueError("profit scenarios must be ordered low <= base <= high")
        if len(self.future_steps) > 7:
            raise ValueError("future_steps must contain at most 7 steps")
