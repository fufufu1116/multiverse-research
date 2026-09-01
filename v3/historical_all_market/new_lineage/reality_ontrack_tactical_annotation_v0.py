"""Burned on-track tactical annotation mechanics with explicit denominators."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable, Mapping


class TacticalAnnotationError(ValueError):
    pass


EVENT_TYPES = {
    "INITIATIVE_ATTACK",
    "INITIATIVE_CONFLICT",
    "BANTE_FOLLOW",
    "BLOCK_OR_POSITION_DEFENSE",
    "POSITION_COMPETITION",
    "LINE_FRAGMENT",
    "SWITCH",
    "REATTACH",
    "SOLO_TRANSITION",
    "FINAL_SPRINT_OR_OVERTAKE",
}

PHASES = {
    "START_TO_FORMATION_SETTLE",
    "MID_RACE_FORMATION",
    "BELL_APPROACH",
    "FINAL_LAP_HOME_TO_BACK",
    "FINAL_BACK_TO_FINISH",
}

VISIBILITY = {"CLEAR", "PARTIAL", "UNOBSERVABLE"}
LABELS = {"PRESENT", "ABSENT", "UNKNOWN"}


@dataclass(frozen=True)
class AnnotationRecord:
    annotation_id: str
    race_id: str
    annotator_id: str
    source_url: str
    event_type: str
    phase: str
    event_time_seconds: float | None
    actor_car: int | None
    counterparty_car: int | None
    before_line_state: str
    after_line_state: str
    visibility: str
    label: str
    provenance_sha256: str
    candidate_outputs_hidden: bool
    finish_order_recorded: bool
    payout_recorded: bool

    def __post_init__(self) -> None:
        if not self.annotation_id or not self.race_id or not self.annotator_id:
            raise TacticalAnnotationError("annotation, race and annotator identifiers are required")
        if not self.source_url.startswith("https://"):
            raise TacticalAnnotationError("https source required")
        if self.event_type not in EVENT_TYPES:
            raise TacticalAnnotationError("unknown event type")
        if self.phase not in PHASES:
            raise TacticalAnnotationError("unknown race phase")
        if self.visibility not in VISIBILITY:
            raise TacticalAnnotationError("unknown visibility")
        if self.label not in LABELS:
            raise TacticalAnnotationError("unknown label")
        if self.visibility == "UNOBSERVABLE" and self.label != "UNKNOWN":
            raise TacticalAnnotationError("unobservable evidence must remain UNKNOWN")
        if self.event_time_seconds is not None:
            if not isfinite(float(self.event_time_seconds)) or float(self.event_time_seconds) < 0:
                raise TacticalAnnotationError("event time must be finite and non-negative")
        for car in (self.actor_car, self.counterparty_car):
            if car is not None and not 1 <= int(car) <= 9:
                raise TacticalAnnotationError("car number outside supported field")
        if len(self.provenance_sha256) != 64:
            raise TacticalAnnotationError("sha256 provenance required")
        if self.candidate_outputs_hidden is not True:
            raise TacticalAnnotationError("candidate outputs must be hidden from annotation")
        if self.finish_order_recorded or self.payout_recorded:
            raise TacticalAnnotationError("outcome/economic fields are outside this annotation contract")


@dataclass(frozen=True)
class OpportunityRecord:
    opportunity_id: str
    race_id: str
    event_type: str
    phase: str
    actor_car: int | None
    counterparty_car: int | None
    eligible: bool
    observable: bool
    label: str

    def __post_init__(self) -> None:
        if not self.opportunity_id or not self.race_id:
            raise TacticalAnnotationError("opportunity and race identifiers are required")
        if self.event_type not in EVENT_TYPES or self.phase not in PHASES:
            raise TacticalAnnotationError("unknown event type or phase")
        if self.label not in LABELS:
            raise TacticalAnnotationError("unknown opportunity label")
        if not self.eligible and self.label != "UNKNOWN":
            raise TacticalAnnotationError("ineligible opportunity cannot carry event label")
        if not self.observable and self.label != "UNKNOWN":
            raise TacticalAnnotationError("unobservable opportunity must remain UNKNOWN")


@dataclass(frozen=True)
class RateRange:
    event_type: str
    positives: int
    denominator: int
    point: float
    wilson95_low: float
    wilson95_high: float
    status: str = "PILOT_DIAGNOSTIC_ONLY_NOT_TRUTH_ADMITTED"


def wilson_interval(positives: int, denominator: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if denominator <= 0 or positives < 0 or positives > denominator:
        raise TacticalAnnotationError("valid positive denominator required")
    p = positives / denominator
    z2 = z * z
    scale = 1.0 + z2 / denominator
    center = (p + z2 / (2.0 * denominator)) / scale
    half = z * sqrt((p * (1.0 - p) + z2 / (4.0 * denominator)) / denominator) / scale
    return max(0.0, center - half), min(1.0, center + half)


def estimate_pilot_rate(event_type: str, opportunities: Iterable[OpportunityRecord]) -> RateRange:
    if event_type not in EVENT_TYPES:
        raise TacticalAnnotationError("unknown event type")
    usable = [
        row for row in opportunities
        if row.event_type == event_type
        and row.eligible
        and row.observable
        and row.label in {"PRESENT", "ABSENT"}
    ]
    if not usable:
        raise TacticalAnnotationError("no observable eligible denominator for event")
    positives = sum(row.label == "PRESENT" for row in usable)
    low, high = wilson_interval(positives, len(usable))
    return RateRange(event_type, positives, len(usable), positives / len(usable), low, high)


@dataclass(frozen=True)
class AgreementReport:
    comparable: int
    agreements: int
    raw_agreement: float | None
    cohen_kappa: float | None


def agreement_report(
    left: Mapping[str, str],
    right: Mapping[str, str],
) -> AgreementReport:
    keys = sorted(set(left) & set(right))
    pairs = [(left[k], right[k]) for k in keys if left[k] in {"PRESENT", "ABSENT"} and right[k] in {"PRESENT", "ABSENT"}]
    n = len(pairs)
    if n == 0:
        return AgreementReport(0, 0, None, None)
    agree = sum(a == b for a, b in pairs)
    raw = agree / n
    left_present = sum(a == "PRESENT" for a, _ in pairs) / n
    right_present = sum(b == "PRESENT" for _, b in pairs) / n
    expected = left_present * right_present + (1.0 - left_present) * (1.0 - right_present)
    if expected >= 1.0:
        kappa = None
    else:
        kappa = (raw - expected) / (1.0 - expected)
    return AgreementReport(n, agree, raw, kappa)


def truth_rate_admitted() -> bool:
    return False
