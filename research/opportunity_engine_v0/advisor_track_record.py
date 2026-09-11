from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AdvisorTrackRecord:
    provider: str
    model: str
    domain: str
    completed_reviews: int
    confirmed_material_challenges: int
    false_alarm_challenges: int
    missed_material_blockers: int
    calibration_error: float
    average_cost_yen: float

    def __post_init__(self) -> None:
        for name in ("provider", "model", "domain"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        for name in (
            "completed_reviews",
            "confirmed_material_challenges",
            "false_alarm_challenges",
            "missed_material_blockers",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.confirmed_material_challenges + self.false_alarm_challenges > self.completed_reviews:
            raise ValueError("challenge counts cannot exceed completed reviews")
        if self.missed_material_blockers > self.completed_reviews:
            raise ValueError("missed blockers cannot exceed completed reviews")
        if not isinstance(self.calibration_error, (int, float)) or isinstance(self.calibration_error, bool) or not 0 <= self.calibration_error <= 1:
            raise ValueError("calibration_error must be between 0 and 1")
        if not isinstance(self.average_cost_yen, (int, float)) or isinstance(self.average_cost_yen, bool) or self.average_cost_yen < 0:
            raise ValueError("average_cost_yen must be nonnegative")


@dataclass(frozen=True)
class AdvisorScore:
    provider: str
    model: str
    domain: str
    score: float
    evidence_weight: float
    sample_size: int
    status: str
    reasons: Tuple[str, ...]


def score_advisor(record: AdvisorTrackRecord, *, prior_score: float = 50.0, full_weight_reviews: int = 20) -> AdvisorScore:
    """Score advisory usefulness conservatively, shrinking sparse history to neutral.

    The score rewards confirmed material challenges and calibration while heavily
    penalizing missed material blockers. Sparse histories are not allowed to create
    strong model rankings after one or two lucky outcomes.
    """
    if not isinstance(prior_score, (int, float)) or isinstance(prior_score, bool) or not 0 <= prior_score <= 100:
        raise ValueError("prior_score must be between 0 and 100")
    if not isinstance(full_weight_reviews, int) or isinstance(full_weight_reviews, bool) or full_weight_reviews < 5:
        raise ValueError("full_weight_reviews must be an integer >= 5")

    n = record.completed_reviews
    evidence_weight = min(1.0, n / float(full_weight_reviews))
    if n == 0:
        raw = float(prior_score)
        status = "UNPROVEN"
        reasons = ("NO_OUTCOME_HISTORY",)
    else:
        confirmed_rate = record.confirmed_material_challenges / n
        false_alarm_rate = record.false_alarm_challenges / n
        miss_rate = record.missed_material_blockers / n
        calibration_quality = 1.0 - float(record.calibration_error)
        raw = (
            50.0
            + confirmed_rate * 30.0
            + calibration_quality * 20.0
            - false_alarm_rate * 20.0
            - miss_rate * 45.0
        )
        raw = max(0.0, min(100.0, raw))
        status = "ESTABLISHED" if n >= full_weight_reviews else "LIMITED_HISTORY"
        reason_list = ["OUTCOME_WEIGHTED"]
        if record.missed_material_blockers:
            reason_list.append("MISSED_BLOCKER_PENALTY")
        if record.false_alarm_challenges:
            reason_list.append("FALSE_ALARM_PENALTY")
        if record.confirmed_material_challenges:
            reason_list.append("CONFIRMED_CHALLENGE_CREDIT")
        reasons = tuple(reason_list)

    score = float(prior_score) * (1.0 - evidence_weight) + raw * evidence_weight
    return AdvisorScore(
        provider=record.provider,
        model=record.model,
        domain=record.domain,
        score=round(score, 2),
        evidence_weight=round(evidence_weight, 3),
        sample_size=n,
        status=status,
        reasons=reasons,
    )


def rank_advisors(
    records: Tuple[AdvisorTrackRecord, ...],
    *,
    domain: str,
    max_advisors: int = 2,
    max_total_expected_cost_yen: float = 1000.0,
    require_cross_provider_when_available: bool = True,
) -> tuple[AdvisorScore, ...]:
    """Rank advisors by measured history while preserving provider diversity.

    This function only recommends an advisory lineup. It does not authorize a
    provider call, credentials, spend, execution, publication or adoption.
    """
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain is required")
    if not isinstance(max_advisors, int) or isinstance(max_advisors, bool) or not 1 <= max_advisors <= 4:
        raise ValueError("max_advisors must be between 1 and 4")
    if not isinstance(max_total_expected_cost_yen, (int, float)) or isinstance(max_total_expected_cost_yen, bool) or max_total_expected_cost_yen < 0:
        raise ValueError("max_total_expected_cost_yen must be nonnegative")

    candidates = [record for record in records if record.domain == domain]
    scored = [(score_advisor(record), record) for record in candidates]
    scored.sort(
        key=lambda row: (
            row[0].score,
            row[0].evidence_weight,
            -row[1].average_cost_yen,
            row[0].provider,
            row[0].model,
        ),
        reverse=True,
    )

    selected: list[AdvisorScore] = []
    selected_providers: set[str] = set()
    total_cost = 0.0
    available_providers = {record.provider for _, record in scored}

    for advisor, record in scored:
        if len(selected) >= max_advisors:
            break
        if total_cost + record.average_cost_yen > max_total_expected_cost_yen:
            continue
        if (
            require_cross_provider_when_available
            and len(selected) >= 1
            and len(available_providers) >= 2
            and record.provider in selected_providers
            and any(
                other_record.provider not in selected_providers
                and total_cost + other_record.average_cost_yen <= max_total_expected_cost_yen
                for _, other_record in scored
            )
        ):
            continue
        selected.append(advisor)
        selected_providers.add(record.provider)
        total_cost += float(record.average_cost_yen)

    return tuple(selected)
