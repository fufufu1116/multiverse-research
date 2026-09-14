"""Research-only retrospective for pre-boom trend signal extraction.

The goal is not to relabel famous outcomes after the fact. Historical cases are
used only to identify candidate leading signals that must later be frozen and
prospectively tested on unseen trends.
"""
from dataclasses import dataclass
from enum import Enum


class RetrospectiveDecision(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"
    CANDIDATE_PATTERN = "CANDIDATE_PATTERN"
    HINDSIGHT_RISK = "HINDSIGHT_RISK"


@dataclass(frozen=True)
class PreBoomWindow:
    days_before_peak: int
    niche_community_strength: int
    creator_or_celebrity_acceleration: int
    imitation_or_derivative_creation: int
    cross_region_spread: int
    search_or_save_intent: int
    scarcity_or_collectibility: int
    mainstream_retail_expansion: int
    visual_shareability: int
    source_evidence_count: int

    def __post_init__(self) -> None:
        if self.days_before_peak not in (30, 90, 180):
            raise ValueError("days_before_peak must be one of 30, 90, 180")
        for name, value in self.__dict__.items():
            if name == "days_before_peak":
                continue
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def assess_preboom_window(window: PreBoomWindow) -> dict:
    if window.source_evidence_count < 2:
        return {
            "decision": RetrospectiveDecision.INSUFFICIENT.value,
            "score": 0,
            "reasons": ["INSUFFICIENT_SOURCE_EVIDENCE"],
            "prospective_prediction_authorized": False,
            "live_execution_authorized": False,
        }

    early_signal_score = (
        window.niche_community_strength * 4
        + window.creator_or_celebrity_acceleration * 4
        + window.imitation_or_derivative_creation * 5
        + window.cross_region_spread * 5
        + window.search_or_save_intent * 5
        + window.scarcity_or_collectibility * 3
        + window.visual_shareability * 4
    )

    hindsight_penalty = 0
    if window.days_before_peak >= 90 and window.mainstream_retail_expansion >= 4:
        hindsight_penalty = 15

    score = max(0, min(100, early_signal_score - hindsight_penalty))
    reasons = []
    if hindsight_penalty:
        reasons.append("MAINSTREAM_CONFIRMATION_MAY_BE_TOO_LATE")

    if hindsight_penalty and score < 45:
        decision = RetrospectiveDecision.HINDSIGHT_RISK
    elif score >= 55:
        decision = RetrospectiveDecision.CANDIDATE_PATTERN
    else:
        decision = RetrospectiveDecision.INSUFFICIENT

    return {
        "decision": decision.value,
        "score": score,
        "reasons": reasons,
        "rule": "historical patterns are hypotheses only until frozen and tested prospectively on unseen cases",
        "prospective_prediction_authorized": False,
        "automatic_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
    }
