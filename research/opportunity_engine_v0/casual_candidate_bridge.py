from __future__ import annotations

from typing import Any

from .casual_intake import CasualPostCandidate, IntakeDecision, assess_casual_post


def build_research_candidate_from_casual(candidate: CasualPostCandidate) -> dict[str, Any]:
    """Convert a useful casual-chat intake into a bounded research-only candidate.

    This bridge does not upgrade a hypothesis into evidence. It carries provenance,
    fingerprint and verification state into the normal research flow while keeping
    every live/authority flag false.
    """
    intake = assess_casual_post(candidate)
    if intake["decision"] != IntakeDecision.STORE_OPPORTUNITY_CANDIDATE.value:
        raise ValueError("casual intake is not eligible for opportunity-candidate promotion")

    research_questions = [
        "Who is the actual payer and what job/pain is being paid for?",
        "What current competitors, substitutes, incumbents and general-AI alternatives exist?",
        "What legal, contractual, platform-policy or territorial constraints apply?",
        "What are contribution economics after fees, support, refunds, tooling, acquisition and churn?",
        "What demand lifetime, competitor response, AI absorption and exit triggers are plausible?",
    ]
    if intake["requires_verification_before_use"]:
        research_questions.insert(0, "Which concrete claims in the source can be verified from authoritative or measured evidence?")

    return {
        "schema": "OPPORTUNITY_ENGINE_RESEARCH_CANDIDATE_FROM_CASUAL_v1",
        "source_id": candidate.source_id,
        "source_kind": candidate.source_kind,
        "content_fingerprint": intake["content_fingerprint"],
        "summary": candidate.summary,
        "reusable_pattern": candidate.reusable_pattern,
        "intake_score": intake["score"],
        "intake_reasons": list(intake["reasons"]),
        "verification_refs": list(intake.get("verification_refs", [])),
        "requires_verification_before_use": intake["requires_verification_before_use"],
        "research_status": "RESEARCH_REQUIRED",
        "research_questions": research_questions,
        "competitor_research_required": True,
        "payer_clarity_required": True,
        "economics_research_required": True,
        "legal_and_policy_research_required": True,
        "forecast_required_before_governed_test": True,
        "dedupe_key": intake["content_fingerprint"],
        "independent_evidence_count_added_by_intake": 0,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "live_execution_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
        "owner_gate_still_required": True,
        "note": "Promotion means only 'worth researching'. Casual repetition does not count as independent evidence and does not authorize action.",
    }
