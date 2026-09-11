from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class SignalType(str, Enum):
    NEWS = "NEWS"
    SEARCH = "SEARCH"
    SOCIAL = "SOCIAL"
    PRODUCT = "PRODUCT"
    ADVERTISING = "ADVERTISING"
    RULE_CHANGE = "RULE_CHANGE"
    SERVICE_CHANGE = "SERVICE_CHANGE"
    PUBLIC_EVENT = "PUBLIC_EVENT"
    OTHER = "OTHER"


@dataclass(frozen=True)
class EvidenceRef:
    source_name: str
    locator: str
    observed_at: str
    primary: bool = False

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if not self.locator.strip():
            raise ValueError("locator is required")
        if not self.observed_at.strip():
            raise ValueError("observed_at is required")


@dataclass(frozen=True)
class SignalObservation:
    signal_id: str
    title: str
    signal_type: SignalType
    market: str
    observed_at: str
    strength: int
    purchase_intent_hint: int
    evidence: Tuple[EvidenceRef, ...]
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("signal_id is required")
        if not self.title.strip():
            raise ValueError("title is required")
        if not self.market.strip():
            raise ValueError("market is required")
        if not self.observed_at.strip():
            raise ValueError("observed_at is required")
        for name in ("strength", "purchase_intent_hint"):
            value = getattr(self, name)
            if not 0 <= value <= 5:
                raise ValueError(f"{name} must be between 0 and 5")
        if not self.evidence:
            raise ValueError("at least one evidence reference is required")


def evidence_quality(signal: SignalObservation) -> int:
    """Return a bounded 0-5 evidence quality score.

    This is intentionally conservative. Multiple sources help, while at least
    one primary source is required for the maximum score.
    """
    distinct_sources = len({ref.source_name.strip().lower() for ref in signal.evidence})
    primary_count = sum(1 for ref in signal.evidence if ref.primary)

    if distinct_sources >= 3 and primary_count >= 1:
        return 5
    if distinct_sources >= 2 and primary_count >= 1:
        return 4
    if distinct_sources >= 2:
        return 3
    if primary_count >= 1:
        return 2
    return 1
