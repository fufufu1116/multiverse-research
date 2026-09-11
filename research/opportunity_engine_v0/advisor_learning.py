from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .advisor_track_record import AdvisorTrackRecord


_TRUSTED_SETTLEMENT_BASES = {
    "OFFICIAL",
    "DETERMINISTIC",
    "MEASURED_OUTCOME",
    "GOVERNED_REVIEW",
}


@dataclass(frozen=True)
class SettledAdvisorOutcome:
    outcome_id: str
    review_id: str
    provider: str
    model: str
    domain: str
    settlement_basis: str
    settled: bool
    confirmed_material_challenge: bool
    false_alarm_challenge: bool
    missed_material_blocker: bool
    calibration_error: float
    actual_cost_yen: float

    def __post_init__(self) -> None:
        for name in ("outcome_id", "review_id", "provider", "model", "domain", "settlement_basis"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if self.confirmed_material_challenge and self.false_alarm_challenge:
            raise ValueError("a challenge cannot be both confirmed and false alarm")
        if not isinstance(self.settled, bool):
            raise ValueError("settled must be boolean")
        for name in ("confirmed_material_challenge", "false_alarm_challenge", "missed_material_blocker"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")
        if not isinstance(self.calibration_error, (int, float)) or isinstance(self.calibration_error, bool) or not 0 <= self.calibration_error <= 1:
            raise ValueError("calibration_error must be between 0 and 1")
        if not isinstance(self.actual_cost_yen, (int, float)) or isinstance(self.actual_cost_yen, bool) or self.actual_cost_yen < 0:
            raise ValueError("actual_cost_yen must be nonnegative")


def compile_advisor_track_records(
    outcomes: Iterable[SettledAdvisorOutcome],
) -> Tuple[AdvisorTrackRecord, ...]:
    """Build advisor records only from settled, externally checkable outcomes.

    Unsettled predictions and untrusted/self-reported settlement bases are excluded.
    Duplicate outcome ids or duplicate provider/model review settlements fail closed.
    """
    accepted: list[SettledAdvisorOutcome] = []
    seen_outcomes: set[str] = set()
    seen_reviews: set[tuple[str, str, str]] = set()

    for item in outcomes:
        if not isinstance(item, SettledAdvisorOutcome):
            raise ValueError("outcomes must contain SettledAdvisorOutcome values")
        if item.outcome_id in seen_outcomes:
            raise ValueError("duplicate outcome_id")
        seen_outcomes.add(item.outcome_id)
        review_key = (item.review_id, item.provider, item.model)
        if review_key in seen_reviews:
            raise ValueError("duplicate settled review for provider/model")
        seen_reviews.add(review_key)
        if not item.settled:
            continue
        if item.settlement_basis not in _TRUSTED_SETTLEMENT_BASES:
            continue
        accepted.append(item)

    grouped: dict[tuple[str, str, str], list[SettledAdvisorOutcome]] = {}
    for item in accepted:
        grouped.setdefault((item.provider, item.model, item.domain), []).append(item)

    records = []
    for (provider, model, domain), items in sorted(grouped.items()):
        n = len(items)
        records.append(
            AdvisorTrackRecord(
                provider=provider,
                model=model,
                domain=domain,
                completed_reviews=n,
                confirmed_material_challenges=sum(item.confirmed_material_challenge for item in items),
                false_alarm_challenges=sum(item.false_alarm_challenge for item in items),
                missed_material_blockers=sum(item.missed_material_blocker for item in items),
                calibration_error=sum(float(item.calibration_error) for item in items) / n,
                average_cost_yen=sum(float(item.actual_cost_yen) for item in items) / n,
            )
        )
    return tuple(records)
