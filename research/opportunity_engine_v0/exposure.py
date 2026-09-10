from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .scale import ScaleClass


class ExposureMode(str, Enum):
    KEEP_INTERNAL = "KEEP_INTERNAL"
    SELL_SIGNAL = "SELL_SIGNAL"
    SELL_PLAYBOOK = "SELL_PLAYBOOK"
    LIMITED_LICENSE = "LIMITED_LICENSE"


@dataclass(frozen=True)
class ExposureProfile:
    scale_class: ScaleClass
    copy_risk: int
    strategic_leakage_risk: int
    buyer_value: int
    time_sensitivity: int
    core_method_exposed: bool
    proprietary_data_exposed: bool
    creates_competitor_against_us: bool
    expires_naturally: bool
    independently_useful_without_multiverse: bool

    def __post_init__(self) -> None:
        for field_name in (
            "copy_risk",
            "strategic_leakage_risk",
            "buyer_value",
            "time_sensitivity",
        ):
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")


@dataclass(frozen=True)
class ExposureDecision:
    mode: ExposureMode
    reasons: Tuple[str, ...]
    blockers: Tuple[str, ...]


def evaluate_exposure(profile: ExposureProfile) -> ExposureDecision:
    reasons = []
    blockers = []

    # Never sell the mechanism that creates the advantage.
    if profile.core_method_exposed:
        blockers.append("CORE_METHOD_EXPOSED")
    if profile.proprietary_data_exposed:
        blockers.append("PROPRIETARY_DATA_EXPOSED")
    if profile.strategic_leakage_risk >= 4:
        blockers.append("STRATEGIC_LEAKAGE_TOO_HIGH")
    if profile.copy_risk >= 4 and profile.creates_competitor_against_us:
        blockers.append("SALE_CREATES_DANGEROUS_COMPETITOR")

    # Portfolio/platform opportunities are presumptively retained because the
    # expected internal option value is larger than a one-off information sale.
    if profile.scale_class in (ScaleClass.PORTFOLIO, ScaleClass.PLATFORM):
        blockers.append("HIGH_SCALE_OPTION_VALUE_KEEP_INTERNAL")

    if blockers:
        return ExposureDecision(ExposureMode.KEEP_INTERNAL, tuple(reasons), tuple(blockers))

    if profile.buyer_value < 3 or not profile.independently_useful_without_multiverse:
        blockers.append("OUTPUT_NOT_SELLABLE_ON_ITS_OWN")
        return ExposureDecision(ExposureMode.KEEP_INTERNAL, tuple(reasons), tuple(blockers))

    if profile.scale_class == ScaleClass.TACTICAL:
        if profile.expires_naturally or profile.time_sensitivity >= 4:
            reasons.append("TACTICAL_WINDOW_CAN_BE_MONETIZED_WITHOUT_SELLING_CORE")
        return ExposureDecision(ExposureMode.SELL_SIGNAL, tuple(reasons), ())

    if profile.scale_class == ScaleClass.SUSTAINING:
        reasons.append("REPEATABLE_OUTPUT_CAN_BE_SOLD_AS_BOUNDED_PLAYBOOK")
        return ExposureDecision(ExposureMode.SELL_PLAYBOOK, tuple(reasons), ())

    # Growth-class outputs may be monetized only as a bounded license when the
    # core method/data remain hidden and the sale does not manufacture a direct
    # dangerous competitor.
    if profile.scale_class == ScaleClass.GROWTH:
        reasons.append("GROWTH_OUTPUT_REQUIRES_BOUNDED_ACCESS")
        return ExposureDecision(ExposureMode.LIMITED_LICENSE, tuple(reasons), ())

    return ExposureDecision(ExposureMode.KEEP_INTERNAL, tuple(reasons), tuple(blockers))
