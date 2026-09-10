from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Optional, Tuple


class ForecastOutcome(str, Enum):
    WIN = "WIN"
    MIXED = "MIXED"
    LOSS = "LOSS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class ForecastCard:
    forecast_id: str
    candidate_name: str
    created_at: str
    source_signal_ids: Tuple[str, ...]
    predicted_peak_start: str
    predicted_peak_end: str
    expected_demand_life_days: Optional[float]
    predicted_competitor_arrival_days: Optional[float]
    predicted_ai_or_incumbent_absorption_days: Optional[float]
    predicted_next_actions: Tuple[str, ...]
    monetization_hypothesis: str
    kill_condition: str
    confidence: int

    def __post_init__(self) -> None:
        required = (
            ("forecast_id", self.forecast_id),
            ("candidate_name", self.candidate_name),
            ("created_at", self.created_at),
            ("predicted_peak_start", self.predicted_peak_start),
            ("predicted_peak_end", self.predicted_peak_end),
            ("monetization_hypothesis", self.monetization_hypothesis),
            ("kill_condition", self.kill_condition),
        )
        for name, value in required:
            if not value.strip():
                raise ValueError(f"{name} is required")
        if not self.source_signal_ids:
            raise ValueError("source_signal_ids must not be empty")
        if len(self.predicted_next_actions) < 3 or len(self.predicted_next_actions) > 7:
            raise ValueError("predicted_next_actions must contain 3-7 steps")
        if not 0 <= self.confidence <= 5:
            raise ValueError("confidence must be between 0 and 5")
        for name in (
            "expected_demand_life_days",
            "predicted_competitor_arrival_days",
            "predicted_ai_or_incumbent_absorption_days",
        ):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive when supplied")


@dataclass(frozen=True)
class ForecastSettlement:
    forecast_id: str
    settled_at: str
    outcome: ForecastOutcome
    observed_peak_at: Optional[str] = None
    observed_demand_life_days: Optional[float] = None
    observed_competitor_arrival_days: Optional[float] = None
    observed_profit_yen: Optional[float] = None
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.forecast_id.strip():
            raise ValueError("forecast_id is required")
        if not self.settled_at.strip():
            raise ValueError("settled_at is required")


def canonical_forecast_payload(card: ForecastCard) -> str:
    return json.dumps(
        asdict(card),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def forecast_commitment(card: ForecastCard) -> str:
    """Tamper-evident hash of the prediction as it existed before outcomes."""
    return hashlib.sha256(canonical_forecast_payload(card).encode("utf-8")).hexdigest()


def verify_forecast_commitment(card: ForecastCard, expected_commitment: str) -> bool:
    return forecast_commitment(card) == expected_commitment


def settle_forecast(
    *,
    card: ForecastCard,
    expected_commitment: str,
    settlement: ForecastSettlement,
) -> dict:
    if settlement.forecast_id != card.forecast_id:
        raise ValueError("settlement forecast_id does not match card")
    if not verify_forecast_commitment(card, expected_commitment):
        raise ValueError("forecast commitment mismatch; prediction may have changed")
    return {
        "forecast_id": card.forecast_id,
        "commitment": expected_commitment,
        "outcome": settlement.outcome.value,
        "settled_at": settlement.settled_at,
        "observed_peak_at": settlement.observed_peak_at,
        "observed_demand_life_days": settlement.observed_demand_life_days,
        "observed_competitor_arrival_days": settlement.observed_competitor_arrival_days,
        "observed_profit_yen": settlement.observed_profit_yen,
        "notes": list(settlement.notes),
    }
