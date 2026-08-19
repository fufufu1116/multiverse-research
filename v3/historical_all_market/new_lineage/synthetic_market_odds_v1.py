from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Dict, Hashable, Mapping, Optional

Ticket = Hashable


@dataclass(frozen=True)
class SyntheticMarketProfile:
    """Scenario parameters for a stylized pari-mutuel-like quote emulator.

    These are engineering/scenario parameters, not empirical keirin estimates unless a
    later receipt explicitly proves calibration from a lawfully held real-price sample.
    """

    name: str
    payout_return_factor: float = 0.75
    sharpness_exponent: float = 1.0
    log_noise_sigma: float = 0.25
    min_decimal_odds: float = 1.01
    max_decimal_odds: Optional[float] = None

    def validate(self) -> None:
        if not (0.0 < self.payout_return_factor <= 1.0):
            raise ValueError("payout_return_factor must be in (0, 1]")
        if self.sharpness_exponent <= 0.0:
            raise ValueError("sharpness_exponent must be > 0")
        if self.log_noise_sigma < 0.0:
            raise ValueError("log_noise_sigma must be >= 0")
        if self.min_decimal_odds < 1.0:
            raise ValueError("min_decimal_odds must be >= 1")
        if self.max_decimal_odds is not None and self.max_decimal_odds < self.min_decimal_odds:
            raise ValueError("max_decimal_odds must be >= min_decimal_odds")


DEFAULT_PROFILES = {
    "SHARP": SyntheticMarketProfile(
        name="SHARP",
        payout_return_factor=0.75,
        sharpness_exponent=1.0,
        log_noise_sigma=0.12,
    ),
    "NOISY": SyntheticMarketProfile(
        name="NOISY",
        payout_return_factor=0.75,
        sharpness_exponent=0.95,
        log_noise_sigma=0.35,
    ),
    "TAIL_HEAVY": SyntheticMarketProfile(
        name="TAIL_HEAVY",
        payout_return_factor=0.75,
        sharpness_exponent=1.15,
        log_noise_sigma=0.30,
        max_decimal_odds=5000.0,
    ),
    "STRESS": SyntheticMarketProfile(
        name="STRESS",
        payout_return_factor=0.70,
        sharpness_exponent=0.90,
        log_noise_sigma=0.60,
        max_decimal_odds=10000.0,
    ),
}


def _normalize_positive(weights: Mapping[Ticket, float]) -> Dict[Ticket, float]:
    cleaned: Dict[Ticket, float] = {}
    for ticket, value in weights.items():
        x = float(value)
        if not math.isfinite(x) or x < 0.0:
            raise ValueError(f"invalid_weight:{ticket}:{x}")
        cleaned[ticket] = x

    total = sum(cleaned.values())
    if total <= 0.0:
        raise ValueError("all weights are zero")
    return {ticket: value / total for ticket, value in cleaned.items()}


def event_probabilities_to_quote_shape(
    event_probabilities: Mapping[Ticket, float],
) -> Dict[Ticket, float]:
    """Convert nonnegative event probabilities into a unit-mass quote-shape object.

    For exclusive markets whose event probabilities sum to one, this is numerically
    identical to the event distribution. For overlapping markets such as Wide, this
    normalization is ONLY a quote-shape transform and must not be relabeled as event
    probability.
    """

    return _normalize_positive(event_probabilities)


def generate_synthetic_decimal_odds(
    event_probabilities: Mapping[Ticket, float],
    *,
    profile: SyntheticMarketProfile,
    seed: int,
) -> Dict[Ticket, float]:
    """Generate deterministic-seeded synthetic decimal odds.

    Pipeline:
      1. Convert event probabilities to a unit-mass quote-shape basis.
      2. Apply a configurable sharpness exponent.
      3. Add multiplicative log-normal-style demand noise with fixed RNG seed.
      4. Normalize the resulting synthetic demand shares.
      5. Convert demand share s_t to pari-mutuel-like decimal payout proxy r/s_t,
         where r is payout_return_factor.

    The result is a synthetic engineering price object, NOT real market evidence.
    """

    profile.validate()
    base_shape = event_probabilities_to_quote_shape(event_probabilities)
    rng = random.Random(int(seed))

    demand_weights: Dict[Ticket, float] = {}
    for ticket, q in base_shape.items():
        if q <= 0.0:
            demand_weights[ticket] = 0.0
            continue
        log_noise = rng.gauss(0.0, profile.log_noise_sigma)
        demand_weights[ticket] = (q ** profile.sharpness_exponent) * math.exp(log_noise)

    demand_share = _normalize_positive(demand_weights)

    odds: Dict[Ticket, float] = {}
    for ticket, share in demand_share.items():
        if share <= 0.0:
            decimal_odds = profile.max_decimal_odds or float("inf")
        else:
            decimal_odds = profile.payout_return_factor / share

        decimal_odds = max(profile.min_decimal_odds, decimal_odds)
        if profile.max_decimal_odds is not None:
            decimal_odds = min(profile.max_decimal_odds, decimal_odds)
        odds[ticket] = float(decimal_odds)

    return odds


def synthetic_market_receipt(
    *,
    market_name: str,
    profile: SyntheticMarketProfile,
    seed: int,
    odds: Mapping[Ticket, float],
) -> dict:
    finite = [float(x) for x in odds.values() if math.isfinite(float(x))]
    return {
        "price_object_type": "SYNTHETIC_MARKET_SIMULATION_ONLY",
        "market": market_name,
        "profile": profile.name,
        "seed": int(seed),
        "payout_return_factor": profile.payout_return_factor,
        "sharpness_exponent": profile.sharpness_exponent,
        "log_noise_sigma": profile.log_noise_sigma,
        "ticket_count": len(odds),
        "min_odds": min(finite) if finite else None,
        "max_odds": max(finite) if finite else None,
        "scientific_claim_boundary": "NOT_REAL_MARKET_EVIDENCE",
    }
