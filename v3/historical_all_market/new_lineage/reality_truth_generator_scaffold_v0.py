"""Non-outcome Reality world scaffold using only admitted calibration envelopes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from reality_numeric_calibration_v0 import NumericCalibrationError, NumericCalibrationRegistry


class TruthExecutionBlocked(RuntimeError):
    pass


TACTICAL_SCENARIOS = {
    "T0_STABLE_LINE",
    "T1_BALANCED_TACTICAL",
    "T2_DISRUPTIVE",
    "T3_CONFLICT_WITH_RECOVERY",
}


@dataclass(frozen=True)
class RiderPrototype:
    rider_id: str
    class_band: str
    style: str
    competition_score: float
    B: float
    S: float
    nige: float
    makuri: float
    sashi: float
    mark: float


@dataclass(frozen=True)
class RealityWorldScaffold:
    tactical_scenario: str
    environment_mode: str = "NONE"

    def __post_init__(self) -> None:
        if self.tactical_scenario not in TACTICAL_SCENARIOS:
            raise NumericCalibrationError("unknown tactical scenario")
        if self.environment_mode not in {"NONE", "OBSERVED_WIND_SENSITIVITY"}:
            raise NumericCalibrationError("unsupported environment mode")


def build_rider_prototype(
    registry: NumericCalibrationRegistry,
    rider_id: str,
    class_band: str,
    style: str,
    coordinates: Mapping[str, float],
    mode: str = "central",
) -> RiderPrototype:
    required = {"score", "B", "S", "nige", "makuri", "sashi", "mark"}
    if set(coordinates) != required:
        raise NumericCalibrationError("explicit independent coordinates required for each calibrated dimension")
    if not rider_id:
        raise NumericCalibrationError("rider_id required")
    return RiderPrototype(
        rider_id=rider_id,
        class_band=class_band,
        style=style,
        competition_score=registry.score(class_band, coordinates["score"], mode),
        B=registry.style_feature(style, "B", coordinates["B"], mode),
        S=registry.style_feature(style, "S", coordinates["S"], mode),
        nige=registry.style_feature(style, "nige", coordinates["nige"], mode),
        makuri=registry.style_feature(style, "makuri", coordinates["makuri"], mode),
        sashi=registry.style_feature(style, "sashi", coordinates["sashi"], mode),
        mark=registry.style_feature(style, "mark", coordinates["mark"], mode),
    )


def validate_line_partition(active_car_numbers: Sequence[int], groups: Sequence[Sequence[int]]) -> tuple[int, ...]:
    active = tuple(active_car_numbers)
    if len(active) < 3 or len(set(active)) != len(active):
        raise NumericCalibrationError("invalid active field")
    flattened = tuple(c for group in groups for c in group)
    if len(flattened) != len(active) or set(flattened) != set(active):
        raise NumericCalibrationError("line groups must partition the active field exactly")
    if any(not group for group in groups):
        raise NumericCalibrationError("empty line group prohibited")
    return tuple(sorted((len(group) for group in groups), reverse=True))


def finish_order(*_args: object, **_kwargs: object) -> tuple[int, ...]:
    raise TruthExecutionBlocked("finish generation is outside the numeric-calibration scaffold gate")
