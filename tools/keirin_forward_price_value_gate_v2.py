#!/usr/bin/env python3
"""Forward-only price/value gate v2 for the KEIRIN prospective lane.

This module deliberately does NOT fetch odds and does NOT place bets.
It consumes a frozen PRE ticket probability plus a separately observed
current decimal price, then applies the preregistered forward rules.

Authority:
- CORE 1.0-20.0x: manual BUY_CANDIDATE_100YEN is possible only when both
  fixed value thresholds pass and the price is verified current PRE.
- >20.0x: SHADOW_ONLY. Never returns a live/manual buy candidate.
- >80.0x: a second independent current PRE price source is required for a
  valid shadow observation.
- >300.0x: second source + anomaly check are required.
- 9999.9 is treated as placeholder-like and fails closed unless explicitly
  verified as a genuine current PRE quote. It is still SHADOW_ONLY because
  it is >20x.

Runtime / automated betting: OFF.
"""

from math import isfinite


class ForwardPriceValueGateError(ValueError):
    pass


BANDS = (
    {
        "name": "CORE",
        "lo_exclusive": None,
        "lo_inclusive": 1.0,
        "hi_inclusive": 20.0,
        "min_multiple": 1.10,
        "min_ev": 0.10,
        "purchase_region": True,
        "second_source_required": False,
        "anomaly_check_required": False,
    },
    {
        "name": "MID_HOLE",
        "lo_exclusive": 20.0,
        "hi_inclusive": 80.0,
        "min_multiple": 1.35,
        "min_ev": 0.35,
        "purchase_region": False,
        "second_source_required": False,
        "anomaly_check_required": False,
    },
    {
        "name": "LONGSHOT",
        "lo_exclusive": 80.0,
        "hi_inclusive": 300.0,
        "min_multiple": 1.75,
        "min_ev": 0.75,
        "purchase_region": False,
        "second_source_required": True,
        "anomaly_check_required": False,
    },
    {
        "name": "EXTREME_LONGSHOT",
        "lo_exclusive": 300.0,
        "hi_inclusive": None,
        "min_multiple": 2.50,
        "min_ev": 1.50,
        "purchase_region": False,
        "second_source_required": True,
        "anomaly_check_required": True,
    },
)

VERIFIED_QUALITY_STATE = "VERIFIED_CURRENT_PRE"


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForwardPriceValueGateError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise ForwardPriceValueGateError(f"{label}_must_be_finite")
    return x


def _probability(value, label):
    x = _finite(value, label)
    if not (0.0 < x <= 1.0):
        raise ForwardPriceValueGateError(f"{label}_must_be_in_(0,1]")
    return x


def band_for_odds(decimal_odds):
    odds = _finite(decimal_odds, "decimal_odds")
    if odds < 1.0:
        raise ForwardPriceValueGateError("decimal_odds_must_be_at_least_1")
    if odds <= 20.0:
        return BANDS[0]
    if odds <= 80.0:
        return BANDS[1]
    if odds <= 300.0:
        return BANDS[2]
    return BANDS[3]


def evaluate(
    s0_probability,
    challenger_probability,
    decimal_odds,
    *,
    odds_quality_state=VERIFIED_QUALITY_STATE,
    second_source_verified=False,
    anomaly_check_passed=False,
    explicit_9999_9_verified=False,
):
    """Evaluate one already-frozen 3renhuku ticket against one PRE price.

    The caller is responsible for ensuring prediction freeze happened before
    price retrieval. This function enforces price-band and data-quality rules.
    """
    s0 = _probability(s0_probability, "s0_probability")
    challenger = _probability(challenger_probability, "challenger_probability")
    odds = _finite(decimal_odds, "decimal_odds")
    band = band_for_odds(odds)

    p = min(s0, challenger)
    market_p = 1.0 / odds
    multiple = p / market_p
    ev = p * odds - 1.0

    quality_failures = []
    if odds_quality_state != VERIFIED_QUALITY_STATE:
        quality_failures.append(f"odds_quality_{odds_quality_state}")
    if band["second_source_required"] and not second_source_verified:
        quality_failures.append("second_source_required")
    if band["anomaly_check_required"] and not anomaly_check_passed:
        quality_failures.append("anomaly_check_required")
    if odds == 9999.9 and not explicit_9999_9_verified:
        quality_failures.append("9999_9_placeholder_not_explicitly_verified")

    valid_price_observation = not quality_failures
    numeric_value_gate_pass = (
        multiple >= band["min_multiple"] and ev >= band["min_ev"]
    )

    if not valid_price_observation:
        decision = "NO_BET_UNVERIFIED"
    elif band["purchase_region"]:
        decision = (
            "BUY_CANDIDATE_100YEN" if numeric_value_gate_pass else "NO_BET"
        )
    else:
        decision = "SHADOW_ONLY"

    return {
        "band": band["name"],
        "s0_probability": s0,
        "challenger_probability": challenger,
        "conservative_probability": p,
        "current_odds": odds,
        "market_implied_probability": market_p,
        "probability_multiple_vs_market": multiple,
        "guarded_expected_roi": ev,
        "required_probability_multiple": band["min_multiple"],
        "required_expected_roi": band["min_ev"],
        "numeric_value_gate_pass": bool(numeric_value_gate_pass),
        "valid_price_observation": bool(valid_price_observation),
        "quality_failures": quality_failures,
        "purchase_region": bool(band["purchase_region"]),
        "decision": decision,
        "owner_action": decision,
        "stake_yen_if_buy_candidate": 100 if decision == "BUY_CANDIDATE_100YEN" else 0,
        "automatic_execution": False,
        "runtime": "OFF",
    }
