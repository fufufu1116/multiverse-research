"""Single completion spine for the Opportunity Engine research prototype.

This module deliberately does not invent another scoring system. It composes
existing decisions so research can move through one path without duplicating
logic: discover -> freeze forecast -> customer value -> contribution economics
-> first-100 evidence -> mission readiness.

All authority remains false. This is a coordination layer only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .customer_contribution import ContributionLoop, assess_contribution_loop
from .customer_value_loop import CustomerValueReturn, assess_customer_value_return
from .hundred_user_general import HundredUserEvidence, assess_hundred_user_stage
from .trend_forecast import TrendSignalSnapshot, assess_trend_signal


@dataclass(frozen=True)
class CompletionSpineInput:
    trend_snapshot: TrendSignalSnapshot
    customer_value: CustomerValueReturn
    contribution_loop: ContributionLoop
    hundred_user_evidence: HundredUserEvidence | None = None
    competitor_research_complete: bool = False
    legal_or_safety_hold: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.competitor_research_complete, bool):
            raise ValueError("competitor_research_complete must be boolean")
        if not isinstance(self.legal_or_safety_hold, bool):
            raise ValueError("legal_or_safety_hold must be boolean")


def build_completion_spine(inp: CompletionSpineInput) -> dict[str, Any]:
    """Compose existing layer outputs into one fail-closed research path.

    The spine never upgrades a weaker decision. It only carries forward blockers
    from source modules and identifies the next useful research action.
    """
    trend = assess_trend_signal(inp.trend_snapshot)
    value = assess_customer_value_return(inp.customer_value)
    contribution = assess_contribution_loop(inp.contribution_loop)
    hundred = (
        assess_hundred_user_stage(inp.hundred_user_evidence)
        if inp.hundred_user_evidence is not None
        else None
    )

    blockers: list[str] = []
    if inp.legal_or_safety_hold:
        blockers.append("LEGAL_OR_SAFETY_HOLD")
    if not inp.competitor_research_complete:
        blockers.append("COMPETITOR_RESEARCH_INCOMPLETE")
    if trend["posture"] != "FORECAST_CANDIDATE":
        blockers.append(f"TREND_{trend['posture']}")
    if value["decision"] != "VALUE_LOOP_CANDIDATE":
        blockers.append(f"CUSTOMER_VALUE_{value['decision']}")
    if contribution["decision"] != "TESTABLE":
        blockers.append(f"CONTRIBUTION_{contribution['decision']}")

    if hundred is None:
        blockers.append("HUNDRED_USER_EVIDENCE_NOT_AVAILABLE")
    elif hundred["decision"] != "NEXT_STAGE_RESEARCH_CANDIDATE":
        blockers.append("HUNDRED_USER_STAGE_NOT_PROMOTABLE")

    if inp.legal_or_safety_hold:
        posture = "HOLD_FAIL_CLOSED"
        next_action = "resolve legal or safety blocker before further promotion research"
    elif "COMPETITOR_RESEARCH_INCOMPLETE" in blockers:
        posture = "RESEARCH_ONLY"
        next_action = "complete competitor/substitute/general-AI research once; reuse it downstream"
    elif any(x.startswith("TREND_") for x in blockers):
        posture = "RESEARCH_ONLY"
        next_action = "improve or replace the candidate using fresh pre-outcome evidence"
    elif any(x.startswith("CUSTOMER_VALUE_") for x in blockers):
        posture = "RESEARCH_ONLY"
        next_action = "redesign customer value so users benefit even without purchase"
    elif any(x.startswith("CONTRIBUTION_") for x in blockers):
        posture = "RESEARCH_ONLY"
        next_action = "repair contribution economics, transparency, consent or abuse resistance"
    elif "HUNDRED_USER_EVIDENCE_NOT_AVAILABLE" in blockers:
        posture = "READY_FOR_GOVERNED_HUNDRED_USER_GATE"
        next_action = "prepare one frozen first-100 experiment packet for owner-governed authorization"
    elif "HUNDRED_USER_STAGE_NOT_PROMOTABLE" in blockers:
        posture = "ITERATE_HUNDRED_USER_RESEARCH"
        next_action = "iterate only the failing first-100 metrics; do not widen scope"
    else:
        posture = "READY_FOR_NEXT_GOVERNED_GATE"
        next_action = "package settled evidence for the next governed decision; do not add new features"

    return {
        "candidate_id": inp.trend_snapshot.candidate_id,
        "posture": posture,
        "next_action": next_action,
        "blockers": blockers,
        "trend": trend,
        "customer_value": value,
        "contribution": contribution,
        "hundred_user": hundred,
        "forecast_commitment": trend["forecast_commitment"],
        "single_path_rule": True,
        "duplicate_scoring_forbidden": True,
        "reuse_existing_module_outputs": True,
        "automatic_execution_authorized": False,
        "provider_call_authorized": False,
        "recruitment_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "payment_collection_authorized": False,
        "adoption_authorized": False,
        "merge_authorized": False,
        "runtime_activation_authorized": False,
        "owner_gate_still_required": True,
    }
