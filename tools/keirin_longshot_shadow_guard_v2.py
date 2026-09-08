#!/usr/bin/env python3
"""Strict outcome-free guard for future Keirin longshot shadow decisions v2."""

from dataclasses import dataclass
from math import isfinite
from typing import Optional


class LongshotGuardError(ValueError):
    pass


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


def _finite_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LongshotGuardError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise LongshotGuardError(f"{label}_must_be_finite")
    return x


def _probability(value, label: str) -> float:
    x = _finite_number(value, label)
    if not (0.0 <= x <= 1.0):
        raise LongshotGuardError(f"{label}_must_be_in_[0,1]")
    return x


def band_for_odds(decimal_odds: float) -> Band:
    odds = _finite_number(decimal_odds, "decimal_odds")
    if odds < 1.0:
        raise LongshotGuardError("decimal_odds_must_be_at_least_1")
    if odds <= 20.0:
        return BANDS[0]
    if odds <= 80.0:
        return BANDS[1]
    if odds <= 300.0:
        return BANDS[2]
    return BANDS[3]


def evaluate_ticket(
    s0_probability: float,
    challenger_probability: float,
    decimal_odds: float,
) -> dict:
    s0 = _probability(s0_probability, "s0_probability")
    challenger = _probability(challenger_probability, "challenger_probability")
    odds = _finite_number(decimal_odds, "decimal_odds")
    band = band_for_odds(odds)

    p_cons = min(s0, challenger)
    p_market = 1.0 / odds
    ratio = p_cons / p_market
    raw_ev = p_cons * odds - 1.0
    if not all(isfinite(x) for x in (p_market, ratio, raw_ev)):
        raise LongshotGuardError("nonfinite_derived_longshot_metric")

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
