from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class ScaleClass(str, Enum):
    TACTICAL = "TACTICAL"
    SUSTAINING = "SUSTAINING"
    GROWTH = "GROWTH"
    PORTFOLIO = "PORTFOLIO"
    PLATFORM = "PLATFORM"


@dataclass(frozen=True)
class ScalePolicy:
    sustain_monthly_profit_yen: int
    growth_monthly_profit_yen: int
    portfolio_monthly_profit_yen: int
    platform_monthly_profit_yen: int

    def __post_init__(self) -> None:
        values = (
            self.sustain_monthly_profit_yen,
            self.growth_monthly_profit_yen,
            self.portfolio_monthly_profit_yen,
            self.platform_monthly_profit_yen,
        )
        if any(v <= 0 for v in values):
            raise ValueError("scale thresholds must be positive")
        if list(values) != sorted(values):
            raise ValueError("scale thresholds must be ordered")


@dataclass(frozen=True)
class ScaleProfile:
    current_monthly_profit_yen: int
    credible_monthly_profit_ceiling_yen: int
    months_to_ceiling: float
    existing_service_coverage: float
    custom_build_share: float
    automation_ratio: float
    owner_hours_per_week_at_ceiling: float
    scale_steps: Tuple[str, ...]
    ceiling_blocker: str
    reversible: bool = True
    requires_team_at_ceiling: bool = False
    requires_sales_calls_at_ceiling: bool = False
    requires_inventory_at_ceiling: bool = False

    def __post_init__(self) -> None:
        if self.current_monthly_profit_yen < 0 or self.credible_monthly_profit_ceiling_yen < 0:
            raise ValueError("profit values must be non-negative")
        if self.credible_monthly_profit_ceiling_yen < self.current_monthly_profit_yen:
            raise ValueError("credible ceiling cannot be below current profit")
        if self.months_to_ceiling < 0:
            raise ValueError("months_to_ceiling must be non-negative")
        for field_name in ("existing_service_coverage", "custom_build_share", "automation_ratio"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.owner_hours_per_week_at_ceiling < 0:
            raise ValueError("owner_hours_per_week_at_ceiling must be non-negative")
        if len(self.scale_steps) > 7:
            raise ValueError("scale_steps must contain at most 7 steps")


@dataclass(frozen=True)
class ScaleEvaluation:
    scale_class: ScaleClass
    reasons: Tuple[str, ...]
    blockers: Tuple[str, ...]
    existing_system_leverage_score: int


def evaluate_scale(profile: ScaleProfile, policy: ScalePolicy) -> ScaleEvaluation:
    reasons = []
    blockers = []

    ceiling = profile.credible_monthly_profit_ceiling_yen

    if ceiling >= policy.platform_monthly_profit_yen:
        scale_class = ScaleClass.PLATFORM
    elif ceiling >= policy.portfolio_monthly_profit_yen:
        scale_class = ScaleClass.PORTFOLIO
    elif ceiling >= policy.growth_monthly_profit_yen:
        scale_class = ScaleClass.GROWTH
    elif ceiling >= policy.sustain_monthly_profit_yen:
        scale_class = ScaleClass.SUSTAINING
    else:
        scale_class = ScaleClass.TACTICAL

    if profile.current_monthly_profit_yen < policy.sustain_monthly_profit_yen:
        if ceiling >= policy.sustain_monthly_profit_yen and len(profile.scale_steps) >= 2:
            reasons.append("HAS_PATH_TO_SUSTAINING_INCOME")
        elif ceiling < policy.sustain_monthly_profit_yen:
            blockers.append("CEILING_BELOW_SUSTAINING_TARGET")
        else:
            blockers.append("SCALE_PATH_UNDERDEFINED")

    if profile.existing_service_coverage >= 0.80 and profile.custom_build_share <= 0.20:
        reasons.append("EXISTING_SYSTEM_LEVERAGE_HIGH")
    elif profile.custom_build_share > 0.50:
        blockers.append("CUSTOM_BUILD_TOO_HEAVY")

    if profile.automation_ratio >= 0.80:
        reasons.append("AUTOMATION_FRIENDLY")
    if profile.owner_hours_per_week_at_ceiling > 20:
        blockers.append("OWNER_TIME_CEILING_TOO_HIGH")
    if profile.requires_team_at_ceiling:
        blockers.append("TEAM_REQUIRED_AT_CEILING")
    if profile.requires_sales_calls_at_ceiling:
        blockers.append("SALES_CALLS_REQUIRED_AT_CEILING")
    if profile.requires_inventory_at_ceiling:
        blockers.append("INVENTORY_REQUIRED_AT_CEILING")
    if not profile.reversible:
        blockers.append("LOW_REVERSIBILITY")
    if not profile.ceiling_blocker.strip():
        blockers.append("CEILING_BLOCKER_UNKNOWN")

    leverage = round(
        100
        * (
            profile.existing_service_coverage * 0.45
            + (1.0 - profile.custom_build_share) * 0.30
            + profile.automation_ratio * 0.25
        )
    )

    return ScaleEvaluation(
        scale_class=scale_class,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
        existing_system_leverage_score=max(0, min(100, leverage)),
    )
