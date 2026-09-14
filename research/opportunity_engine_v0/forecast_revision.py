from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .forecast_ledger import ForecastCard, forecast_commitment, verify_forecast_commitment


class RevisionDecision(str, Enum):
    KEEP_CURRENT = "KEEP_CURRENT"
    FRESH_RESEARCH_REQUIRED = "FRESH_RESEARCH_REQUIRED"
    REJECT_ADAPTATION = "REJECT_ADAPTATION"


_ALLOWED_SHOCK_VERDICTS = {"REJECT", "HOLD", "ADAPT", "CONSTRAINT_INVERSION"}


@dataclass(frozen=True)
class ExternalChange:
    change_id: str
    observed_at: str
    change_type: str
    evidence_refs: Tuple[str, ...]
    materiality: int

    def __post_init__(self) -> None:
        if not self.change_id.strip() or not self.observed_at.strip() or not self.change_type.strip():
            raise ValueError("change identity, time and type are required")
        if not self.evidence_refs:
            raise ValueError("evidence_refs must not be empty")
        if not isinstance(self.materiality, int) or isinstance(self.materiality, bool) or not 0 <= self.materiality <= 5:
            raise ValueError("materiality must be an integer from 0 to 5")


def assess_forecast_revision_need(
    *,
    current_card: ForecastCard,
    current_commitment: str,
    change: ExternalChange,
    shock_verdict: str,
) -> dict[str, object]:
    """Decide whether new external evidence requires a new forecast lineage.

    The frozen forecast is never edited. Material changes trigger fresh research first;
    only after that research may a separate ForecastCard be created with a new id and
    commitment. This preserves prediction-vs-reality history.
    """
    if not verify_forecast_commitment(current_card, current_commitment):
        raise ValueError("current forecast commitment mismatch")
    if shock_verdict not in _ALLOWED_SHOCK_VERDICTS:
        raise ValueError("unexpected shock_verdict")

    if shock_verdict == "REJECT":
        decision = RevisionDecision.REJECT_ADAPTATION
        reasons = ("SHOCK_ADAPTATION_REJECTED",)
    elif change.materiality >= 3 or shock_verdict in {"ADAPT", "CONSTRAINT_INVERSION"}:
        decision = RevisionDecision.FRESH_RESEARCH_REQUIRED
        reasons = ("MATERIAL_EXTERNAL_CHANGE", "PRESERVE_FROZEN_FORECAST")
    else:
        decision = RevisionDecision.KEEP_CURRENT
        reasons = ("CHANGE_NOT_MATERIAL_ENOUGH_FOR_REVISION",)

    return {
        "decision": decision.value,
        "current_forecast_id": current_card.forecast_id,
        "current_forecast_commitment": current_commitment,
        "change_id": change.change_id,
        "change_type": change.change_type,
        "evidence_refs": list(change.evidence_refs),
        "shock_verdict": shock_verdict,
        "fresh_research_required": decision == RevisionDecision.FRESH_RESEARCH_REQUIRED,
        "new_forecast_must_use_new_id": True,
        "old_forecast_mutation_authorized": False,
        "automatic_execution_authorized": False,
        "adoption_authorized": False,
        "reasons": list(reasons),
        "note": "External change can trigger research and a new forecast version, never rewriting the frozen historical prediction.",
    }


def bind_successor_forecast(
    *,
    prior_card: ForecastCard,
    prior_commitment: str,
    successor_card: ForecastCard,
    triggering_change_id: str,
) -> dict[str, object]:
    """Bind a new forecast to its immutable predecessor without replacing it."""
    if not verify_forecast_commitment(prior_card, prior_commitment):
        raise ValueError("prior forecast commitment mismatch")
    if successor_card.forecast_id == prior_card.forecast_id:
        raise ValueError("successor forecast must use a new forecast_id")
    if not triggering_change_id.strip():
        raise ValueError("triggering_change_id is required")
    return {
        "prior_forecast_id": prior_card.forecast_id,
        "prior_commitment": prior_commitment,
        "successor_forecast_id": successor_card.forecast_id,
        "successor_commitment": forecast_commitment(successor_card),
        "triggering_change_id": triggering_change_id,
        "prior_forecast_preserved": True,
        "automatic_execution_authorized": False,
        "adoption_authorized": False,
    }
