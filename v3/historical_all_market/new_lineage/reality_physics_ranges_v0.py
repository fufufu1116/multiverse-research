"""Reality physics parameter-range contract v0.

Foundation-only. These ranges constrain sensitivity experiments and are not asserted
as exact Japanese-keirin population distributions or rider-specific truths.
No candidate model is imported or evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


class RangeContractError(ValueError):
    pass


@dataclass(frozen=True)
class ClosedRange:
    low: float
    high: float
    label: str

    def __post_init__(self) -> None:
        if not (isfinite(self.low) and isfinite(self.high)):
            raise RangeContractError(f"{self.label}: range endpoints must be finite")
        if self.low > self.high:
            raise RangeContractError(f"{self.label}: low must be <= high")

    def contains(self, value: float) -> bool:
        value = float(value)
        return isfinite(value) and self.low <= value <= self.high

    def require(self, value: float) -> float:
        value = float(value)
        if not self.contains(value):
            raise RangeContractError(
                f"{self.label}: {value} outside admitted sensitivity range "
                f"[{self.low}, {self.high}]"
            )
        return value


# Literature-bounded sensitivity supports. These are deliberately broad and are not
# probability distributions.
CDA_M2 = ClosedRange(0.19, 0.31, "CdA_m2")
DRAFTING_DRAG_MULTIPLIER_LEADER = ClosedRange(0.95, 1.00, "draft_leader")
DRAFTING_DRAG_MULTIPLIER_SECOND = ClosedRange(0.55, 0.70, "draft_second")
DRAFTING_DRAG_MULTIPLIER_LATER = ClosedRange(0.45, 0.65, "draft_later")
PEAK_MECHANICAL_POWER_W = ClosedRange(775.0, 2025.0, "peak_mechanical_power_W")
DRIVETRAIN_EFFICIENCY = ClosedRange(0.97, 0.99, "drivetrain_efficiency")
OFFICIAL_TRACK_LENGTH_SUPPORT_M = frozenset({333, 335, 400, 500})

# Crr=0.002 is retained only as a literature reference value. There is intentionally
# no admitted runtime range until track-tyre evidence justifies one.
ROLLING_RESISTANCE_REFERENCE_ONLY = 0.002
ROLLING_RESISTANCE_RUNTIME_ADMITTED = False


def require_official_track_length(track_length_m: int) -> int:
    value = int(track_length_m)
    if value != track_length_m or value not in OFFICIAL_TRACK_LENGTH_SUPPORT_M:
        raise RangeContractError(
            f"track_length_m must be one of {sorted(OFFICIAL_TRACK_LENGTH_SUPPORT_M)}"
        )
    return value


def require_drafting_multiplier(role: str, multiplier: float) -> float:
    role_key = role.strip().lower()
    ranges = {
        "leader": DRAFTING_DRAG_MULTIPLIER_LEADER,
        "second": DRAFTING_DRAG_MULTIPLIER_SECOND,
        "later": DRAFTING_DRAG_MULTIPLIER_LATER,
    }
    if role_key not in ranges:
        raise RangeContractError("drafting role must be leader, second, or later")
    return ranges[role_key].require(multiplier)


def require_rolling_resistance_runtime(_: float) -> float:
    raise RangeContractError(
        "rolling-resistance runtime range is not admitted yet; 0.002 is reference-only"
    )


def assert_no_probability_semantics() -> None:
    """Marker assertion: these supports are bounds, not sampling distributions."""
    assert CDA_M2.low < CDA_M2.high
    assert PEAK_MECHANICAL_POWER_W.low < PEAK_MECHANICAL_POWER_W.high
    assert ROLLING_RESISTANCE_RUNTIME_ADMITTED is False
