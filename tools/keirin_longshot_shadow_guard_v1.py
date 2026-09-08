#!/usr/bin/env python3
"""Outcome-free engineering guard for future longshot shadow decisions.

This module does not fetch odds, predictions, results, payouts, or external data.
It only evaluates caller-supplied, already-authorized PRE inputs.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Band:
    name: str
    lo: float
    hi: Optional[float]
    min_ratio: float
    min_ev: float
    risk_units: float

BANDS = (
    Band("CORE", 1.0, 20.0, 1.10, 0.10, 1.00),
    Band("MID_HOLE", 20.0, 80.0, 1.35, 0.35, 0.50),
    Band("LONGSHOT", 80.0, 300.0, 1.75, 0.75, 0.25),
    Band("EXTREME_LONGSHOT", 300.0, None, 2.50, 1.50, 0.10),
)

def band_for_odds(decimal_odds: float) -> Band:
    if decimal_odds < 1.0:
        raise ValueError("decimal_odds must be >= 1")
    for b in BANDS:
        if decimal_odds > b.lo and (b.hi is None or decimal_odds <= b.hi):
            return b
        if b.name == "CORE" and 1.0 <= decimal_odds <= 20.0:
            return b
    raise AssertionError("unreachable")

def evaluate_ticket(
    s0_probability: float,
    challenger_probability: float,
    decimal_odds: float,
) -> dict:
    for p in (s0_probability, challenger_probability):
        if not (0.0 <= p <= 1.0):
            raise ValueError("probabilities must be in [0,1]")
    band = band_for_odds(decimal_odds)
    p_cons = min(s0_probability, challenger_probability)
    p_market = 1.0 / decimal_odds
    ratio = p_cons / p_market if p_market else 0.0
    raw_ev = p_cons * decimal_odds - 1.0
    qualify = ratio >= band.min_ratio and raw_ev >= band.min_ev
    return {
        "band": band.name,
        "conservative_probability": p_cons,
        "market_implied_probability": p_market,
        "probability_ratio": ratio,
        "raw_ev": raw_ev,
        "minimum_ratio": band.min_ratio,
        "minimum_ev": band.min_ev,
        "qualifies": qualify,
        "shadow_risk_units": band.risk_units if qualify else 0.0,
        "real_money_instruction": False,
    }

def _self_test() -> None:
    cases = [
        # Core: 6.3x, p=18.86% -> qualifies.
        (0.1886, 0.1968, 6.3, "CORE", True),
        # Mid-hole: 30x needs >=35% EV and >=1.35x market probability.
        (0.050, 0.052, 30.0, "MID_HOLE", True),
        # Longshot: 150x with only 1.0% conservative p is insufficient (ratio 1.5).
        (0.010, 0.012, 150.0, "LONGSHOT", False),
        # Extreme: 500x with 0.6% conservative p -> ratio 3.0, EV 200%, qualifies.
        (0.006, 0.007, 500.0, "EXTREME_LONGSHOT", True),
    ]
    for s0, ch, odds, band, expected in cases:
        got = evaluate_ticket(s0, ch, odds)
        assert got["band"] == band
        assert got["qualifies"] is expected
    print("PASS")

if __name__ == "__main__":
    _self_test()
