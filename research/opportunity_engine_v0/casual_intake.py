from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntakeDecision(str, Enum):
    REJECT = "REJECT"
    STORE_NOTE = "STORE_NOTE"
    STORE_OPPORTUNITY_CANDIDATE = "STORE_OPPORTUNITY_CANDIDATE"


@dataclass(frozen=True)
class CasualPostCandidate:
    source_id: str
    source_kind: str
    summary: str
    reusable_pattern: str
    concrete_claims_present: bool
    claims_verified: bool
    contains_sensitive_personal_data: bool
    deceptive_or_evasive: bool
    commercial_relevance: int
    novelty_or_reuse_value: int
    evidence_strength: int
    owner_fit: int

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.source_kind.strip():
            raise ValueError("source_kind is required")
        if not self.summary.strip():
            raise ValueError("summary is required")
        if not self.reusable_pattern.strip():
            raise ValueError("reusable_pattern is required")
        for name in (
            "commercial_relevance",
            "novelty_or_reuse_value",
            "evidence_strength",
            "owner_fit",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def assess_casual_post(candidate: CasualPostCandidate) -> dict[str, object]:
    """Route useful ideas from casual conversation into durable research without treating them as facts.

    The intake is intentionally conservative. A casual post can preserve a reusable business pattern
    even when its numerical, legal, market, or provider-specific claims are unverified. It never grants
    adoption, execution, provider, spend, publication, or canonical authority.
    """
    if candidate.contains_sensitive_personal_data:
        return {
            "decision": IntakeDecision.REJECT.value,
            "score": 0,
            "reasons": ("SENSITIVE_PERSONAL_DATA_NOT_FOR_OPPORTUNITY_INBOX",),
            "requires_verification_before_use": True,
            "automatic_execution_authorized": False,
        }

    if candidate.deceptive_or_evasive:
        return {
            "decision": IntakeDecision.REJECT.value,
            "score": 0,
            "reasons": ("DECEPTIVE_OR_EVASIVE_PATTERN",),
            "requires_verification_before_use": True,
            "automatic_execution_authorized": False,
        }

    score = (
        candidate.commercial_relevance * 6
        + candidate.novelty_or_reuse_value * 5
        + candidate.owner_fit * 5
        + candidate.evidence_strength * 3
    )
    score = max(0, min(100, score))

    reasons: list[str] = []
    if candidate.commercial_relevance >= 3:
        reasons.append("COMMERCIALLY_RELEVANT")
    if candidate.novelty_or_reuse_value >= 3:
        reasons.append("REUSABLE_PATTERN")
    if candidate.owner_fit >= 3:
        reasons.append("OWNER_OPERATING_MODEL_FIT")

    requires_verification = candidate.concrete_claims_present and not candidate.claims_verified
    if requires_verification:
        reasons.append("UNVERIFIED_CLAIMS_QUARANTINED")

    if score >= 55 and candidate.commercial_relevance >= 3 and candidate.novelty_or_reuse_value >= 3:
        decision = IntakeDecision.STORE_OPPORTUNITY_CANDIDATE
    elif score >= 30:
        decision = IntakeDecision.STORE_NOTE
    else:
        decision = IntakeDecision.REJECT

    return {
        "decision": decision.value,
        "score": score,
        "reasons": tuple(reasons),
        "requires_verification_before_use": requires_verification,
        "automatic_execution_authorized": False,
        "adoption_authorized": False,
        "note": (
            "Casual-chat material is hypothesis input only. Provider terms, resale rights, fees, demand, "
            "economics and legal claims must be freshly verified before advancing a live opportunity."
        ),
    }
