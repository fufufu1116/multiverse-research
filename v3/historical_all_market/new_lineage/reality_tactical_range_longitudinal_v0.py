"""Reality tactical-range + longitudinal rider foundation v0.

Foundation only. This module deliberately contains no fitted tactical probabilities,
no finish-effect coefficients, no candidate-model calls, no RESULT/PAYOUT access,
and no network access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Mapping, Sequence


class RealityCoreFoundationError(ValueError):
    pass


def _dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise RealityCoreFoundationError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RealityCoreFoundationError("timezone-aware timestamp required")
    return parsed


class OrdinalBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


TACTICAL_DIMENSIONS = (
    "line_cohesion",
    "initiative_conflict",
    "position_competition",
    "block_or_position_defense",
    "line_fragmentation",
    "switching",
    "reattachment",
    "solo_transition",
)


@dataclass(frozen=True)
class TacticalScenario:
    scenario_id: str
    bands: Mapping[str, OrdinalBand]

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise RealityCoreFoundationError("scenario_id required")
        if set(self.bands) != set(TACTICAL_DIMENSIONS):
            raise RealityCoreFoundationError("tactical scenario must define every dimension exactly once")
        for key, value in self.bands.items():
            if key not in TACTICAL_DIMENSIONS:
                raise RealityCoreFoundationError(f"unknown tactical dimension: {key}")
            if not isinstance(value, OrdinalBand):
                raise RealityCoreFoundationError("tactical values must be ordinal bands, not numeric probabilities")


@dataclass(frozen=True)
class ExpectedLineGroup:
    car_numbers: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.car_numbers:
            raise RealityCoreFoundationError("line group cannot be empty")
        if len(set(self.car_numbers)) != len(self.car_numbers):
            raise RealityCoreFoundationError("duplicate car number inside line group")
        if any((not isinstance(c, int)) or c < 1 for c in self.car_numbers):
            raise RealityCoreFoundationError("car numbers must be positive integers")


@dataclass(frozen=True)
class ExpectedLineSnapshot:
    race_id: str
    active_car_numbers: tuple[int, ...]
    groups: tuple[ExpectedLineGroup, ...]
    snapshot_timestamp: str
    decision_timestamp: str
    source_url: str
    provider_name: str
    provenance_sha: str
    observation_type: str = "PRE_EVENT_EXPECTED_LINE"

    def __post_init__(self) -> None:
        if self.observation_type != "PRE_EVENT_EXPECTED_LINE":
            raise RealityCoreFoundationError("this class accepts provider expected line only")
        if not self.race_id or not self.source_url or not self.provider_name or not self.provenance_sha:
            raise RealityCoreFoundationError("line provenance fields are required")
        if _dt(self.snapshot_timestamp) > _dt(self.decision_timestamp):
            raise RealityCoreFoundationError("expected line snapshot after decision cutoff")
        active = tuple(self.active_car_numbers)
        if len(active) < 3 or len(set(active)) != len(active):
            raise RealityCoreFoundationError("active car numbers invalid")
        flattened = tuple(c for group in self.groups for c in group.car_numbers)
        if len(flattened) != len(active):
            raise RealityCoreFoundationError("expected line must partition the active field exactly")
        if set(flattened) != set(active):
            raise RealityCoreFoundationError("expected line groups do not match active field")

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(sorted((len(g.car_numbers) for g in self.groups), reverse=True))


@dataclass(frozen=True)
class RiderTemporalObservation:
    rider_id: str
    observation_timestamp: str
    capture_timestamp: str
    source_url: str
    provenance_sha: str
    class_at_observation: str
    competition_score: float | None = None
    win_rate: float | None = None
    quinella_rate: float | None = None
    trio_rate: float | None = None
    S: float | None = None
    H: float | None = None
    B: float | None = None
    nige: float | None = None
    makuri: float | None = None
    sashi: float | None = None
    mark: float | None = None

    def __post_init__(self) -> None:
        if not self.rider_id or not self.source_url or not self.provenance_sha or not self.class_at_observation:
            raise RealityCoreFoundationError("rider observation provenance/identity required")
        observed = _dt(self.observation_timestamp)
        captured = _dt(self.capture_timestamp)
        if captured < observed:
            raise RealityCoreFoundationError("capture cannot precede observation")
        for name in (
            "competition_score", "win_rate", "quinella_rate", "trio_rate", "S", "H", "B",
            "nige", "makuri", "sashi", "mark",
        ):
            value = getattr(self, name)
            if value is not None and not isfinite(float(value)):
                raise RealityCoreFoundationError(f"{name} must be finite")
        for name in ("win_rate", "quinella_rate", "trio_rate"):
            value = getattr(self, name)
            if value is not None and not (0.0 <= float(value) <= 100.0):
                raise RealityCoreFoundationError(f"{name} outside [0,100]")
        for name in ("S", "H", "B", "nige", "makuri", "sashi", "mark"):
            value = getattr(self, name)
            if value is not None and float(value) < 0.0:
                raise RealityCoreFoundationError(f"{name} cannot be negative")


@dataclass(frozen=True)
class RiderLongitudinalSeries:
    rider_id: str
    observations: tuple[RiderTemporalObservation, ...]

    def __post_init__(self) -> None:
        if not self.rider_id or not self.observations:
            raise RealityCoreFoundationError("non-empty rider series required")
        if any(obs.rider_id != self.rider_id for obs in self.observations):
            raise RealityCoreFoundationError("mixed rider IDs in longitudinal series")
        keys = [(_dt(o.observation_timestamp), _dt(o.capture_timestamp)) for o in self.observations]
        if keys != sorted(keys):
            raise RealityCoreFoundationError("rider observations must be chronological")
        if len(set(keys)) != len(keys):
            raise RealityCoreFoundationError("duplicate rider observation/capture timestamp pair")

    def latest_available_by(self, decision_timestamp: str) -> RiderTemporalObservation:
        decision = _dt(decision_timestamp)
        eligible = [
            obs for obs in self.observations
            if _dt(obs.observation_timestamp) <= decision and _dt(obs.capture_timestamp) <= decision
        ]
        if not eligible:
            raise RealityCoreFoundationError("no point-in-time rider observation available by decision cutoff")
        return eligible[-1]


def validate_scenario_family(scenarios: Sequence[TacticalScenario]) -> None:
    if len(scenarios) < 3:
        raise RealityCoreFoundationError("at least three ordinal tactical worlds required")
    ids = [s.scenario_id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise RealityCoreFoundationError("duplicate tactical scenario ID")


def assert_no_numeric_tactical_mapping(mapping: Mapping[str, object]) -> None:
    """Reject attempts to sneak fitted probabilities/effect sizes into this foundation."""
    forbidden_tokens = ("probability", "prob", "coefficient", "coef", "effect_size", "win_effect")
    for key, value in mapping.items():
        lowered = key.lower()
        if any(token in lowered for token in forbidden_tokens):
            raise RealityCoreFoundationError(f"numeric tactical mapping prohibited at foundation gate: {key}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            raise RealityCoreFoundationError(f"numeric tactical value prohibited at foundation gate: {key}")
