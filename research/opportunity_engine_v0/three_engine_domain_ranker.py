from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .three_engine_funnel import ThreeEngineSurface, score_three_engine_surface


@dataclass(frozen=True)
class DomainResearchState:
    surface: ThreeEngineSurface
    competitor_research_complete: bool
    official_or_primary_evidence_count: int
    measured_outcome_count: int = 0
    incumbent_pressure: int = 0
    natural_loop_strength: int = 0

    def __post_init__(self) -> None:
        for name in ("official_or_primary_evidence_count", "measured_outcome_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("incumbent_pressure", "natural_loop_strength"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")
        if not isinstance(self.competitor_research_complete, bool):
            raise ValueError("competitor_research_complete must be boolean")


def rank_domain_research(states: Iterable[DomainResearchState]) -> dict[str, object]:
    """Prioritize domains without confusing hypothesis score with evidence.

    Raw three-engine fit can choose what to research next. It cannot authorize
    adoption. Missing competitor research and sparse primary evidence reduce
    confidence; measured outcomes are tracked separately and never fabricated.
    """
    rows: list[dict[str, object]] = []
    for state in states:
        raw = score_three_engine_surface(state.surface)
        evidence_penalty = 0
        reasons: list[str] = []
        if not state.competitor_research_complete:
            evidence_penalty += 15
            reasons.append("COMPETITOR_RESEARCH_INCOMPLETE")
        if state.official_or_primary_evidence_count < 2:
            evidence_penalty += 10
            reasons.append("PRIMARY_EVIDENCE_SPARSE")
        incumbent_penalty = state.incumbent_pressure * 3
        loop_bonus = state.natural_loop_strength * 2
        priority_score = max(0, min(100, int(raw["score"]) - evidence_penalty - incumbent_penalty + loop_bonus))
        rows.append({
            "domain": state.surface.domain,
            "raw_hypothesis_score": raw["score"],
            "research_priority_score": priority_score,
            "research_reasons": reasons,
            "official_or_primary_evidence_count": state.official_or_primary_evidence_count,
            "measured_outcome_count": state.measured_outcome_count,
            "competitor_research_complete": state.competitor_research_complete,
            "incumbent_pressure": state.incumbent_pressure,
            "natural_loop_strength": state.natural_loop_strength,
            "adoption_authorized": False,
            "live_execution_authorized": False,
        })

    rows.sort(key=lambda row: (-int(row["research_priority_score"]), str(row["domain"])))
    return {
        "ranking": rows,
        "next_domain_to_research": rows[0]["domain"] if rows else None,
        "ranking_is_research_priority_only": True,
        "measured_winner_declared": False,
        "adoption_authorized": False,
        "live_execution_authorized": False,
    }
