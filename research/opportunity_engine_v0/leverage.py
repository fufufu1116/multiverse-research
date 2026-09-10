from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import log2
from typing import Optional, Tuple


class LeverageKind(str, Enum):
    DISTRIBUTION = "DISTRIBUTION"
    AUTOMATION = "AUTOMATION"
    AI = "AI"
    MONETIZATION = "MONETIZATION"
    DATA = "DATA"
    REUSE = "REUSE"
    GEOGRAPHY = "GEOGRAPHY"
    PARTNER = "PARTNER"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class LeverageDecision(str, Enum):
    SEARCH_INCOMPLETE = "SEARCH_INCOMPLETE"
    NO_SAFE_LEVERAGE = "NO_SAFE_LEVERAGE"
    LEVERAGE_READY = "LEVERAGE_READY"


@dataclass(frozen=True)
class LeverageOption:
    name: str
    kind: LeverageKind
    verified_available: bool
    evidence_count: int
    expected_output_multiplier: float
    setup_cost_yen: int
    setup_days: float
    recurring_cost_yen_month: int
    owner_hours_month: float
    automation_gain_pct: int
    reusable_asset_gain: int
    copy_exposure_risk: int
    vendor_lock_in_risk: int
    legal_risk: int
    reversibility: int
    existing_system_share: float
    requires_team: bool = False
    requires_sales_calls: bool = False
    requires_inventory: bool = False
    deceptive_tactics_required: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        if self.evidence_count < 0:
            raise ValueError("evidence_count must be non-negative")
        if self.expected_output_multiplier < 1.0:
            raise ValueError("expected_output_multiplier must be >= 1")
        for field_name in (
            "setup_cost_yen",
            "setup_days",
            "recurring_cost_yen_month",
            "owner_hours_month",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if not 0 <= self.automation_gain_pct <= 100:
            raise ValueError("automation_gain_pct must be between 0 and 100")
        for field_name in (
            "reusable_asset_gain",
            "copy_exposure_risk",
            "vendor_lock_in_risk",
            "legal_risk",
            "reversibility",
        ):
            if not 0 <= getattr(self, field_name) <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")
        if not 0.0 <= self.existing_system_share <= 1.0:
            raise ValueError("existing_system_share must be between 0 and 1")


@dataclass(frozen=True)
class LeverageScan:
    searched_at: str
    distribution_checked: bool
    automation_checked: bool
    ai_checked: bool
    monetization_checked: bool
    data_checked: bool
    reuse_checked: bool
    geography_checked: bool
    partner_checked: bool
    infrastructure_checked: bool
    options: Tuple[LeverageOption, ...]

    @property
    def complete(self) -> bool:
        return bool(self.searched_at.strip()) and all(
            (
                self.distribution_checked,
                self.automation_checked,
                self.ai_checked,
                self.monetization_checked,
                self.data_checked,
                self.reuse_checked,
                self.geography_checked,
                self.partner_checked,
                self.infrastructure_checked,
            )
        )


@dataclass(frozen=True)
class RankedLeverage:
    option: LeverageOption
    score: int
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class LeverageAssessment:
    decision: LeverageDecision
    ranked: Tuple[RankedLeverage, ...]
    conservative_multiplier: float
    hard_failures: Tuple[str, ...]


def _eligibility_failures(option: LeverageOption) -> Tuple[str, ...]:
    failures = []
    if not option.verified_available or option.evidence_count < 1:
        failures.append("UNVERIFIED_LEVERAGE")
    if option.deceptive_tactics_required:
        failures.append("DECEPTIVE_TACTICS_REQUIRED")
    if option.legal_risk >= 4:
        failures.append("LEGAL_RISK_TOO_HIGH")
    if option.copy_exposure_risk >= 4:
        failures.append("COPY_EXPOSURE_TOO_HIGH")
    if option.requires_team:
        failures.append("REQUIRES_TEAM")
    if option.requires_sales_calls:
        failures.append("REQUIRES_SALES_CALLS")
    if option.requires_inventory:
        failures.append("REQUIRES_INVENTORY")
    return tuple(failures)


def score_leverage(option: LeverageOption) -> tuple[Optional[int], Tuple[str, ...]]:
    failures = _eligibility_failures(option)
    if failures:
        return None, failures

    positive = (
        log2(option.expected_output_multiplier) * 18
        + option.automation_gain_pct * 0.18
        + option.reusable_asset_gain * 5
        + option.reversibility * 2
        + option.existing_system_share * 10
        + min(option.evidence_count, 3) * 2
    )
    penalties = (
        min(option.setup_cost_yen / 1000.0, 20) * 0.7
        + min(option.recurring_cost_yen_month / 1000.0, 20) * 0.5
        + option.owner_hours_month * 1.5
        + option.vendor_lock_in_risk * 3
        + option.legal_risk * 4
    )

    reasons = []
    if option.existing_system_share >= 0.80:
        reasons.append("HIGH_EXISTING_SYSTEM_REUSE")
    if option.automation_gain_pct >= 50:
        reasons.append("STRONG_AUTOMATION_GAIN")
    if option.reusable_asset_gain >= 4:
        reasons.append("COMPOUNDING_ASSET")
    if option.reversibility >= 4:
        reasons.append("HIGH_REVERSIBILITY")

    score = round(max(0, min(100, positive - penalties)))
    return score, tuple(reasons)


def conservative_combined_multiplier(options: Tuple[LeverageOption, ...]) -> float:
    """Estimate stacked leverage without naively multiplying every claimed uplift.

    The strongest eligible option receives full credit. The second and third
    receive diminishing credit because leverage mechanisms often overlap.
    More than three are not counted in this first-pass estimate.
    """
    eligible = []
    for option in options:
        score, _ = score_leverage(option)
        if score is not None:
            eligible.append(option)

    eligible.sort(key=lambda item: item.expected_output_multiplier, reverse=True)
    discounts = (1.0, 0.5, 0.25)
    uplift = sum(
        (option.expected_output_multiplier - 1.0) * discount
        for option, discount in zip(eligible[:3], discounts)
    )
    return round(1.0 + uplift, 2)


def assess_leverage(scan: LeverageScan) -> LeverageAssessment:
    """Rank leverage options after a mandatory broad search.

    Search itself is part of the gate: a candidate should not be called
    leverage-optimized merely because one obvious tactic was found.
    """
    if not scan.complete:
        return LeverageAssessment(
            decision=LeverageDecision.SEARCH_INCOMPLETE,
            ranked=(),
            conservative_multiplier=1.0,
            hard_failures=("LEVERAGE_SEARCH_INCOMPLETE",),
        )

    ranked = []
    rejected_failures = []
    for option in scan.options:
        score, reasons = score_leverage(option)
        if score is None:
            rejected_failures.extend(reasons)
            continue
        ranked.append(RankedLeverage(option=option, score=score, reasons=reasons))

    ranked.sort(
        key=lambda item: (
            item.score,
            item.option.expected_output_multiplier,
            item.option.name,
        ),
        reverse=True,
    )

    if not ranked:
        return LeverageAssessment(
            decision=LeverageDecision.NO_SAFE_LEVERAGE,
            ranked=(),
            conservative_multiplier=1.0,
            hard_failures=tuple(sorted(set(rejected_failures))),
        )

    selected = tuple(item.option for item in ranked[:3])
    return LeverageAssessment(
        decision=LeverageDecision.LEVERAGE_READY,
        ranked=tuple(ranked),
        conservative_multiplier=conservative_combined_multiplier(selected),
        hard_failures=tuple(sorted(set(rejected_failures))),
    )
