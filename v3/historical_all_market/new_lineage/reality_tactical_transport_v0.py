"""Reality tactical/weather/leg-show transport foundation v0.

Foundation only. No race truth generation, no transition probabilities, no candidate
model calls, no network access, and no outcome/economic use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import FrozenSet


class RealityTransportError(ValueError):
    pass


def _dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise RealityTransportError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise RealityTransportError("timestamp must be timezone-aware")
    return parsed


class TacticalState(str, Enum):
    PRE_START_LINE_INTENT = "PRE_START_LINE_INTENT"
    INITIAL_POSITION_ACQUISITION = "INITIAL_POSITION_ACQUISITION"
    LINE_MAINTENANCE = "LINE_MAINTENANCE"
    INITIATIVE_ATTACK = "INITIATIVE_ATTACK"
    INITIATIVE_CONFLICT = "INITIATIVE_CONFLICT"
    BANTE_FOLLOWING = "BANTE_FOLLOWING"
    BLOCK_OR_POSITION_DEFENSE = "BLOCK_OR_POSITION_DEFENSE"
    POSITION_COMPETITION = "POSITION_COMPETITION"
    LINE_FRAGMENTATION = "LINE_FRAGMENTATION"
    SWITCHING = "SWITCHING"
    REATTACHMENT = "REATTACHMENT"
    SOLO_TRANSITION = "SOLO_TRANSITION"
    FINAL_SPRINT_OR_OVERTAKE = "FINAL_SPRINT_OR_OVERTAKE"
    TERMINAL_FINISH = "TERMINAL_FINISH"


# Structural reachability only. No probability or effect size is encoded here.
_ALLOWED: dict[TacticalState, FrozenSet[TacticalState]] = {
    TacticalState.PRE_START_LINE_INTENT: frozenset({TacticalState.INITIAL_POSITION_ACQUISITION}),
    TacticalState.INITIAL_POSITION_ACQUISITION: frozenset({
        TacticalState.LINE_MAINTENANCE,
        TacticalState.INITIATIVE_ATTACK,
        TacticalState.POSITION_COMPETITION,
        TacticalState.SOLO_TRANSITION,
    }),
    TacticalState.LINE_MAINTENANCE: frozenset({
        TacticalState.INITIATIVE_ATTACK,
        TacticalState.INITIATIVE_CONFLICT,
        TacticalState.BANTE_FOLLOWING,
        TacticalState.BLOCK_OR_POSITION_DEFENSE,
        TacticalState.POSITION_COMPETITION,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.INITIATIVE_ATTACK: frozenset({
        TacticalState.INITIATIVE_CONFLICT,
        TacticalState.LINE_MAINTENANCE,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.INITIATIVE_CONFLICT: frozenset({
        TacticalState.LINE_MAINTENANCE,
        TacticalState.POSITION_COMPETITION,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.SWITCHING,
        TacticalState.SOLO_TRANSITION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.BANTE_FOLLOWING: frozenset({
        TacticalState.BLOCK_OR_POSITION_DEFENSE,
        TacticalState.POSITION_COMPETITION,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.SWITCHING,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.BLOCK_OR_POSITION_DEFENSE: frozenset({
        TacticalState.BANTE_FOLLOWING,
        TacticalState.POSITION_COMPETITION,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.SWITCHING,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.POSITION_COMPETITION: frozenset({
        TacticalState.LINE_MAINTENANCE,
        TacticalState.BANTE_FOLLOWING,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.SWITCHING,
        TacticalState.SOLO_TRANSITION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.LINE_FRAGMENTATION: frozenset({
        TacticalState.SWITCHING,
        TacticalState.REATTACHMENT,
        TacticalState.SOLO_TRANSITION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.SWITCHING: frozenset({
        TacticalState.REATTACHMENT,
        TacticalState.LINE_MAINTENANCE,
        TacticalState.SOLO_TRANSITION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.REATTACHMENT: frozenset({
        TacticalState.LINE_MAINTENANCE,
        TacticalState.BANTE_FOLLOWING,
        TacticalState.LINE_FRAGMENTATION,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.SOLO_TRANSITION: frozenset({
        TacticalState.POSITION_COMPETITION,
        TacticalState.REATTACHMENT,
        TacticalState.FINAL_SPRINT_OR_OVERTAKE,
    }),
    TacticalState.FINAL_SPRINT_OR_OVERTAKE: frozenset({TacticalState.TERMINAL_FINISH}),
    TacticalState.TERMINAL_FINISH: frozenset(),
}


def validate_tactical_transition(previous: TacticalState, nxt: TacticalState) -> None:
    if nxt not in _ALLOWED[previous]:
        raise RealityTransportError(f"illegal tactical transition: {previous.value} -> {nxt.value}")


class LineObservationType(str, Enum):
    PRE_EVENT_EXPECTED_LINE = "PRE_EVENT_EXPECTED_LINE"
    LEGSHOW_OBSERVED_LINE = "LEGSHOW_OBSERVED_LINE"
    NONE_OR_UNAVAILABLE = "NONE_OR_UNAVAILABLE"
    POST_RACE_RECONSTRUCTED_LINE = "POST_RACE_RECONSTRUCTED_LINE"


@dataclass(frozen=True)
class LineMember:
    rider_id: str
    line_group_id: str
    line_position: int
    line_size: int

    def __post_init__(self) -> None:
        if not self.rider_id or not self.line_group_id:
            raise RealityTransportError("rider_id and line_group_id are required")
        if self.line_position < 1 or self.line_size < 1 or self.line_position > self.line_size:
            raise RealityTransportError("invalid line position/size")


@dataclass(frozen=True)
class LineSnapshot:
    race_id: str
    observation_type: LineObservationType
    snapshot_timestamp: str
    decision_timestamp: str
    source_url: str
    source_class: str
    provenance_sha: str
    active_rider_ids: tuple[str, ...]
    members: tuple[LineMember, ...]

    def __post_init__(self) -> None:
        if self.observation_type is LineObservationType.POST_RACE_RECONSTRUCTED_LINE:
            raise RealityTransportError("post-race reconstructed line is prohibited as PRE")
        if self.observation_type is LineObservationType.NONE_OR_UNAVAILABLE and self.members:
            raise RealityTransportError("NONE_OR_UNAVAILABLE cannot carry line members")
        if self.observation_type is not LineObservationType.NONE_OR_UNAVAILABLE and not self.members:
            raise RealityTransportError("line observation requires members")
        if _dt(self.snapshot_timestamp) > _dt(self.decision_timestamp):
            raise RealityTransportError("line snapshot occurs after decision cutoff")
        if not self.source_url or not self.source_class or not self.provenance_sha:
            raise RealityTransportError("line provenance is required")
        active = set(self.active_rider_ids)
        if len(active) != len(self.active_rider_ids):
            raise RealityTransportError("active_rider_ids must be unique")
        if any(m.rider_id not in active for m in self.members):
            raise RealityTransportError("line member not in active rider set")
        grouped: dict[str, list[LineMember]] = {}
        for m in self.members:
            grouped.setdefault(m.line_group_id, []).append(m)
        for group in grouped.values():
            claimed = {m.line_size for m in group}
            positions = {m.line_position for m in group}
            if len(claimed) != 1 or claimed != {len(group)} or positions != set(range(1, len(group) + 1)):
                raise RealityTransportError("line group size/positions are inconsistent")

    @property
    def is_observed_legshow(self) -> bool:
        return self.observation_type is LineObservationType.LEGSHOW_OBSERVED_LINE


@dataclass(frozen=True)
class WeatherObservation:
    venue_id: str
    station_id: str
    observation_timestamp: str
    decision_timestamp: str
    capture_timestamp: str
    wind_speed_mps: float | None
    wind_direction: str | None
    temperature_c: float | None
    precipitation_mm: float | None
    source_url: str
    source_class: str
    provenance_sha: str
    venue_station_mapping_source: str

    def __post_init__(self) -> None:
        if not self.venue_id or not self.station_id:
            raise RealityTransportError("venue_id and station_id are required")
        obs = _dt(self.observation_timestamp)
        decision = _dt(self.decision_timestamp)
        capture = _dt(self.capture_timestamp)
        if obs > decision:
            raise RealityTransportError("weather observation occurs after decision cutoff")
        if capture < obs:
            raise RealityTransportError("capture_timestamp cannot precede observation_timestamp")
        if self.wind_speed_mps is not None:
            v = float(self.wind_speed_mps)
            if not isfinite(v) or v < 0:
                raise RealityTransportError("wind_speed_mps must be finite and >= 0")
        if self.temperature_c is not None and not isfinite(float(self.temperature_c)):
            raise RealityTransportError("temperature_c must be finite")
        if self.precipitation_mm is not None:
            p = float(self.precipitation_mm)
            if not isfinite(p) or p < 0:
                raise RealityTransportError("precipitation_mm must be finite and >= 0")
        if (self.wind_speed_mps is None) != (self.wind_direction is None):
            raise RealityTransportError("wind speed and direction must be present together or both missing")
        if not self.source_url or not self.source_class or not self.provenance_sha:
            raise RealityTransportError("weather provenance is required")
        if not self.venue_station_mapping_source:
            raise RealityTransportError("explicit venue-to-station mapping provenance is required")


def assert_expected_line_not_upgraded(snapshot: LineSnapshot) -> None:
    if snapshot.observation_type is LineObservationType.PRE_EVENT_EXPECTED_LINE and snapshot.is_observed_legshow:
        raise RealityTransportError("expected line cannot be upgraded to leg-show observed line")
