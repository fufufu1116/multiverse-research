"""Fail-closed numeric calibration mechanics for the Reality foundation."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


class NumericCalibrationError(ValueError):
    pass


@dataclass(frozen=True)
class QuantileEnvelope:
    minimum: float
    q05: float
    q25: float
    median: float
    q75: float
    q95: float
    maximum: float

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "QuantileEnvelope":
        required = ("min", "q05", "q25", "median", "q75", "q95", "max")
        try:
            vals = [float(data[k]) for k in required]
        except Exception as exc:
            raise NumericCalibrationError("complete numeric quantile envelope required") from exc
        if not all(isfinite(v) for v in vals):
            raise NumericCalibrationError("finite quantile values required")
        if vals != sorted(vals):
            raise NumericCalibrationError("quantile envelope must be monotone")
        return cls(*vals)

    def central(self, u: float) -> float:
        return _piecewise(u, (self.q05, self.q25, self.median, self.q75, self.q95))

    def stress(self, u: float) -> float:
        return _piecewise(u, (self.minimum, self.q05, self.median, self.q95, self.maximum))


def _piecewise(u: float, knots: tuple[float, ...]) -> float:
    if not isfinite(float(u)) or not 0.0 <= float(u) <= 1.0:
        raise NumericCalibrationError("coordinate must be in [0,1]")
    x = float(u) * (len(knots) - 1)
    lo = int(x)
    if lo >= len(knots) - 1:
        return float(knots[-1])
    frac = x - lo
    return float(knots[lo] * (1.0 - frac) + knots[lo + 1] * frac)


def _support_value(data: Mapping[str, object], u: float, stress: bool) -> float:
    keys = ("min", "q05", "median", "q95", "max")
    try:
        vals = tuple(float(data[k]) for k in keys)
    except Exception as exc:
        raise NumericCalibrationError("five-point support envelope required") from exc
    if vals != tuple(sorted(vals)):
        raise NumericCalibrationError("support envelope must be monotone")
    if stress:
        return _piecewise(u, vals)
    return _piecewise(u, (vals[1], vals[2], vals[3]))


@dataclass(frozen=True)
class NumericCalibrationRegistry:
    raw: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.raw.get("status") != "PARTIAL_NUMERIC_CALIBRATION_PASS_FAIL_CLOSED_ON_UNIDENTIFIED_TACTICS":
            raise NumericCalibrationError("unexpected registry status")
        score_map = self.raw.get("competition_score_observation_envelopes_by_class")
        if not isinstance(score_map, Mapping) or set(score_map) != {"S1", "S2", "A1", "A2", "A3"}:
            raise NumericCalibrationError("all five class score envelopes required")
        for data in score_map.values():
            QuantileEnvelope.from_mapping(data)
        tactical = self.raw.get("tactical_numeric_status")
        if not isinstance(tactical, Mapping):
            raise NumericCalibrationError("tactical status required")
        for key, value in tactical.items():
            if key == "rule":
                continue
            if value != "UNIDENTIFIED":
                raise NumericCalibrationError(f"tactical numeric value not admitted: {key}")
        topology = self.raw.get("line_topology_support")
        if not isinstance(topology, Mapping) or topology.get("truth_sampling_weight_calibrated") is not False:
            raise NumericCalibrationError("line topology weights must remain uncalibrated")
        if topology.get("population_frequency_claim") is not False:
            raise NumericCalibrationError("population topology frequency claim prohibited")

    def score(self, class_band: str, u: float, mode: str = "central") -> float:
        data = self.raw["competition_score_observation_envelopes_by_class"][class_band]
        env = QuantileEnvelope.from_mapping(data)
        if mode == "central":
            return env.central(u)
        if mode == "stress":
            return env.stress(u)
        raise NumericCalibrationError("mode must be central or stress")

    def style_feature(self, style: str, feature: str, u: float, mode: str = "central") -> float:
        styles = self.raw.get("race_pre_style_conditional_support")
        if not isinstance(styles, Mapping) or style not in styles:
            raise NumericCalibrationError("unknown style support")
        data = styles[style]
        if not isinstance(data, Mapping) or feature not in data or not isinstance(data[feature], Mapping):
            raise NumericCalibrationError("unknown style feature support")
        if mode not in ("central", "stress"):
            raise NumericCalibrationError("mode must be central or stress")
        return _support_value(data[feature], u, mode == "stress")

    def tactical_numeric_available(self) -> bool:
        return False
