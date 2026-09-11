from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketDiscoveryCandidate:
    domain: str
    trend_content_fit: int
    character_brand_fit: int
    repeat_intent: int
    owned_state_value: int
    shareable_output: int
    monetization_fit: int
    ai_substitution_resistance: int
    gross_margin_potential: int
    competition_density: int
    regulatory_harm_risk: int
    platform_dependency: int
    owner_operating_burden: int
    evidence_strength: int

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValueError("domain is required")
        for name, value in self.__dict__.items():
            if name == "domain":
                continue
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def assess_market(candidate: MarketDiscoveryCandidate) -> dict[str, object]:
    """Prioritize research markets; never treat a hypothesis score as market proof."""
    upside = (
        candidate.trend_content_fit * 4
        + candidate.character_brand_fit * 4
        + candidate.repeat_intent * 5
        + candidate.owned_state_value * 6
        + candidate.shareable_output * 4
        + candidate.monetization_fit * 5
        + candidate.ai_substitution_resistance * 5
        + candidate.gross_margin_potential * 4
    )
    risk = (
        candidate.competition_density * 3
        + candidate.regulatory_harm_risk * 7
        + candidate.platform_dependency * 4
        + candidate.owner_operating_burden * 3
    )
    evidence_penalty = (5 - candidate.evidence_strength) * 6
    score = max(0, min(100, upside - risk - evidence_penalty))

    blockers: list[str] = []
    if candidate.regulatory_harm_risk >= 4:
        blockers.append("HIGH_REGULATORY_OR_USER_HARM_RISK")
    if candidate.owned_state_value < 3:
        blockers.append("WEAK_OWNED_STATE_MOAT")
    if candidate.repeat_intent < 3:
        blockers.append("WEAK_REPEAT_INTENT")
    if candidate.evidence_strength < 2:
        blockers.append("INSUFFICIENT_EXTERNAL_EVIDENCE")

    if blockers:
        posture = "RESEARCH_OR_REDESIGN"
    elif score >= 65:
        posture = "TOP_RESEARCH_CANDIDATE"
    elif score >= 45:
        posture = "SECONDARY_RESEARCH_CANDIDATE"
    else:
        posture = "LOW_PRIORITY"

    return {
        "domain": candidate.domain,
        "risk_adjusted_research_score": score,
        "posture": posture,
        "blockers": tuple(blockers),
        "score_is_hypothesis_only": True,
        "winner_claim_authorized": False,
        "live_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
    }


def rank_markets(candidates: tuple[MarketDiscoveryCandidate, ...]) -> tuple[dict[str, object], ...]:
    assessed = [assess_market(c) for c in candidates]
    return tuple(sorted(assessed, key=lambda row: int(row["risk_adjusted_research_score"]), reverse=True))
