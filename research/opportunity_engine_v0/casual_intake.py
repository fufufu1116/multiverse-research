from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


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
    verification_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.source_kind.strip():
            raise ValueError("source_kind is required")
        if not self.summary.strip():
            raise ValueError("summary is required")
        if not self.reusable_pattern.strip():
            raise ValueError("reusable_pattern is required")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.verification_refs):
            raise ValueError("verification_refs must contain non-empty strings")
        for name in (
            "commercial_relevance",
            "novelty_or_reuse_value",
            "evidence_strength",
            "owner_fit",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def casual_content_fingerprint(candidate: CasualPostCandidate) -> str:
    """Content commitment used for dedupe; source identity is deliberately excluded."""
    payload = {
        "summary": " ".join(candidate.summary.lower().split()),
        "reusable_pattern": " ".join(candidate.reusable_pattern.lower().split()),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _authority_false() -> dict[str, bool]:
    return {
        "automatic_execution_authorized": False,
        "adoption_authorized": False,
        "provider_call_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
    }


def assess_casual_post(candidate: CasualPostCandidate) -> dict[str, object]:
    """Route useful ideas from casual conversation into durable research without treating them as facts.

    Verified status is not trusted from a naked boolean: concrete claims only leave quarantine
    when at least one external verification reference is bound to the intake record. The returned
    content fingerprint lets the knowledge layer detect repeated material without treating repetition
    as independent evidence.
    """
    fingerprint = casual_content_fingerprint(candidate)

    if candidate.contains_sensitive_personal_data:
        return {
            "decision": IntakeDecision.REJECT.value,
            "score": 0,
            "content_fingerprint": fingerprint,
            "reasons": ("SENSITIVE_PERSONAL_DATA_NOT_FOR_OPPORTUNITY_INBOX",),
            "requires_verification_before_use": True,
            **_authority_false(),
        }

    if candidate.deceptive_or_evasive:
        return {
            "decision": IntakeDecision.REJECT.value,
            "score": 0,
            "content_fingerprint": fingerprint,
            "reasons": ("DECEPTIVE_OR_EVASIVE_PATTERN",),
            "requires_verification_before_use": True,
            **_authority_false(),
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

    concrete_claims_verified = (
        candidate.concrete_claims_present
        and candidate.claims_verified
        and bool(candidate.verification_refs)
    )
    requires_verification = candidate.concrete_claims_present and not concrete_claims_verified
    if candidate.concrete_claims_present and candidate.claims_verified and not candidate.verification_refs:
        reasons.append("VERIFIED_FLAG_WITHOUT_EVIDENCE_REFS_IGNORED")
    if requires_verification:
        reasons.append("UNVERIFIED_CLAIMS_QUARANTINED")
    elif concrete_claims_verified:
        reasons.append("CLAIMS_BOUND_TO_VERIFICATION_REFS")

    if score >= 55 and candidate.commercial_relevance >= 3 and candidate.novelty_or_reuse_value >= 3:
        decision = IntakeDecision.STORE_OPPORTUNITY_CANDIDATE
    elif score >= 30:
        decision = IntakeDecision.STORE_NOTE
    else:
        decision = IntakeDecision.REJECT

    return {
        "decision": decision.value,
        "score": score,
        "source_id": candidate.source_id,
        "content_fingerprint": fingerprint,
        "verification_refs": list(candidate.verification_refs),
        "reasons": tuple(reasons),
        "requires_verification_before_use": requires_verification,
        **_authority_false(),
        "note": (
            "Casual-chat material is hypothesis input only. Repeated content must be deduplicated by fingerprint and does not add independent evidence. "
            "Provider terms, resale rights, fees, demand, economics and legal claims must be freshly verified before advancing a live opportunity."
        ),
    }
