"""Pre-outcome trend forecast candidate for research-only scoring.

The key rule is temporal integrity: score with information available at forecast time,
freeze the forecast, and settle later. This module does not authorize investment,
spend, publication, or live execution.
"""
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import hashlib
import json


class TrendForecastPosture(str, Enum):
    IGNORE = "IGNORE"
    WATCH = "WATCH"
    FORECAST_CANDIDATE = "FORECAST_CANDIDATE"


@dataclass(frozen=True)
class TrendSignalSnapshot:
    candidate_id: str
    observed_on: str
    early_community_heat: int
    creator_adoption_acceleration: int
    cross_region_spread: int
    derivative_creation: int
    search_or_save_intent: int
    collectibility_or_identity: int
    repeat_mention_persistence: int
    mainstream_saturation: int
    evidence_strength: int

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id required")
        date.fromisoformat(self.observed_on)
        for name in (
            "early_community_heat", "creator_adoption_acceleration", "cross_region_spread",
            "derivative_creation", "search_or_save_intent", "collectibility_or_identity",
            "repeat_mention_persistence", "mainstream_saturation", "evidence_strength",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be 0..5")


def assess_trend_signal(snapshot: TrendSignalSnapshot) -> dict:
    upside = (
        snapshot.early_community_heat * 5
        + snapshot.creator_adoption_acceleration * 6
        + snapshot.cross_region_spread * 6
        + snapshot.derivative_creation * 5
        + snapshot.search_or_save_intent * 6
        + snapshot.collectibility_or_identity * 4
        + snapshot.repeat_mention_persistence * 5
        + snapshot.evidence_strength * 5
    )
    late_penalty = snapshot.mainstream_saturation * 9
    score = max(0, min(100, upside - late_penalty))

    blockers = []
    if snapshot.evidence_strength < 2:
        blockers.append("EVIDENCE_TOO_WEAK")
    if snapshot.mainstream_saturation >= 4:
        blockers.append("ALREADY_TOO_MAINSTREAM_FOR_EARLY_CALL")
    if snapshot.creator_adoption_acceleration < 2 and snapshot.cross_region_spread < 2:
        blockers.append("NO_PROPAGATION_ACCELERATION")

    if blockers:
        posture = TrendForecastPosture.IGNORE if "ALREADY_TOO_MAINSTREAM_FOR_EARLY_CALL" in blockers else TrendForecastPosture.WATCH
    elif score >= 65:
        posture = TrendForecastPosture.FORECAST_CANDIDATE
    elif score >= 40:
        posture = TrendForecastPosture.WATCH
    else:
        posture = TrendForecastPosture.IGNORE

    payload = {
        "candidate_id": snapshot.candidate_id,
        "observed_on": snapshot.observed_on,
        "score": score,
        "posture": posture.value,
        "blockers": blockers,
        "horizons_days": [30, 90, 180],
        "prediction_claim": "candidate may exhibit materially broader adoption than at snapshot time",
        "settlement_required": True,
        "investment_advice": False,
        "automatic_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
    }
    commitment_payload = {
        "snapshot": asdict(snapshot),
        "assessment": payload,
    }
    canonical = json.dumps(
        commitment_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    payload["forecast_commitment"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload
