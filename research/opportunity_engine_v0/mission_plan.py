from __future__ import annotations

from typing import Any, Iterable

from .advisor_track_record import AdvisorScore
from .growth_loop import GrowthLoopAssessment, LoopDecision
from .opportunity_archetype import OpportunityArchetype, ui_label


_ALLOWED_INDEPENDENCE = {
    "CROSS_PROVIDER_NO_BLOCKER_FOUND_YET",
    "INDEPENDENCE_INSUFFICIENT",
    "REVIEW_INCOMPLETE",
    "CHALLENGE_REQUIRED",
    "FALSIFICATION_REQUIRED",
    "MORE_EVIDENCE_OR_REVISION",
}


def _advisor_summary(advisors: Iterable[AdvisorScore]) -> list[dict[str, Any]]:
    return [
        {
            "provider": item.provider,
            "model": item.model,
            "domain": item.domain,
            "score": item.score,
            "evidence_weight": item.evidence_weight,
            "sample_size": item.sample_size,
            "status": item.status,
        }
        for item in advisors
    ]


def build_mission_plan(
    *,
    case_id: str,
    archetype: OpportunityArchetype,
    execution_route: dict[str, Any],
    advisors: tuple[AdvisorScore, ...],
    review_independence_state: str,
    leverage_search_complete: bool,
    loadout_ready: bool,
    tactic_sequence_ready: bool,
    forecast_frozen: bool,
    competitor_research_complete: bool,
    legal_or_safety_hold: bool = False,
    growth_loop_assessment: GrowthLoopAssessment | None = None,
    growth_loop_required: bool = False,
) -> dict[str, Any]:
    """Compose a non-authoritative one-page mission plan from existing layers.

    Growth-loop evidence is integrated as a bounded readiness input, never as a
    multiplier on mission value. This avoids double-counting leverage: the loop
    score remains descriptive evidence and cannot manufacture readiness.

    This coordination artifact never authorizes provider calls, spend,
    publication, credentials, live execution, adoption, Runtime activation or merge.
    """
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id is required")
    if not isinstance(archetype, OpportunityArchetype):
        raise ValueError("archetype must be OpportunityArchetype")
    if not isinstance(execution_route, dict) or not execution_route.get("primary_environment"):
        raise ValueError("execution_route must be a valid routing result")
    if review_independence_state not in _ALLOWED_INDEPENDENCE:
        raise ValueError("unexpected review_independence_state")
    for value, name in (
        (leverage_search_complete, "leverage_search_complete"),
        (loadout_ready, "loadout_ready"),
        (tactic_sequence_ready, "tactic_sequence_ready"),
        (forecast_frozen, "forecast_frozen"),
        (competitor_research_complete, "competitor_research_complete"),
        (legal_or_safety_hold, "legal_or_safety_hold"),
        (growth_loop_required, "growth_loop_required"),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")
    if growth_loop_assessment is not None and not isinstance(growth_loop_assessment, GrowthLoopAssessment):
        raise ValueError("growth_loop_assessment must be GrowthLoopAssessment or None")

    provider_count = len({item.provider for item in advisors})
    blockers: list[str] = []
    if legal_or_safety_hold:
        blockers.append("LEGAL_OR_SAFETY_HOLD")
    if not competitor_research_complete:
        blockers.append("COMPETITOR_RESEARCH_INCOMPLETE")
    if not leverage_search_complete:
        blockers.append("LEVERAGE_SEARCH_INCOMPLETE")
    if not loadout_ready:
        blockers.append("LOADOUT_NOT_READY")
    if not tactic_sequence_ready:
        blockers.append("TACTIC_SEQUENCE_NOT_READY")
    if not forecast_frozen:
        blockers.append("FORECAST_NOT_FROZEN")
    if review_independence_state != "CROSS_PROVIDER_NO_BLOCKER_FOUND_YET":
        blockers.append(f"REVIEW_{review_independence_state}")

    loop_decision = None
    loop_score = None
    loop_reasons: list[str] = []
    loop_blockers: list[str] = []
    loop_multiplier_hypothesis = None
    if growth_loop_assessment is not None:
        loop_decision = growth_loop_assessment.decision.value
        loop_score = growth_loop_assessment.score
        loop_reasons = list(growth_loop_assessment.reasons)
        loop_blockers = list(growth_loop_assessment.blockers)
        loop_multiplier_hypothesis = growth_loop_assessment.estimated_loop_multiplier
        if growth_loop_assessment.decision == LoopDecision.UNSAFE_OR_POLICY_FRAGILE:
            blockers.append("GROWTH_LOOP_UNSAFE_OR_POLICY_FRAGILE")
        elif growth_loop_required and growth_loop_assessment.decision != LoopDecision.LOOP_READY:
            blockers.append(f"GROWTH_LOOP_{growth_loop_assessment.decision.value}")
    elif growth_loop_required:
        blockers.append("GROWTH_LOOP_NOT_ASSESSED")

    if (
        legal_or_safety_hold
        or "GROWTH_LOOP_UNSAFE_OR_POLICY_FRAGILE" in blockers
        or review_independence_state in {
            "CHALLENGE_REQUIRED",
            "FALSIFICATION_REQUIRED",
            "REVIEW_INCOMPLETE",
        }
    ):
        posture = "HOLD_AND_RESOLVE_BLOCKER"
    elif blockers:
        posture = "RESEARCH_OR_TRAINING_ONLY"
    elif archetype == OpportunityArchetype.SHORT_WAVE_ONE_HIT:
        posture = "TACTICAL_TEST_READY_FOR_GOVERNED_GATE"
    elif archetype == OpportunityArchetype.RECURRING_BURST:
        posture = "RECURRING_TEST_READY_FOR_GOVERNED_GATE"
    elif archetype == OpportunityArchetype.DURABLE_COMPOUNDER:
        posture = "DURABLE_TEST_READY_FOR_GOVERNED_GATE"
    else:
        posture = "EXPERIMENT_READY_FOR_GOVERNED_GATE"

    return {
        "case_id": case_id,
        "archetype": archetype.value,
        "ui_archetype_label": ui_label(archetype),
        "mission_posture": posture,
        "execution_environment": execution_route["primary_environment"],
        "phone_can_complete": bool(execution_route.get("phone_can_complete")),
        "mac_leverage_score": execution_route.get("mac_leverage_score"),
        "advisors": _advisor_summary(advisors),
        "advisor_provider_count": provider_count,
        "review_independence_state": review_independence_state,
        "growth_loop_required": growth_loop_required,
        "growth_loop_decision": loop_decision,
        "growth_loop_score": loop_score,
        "growth_loop_reasons": loop_reasons,
        "growth_loop_blockers": loop_blockers,
        "growth_loop_multiplier_hypothesis": loop_multiplier_hypothesis,
        "growth_loop_multiplier_applied_to_mission": False,
        "blockers": blockers,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "live_execution_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
        "owner_gate_still_required": True,
        "note": (
            "Mission planning only. Growth-loop scores are descriptive evidence and are not stacked as mission multipliers. "
            "A ready posture means the research packet is organized for the next governed gate; it is not permission to act."
        ),
    }
