from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NarrowWedge:
    name: str
    character_content_fit: int
    short_video_fit: int
    repeat_intent: int
    owned_state_value: int
    shareable_output: int
    monetization_fit: int
    ai_substitution_risk: int
    competition_density: int
    safety_regulatory_risk: int
    owner_operating_burden: int
    evidence_strength: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        for field_name in (
            "character_content_fit",
            "short_video_fit",
            "repeat_intent",
            "owned_state_value",
            "shareable_output",
            "monetization_fit",
            "ai_substitution_risk",
            "competition_density",
            "safety_regulatory_risk",
            "owner_operating_burden",
            "evidence_strength",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be an integer from 0 to 5")


def rank_narrow_wedge(wedge: NarrowWedge) -> dict[str, object]:
    """Prioritize a narrow entry market without pretending desk research proves demand.

    The score rewards content/distribution fit, recurring owned state, shareable output
    and monetization. It penalizes generic-AI substitution, crowding, safety/regulatory
    risk and owner burden. Weak evidence caps readiness even when the theoretical score
    is high.
    """
    positive = (
        wedge.character_content_fit * 4
        + wedge.short_video_fit * 4
        + wedge.repeat_intent * 5
        + wedge.owned_state_value * 6
        + wedge.shareable_output * 4
        + wedge.monetization_fit * 4
    )
    penalty = (
        wedge.ai_substitution_risk * 5
        + wedge.competition_density * 4
        + wedge.safety_regulatory_risk * 6
        + wedge.owner_operating_burden * 3
    )
    raw_score = max(0, min(100, positive - penalty))

    blockers: list[str] = []
    if wedge.owned_state_value < 3:
        blockers.append("OWNED_STATE_TOO_WEAK")
    if wedge.repeat_intent < 3:
        blockers.append("REPEAT_INTENT_TOO_WEAK")
    if wedge.safety_regulatory_risk >= 4:
        blockers.append("SAFETY_OR_REGULATORY_RISK_HIGH")
    if wedge.ai_substitution_risk >= 5 and wedge.owned_state_value < 5:
        blockers.append("GENERIC_AI_SUBSTITUTION_EXTREME")
    if wedge.evidence_strength < 2:
        blockers.append("EVIDENCE_TOO_WEAK_FOR_WINNER_SELECTION")

    if blockers:
        posture = "RESEARCH_OR_REDESIGN"
    elif wedge.evidence_strength < 4:
        posture = "PRIORITY_RESEARCH_ONLY" if raw_score >= 55 else "SECONDARY_RESEARCH_ONLY"
    elif raw_score >= 65:
        posture = "CANDIDATE_FOR_FROZEN_SMALL_TEST_FORECAST"
    elif raw_score >= 45:
        posture = "SECONDARY_RESEARCH_ONLY"
    else:
        posture = "LOW_PRIORITY"

    moat_questions = (
        "What user-specific state becomes more valuable after every session?",
        "What can a generic AI answer but not reliably own, measure or accumulate?",
        "What shareable output naturally sends users back toward the owned product?",
        "What recurring friction is removed strongly enough to justify payment?",
        "What incumbent or substitute already owns this job and why would a user switch?",
    )

    return {
        "name": wedge.name,
        "score": raw_score,
        "posture": posture,
        "blockers": blockers,
        "evidence_strength": wedge.evidence_strength,
        "winner_claim_authorized": False,
        "small_live_test_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "moat_questions": moat_questions,
    }
