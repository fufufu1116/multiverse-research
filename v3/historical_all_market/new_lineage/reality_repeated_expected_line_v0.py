"""Repeated provider expected-line snapshot foundation.

This module models point-in-time pre-event line forecasts only. It contains no
fitted transition rates, finish effects, model calls, or network access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


class RepeatedExpectedLineError(ValueError):
    pass


def _dt(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise RepeatedExpectedLineError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RepeatedExpectedLineError("timezone-aware timestamp required")
    return parsed


def _canonical_groups(groups: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    # Group ordering on a provider page is presentation-level; within-group order
    # is meaningful because it encodes front-to-back expected line order.
    return tuple(sorted(groups, key=lambda g: (g[0], len(g), g)))


@dataclass(frozen=True)
class ExpectedLinePointInTime:
    race_id: str
    active_car_numbers: tuple[int, ...]
    groups: tuple[tuple[int, ...], ...]
    capture_timestamp: str
    decision_timestamp: str
    source_url: str
    provider_name: str
    provenance_sha: str
    observation_type: str = "PRE_EVENT_EXPECTED_LINE"

    def __post_init__(self) -> None:
        if self.observation_type != "PRE_EVENT_EXPECTED_LINE":
            raise RepeatedExpectedLineError("only PRE_EVENT_EXPECTED_LINE is admitted")
        if not self.race_id or not self.source_url or not self.provider_name or not self.provenance_sha:
            raise RepeatedExpectedLineError("identity/provenance fields required")
        capture = _dt(self.capture_timestamp)
        decision = _dt(self.decision_timestamp)
        if capture > decision:
            raise RepeatedExpectedLineError("capture after decision cutoff")
        active = tuple(self.active_car_numbers)
        if len(active) < 3 or len(set(active)) != len(active):
            raise RepeatedExpectedLineError("active field invalid")
        if any((not isinstance(c, int)) or c < 1 for c in active):
            raise RepeatedExpectedLineError("active car numbers must be positive integers")
        if not self.groups:
            raise RepeatedExpectedLineError("at least one expected group required")
        flat = tuple(c for group in self.groups for c in group)
        if any(not group for group in self.groups):
            raise RepeatedExpectedLineError("empty line group prohibited")
        if any((not isinstance(c, int)) or c < 1 for c in flat):
            raise RepeatedExpectedLineError("group car numbers must be positive integers")
        if len(flat) != len(active) or set(flat) != set(active):
            raise RepeatedExpectedLineError("groups must partition active field exactly")
        if len(set(flat)) != len(flat):
            raise RepeatedExpectedLineError("duplicate car across groups")

    @property
    def signature(self) -> tuple[tuple[int, ...], ...]:
        return _canonical_groups(self.groups)

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(sorted((len(group) for group in self.groups), reverse=True))


@dataclass(frozen=True)
class ExpectedLineChange:
    race_id: str
    earlier_capture_timestamp: str
    later_capture_timestamp: str
    earlier_signature: tuple[tuple[int, ...], ...]
    later_signature: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class ExpectedLineSeries:
    race_id: str
    snapshots: tuple[ExpectedLinePointInTime, ...]

    def __post_init__(self) -> None:
        if not self.race_id or not self.snapshots:
            raise RepeatedExpectedLineError("non-empty race series required")
        if any(s.race_id != self.race_id for s in self.snapshots):
            raise RepeatedExpectedLineError("mixed race IDs")
        active_sets = {tuple(sorted(s.active_car_numbers)) for s in self.snapshots}
        if len(active_sets) != 1:
            raise RepeatedExpectedLineError("active field changed inside one series; create a new program snapshot")
        decisions = {_dt(s.decision_timestamp) for s in self.snapshots}
        if len(decisions) != 1:
            raise RepeatedExpectedLineError("decision cutoff drift inside one series")
        captures = [_dt(s.capture_timestamp) for s in self.snapshots]
        if captures != sorted(captures):
            raise RepeatedExpectedLineError("snapshots must be chronological")
        if len(set(captures)) != len(captures):
            raise RepeatedExpectedLineError("duplicate capture timestamp")

    def latest_available_by(self, decision_timestamp: str) -> ExpectedLinePointInTime:
        decision = _dt(decision_timestamp)
        eligible = [s for s in self.snapshots if _dt(s.capture_timestamp) <= decision]
        if not eligible:
            raise RepeatedExpectedLineError("no expected-line snapshot available by cutoff")
        return eligible[-1]

    def changes(self) -> tuple[ExpectedLineChange, ...]:
        events: list[ExpectedLineChange] = []
        for earlier, later in zip(self.snapshots, self.snapshots[1:]):
            if earlier.signature != later.signature:
                events.append(
                    ExpectedLineChange(
                        race_id=self.race_id,
                        earlier_capture_timestamp=earlier.capture_timestamp,
                        later_capture_timestamp=later.capture_timestamp,
                        earlier_signature=earlier.signature,
                        later_signature=later.signature,
                    )
                )
        return tuple(events)

    def unchanged_intervals(self) -> int:
        return sum(
            earlier.signature == later.signature
            for earlier, later in zip(self.snapshots, self.snapshots[1:])
        )


def validate_series_collection(series: Sequence[ExpectedLineSeries]) -> None:
    if not series:
        raise RepeatedExpectedLineError("at least one series required")
    race_ids = [s.race_id for s in series]
    if len(set(race_ids)) != len(race_ids):
        raise RepeatedExpectedLineError("duplicate race series")
