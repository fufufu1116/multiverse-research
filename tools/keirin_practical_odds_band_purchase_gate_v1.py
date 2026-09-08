#!/usr/bin/env python3
"""Owner-assisted practical odds-band purchase gate v1.

No network access and no automated betting. Caller supplies frozen PRE model
probabilities and a manually observed current decimal odds value.

Key change from the earlier <=20x practical rule:
- no hard odds ceiling;
- higher-odds bands require progressively larger guarded expected value;
- conservative probability is min(S0, challenger);
- one flat 100-yen ticket remains the practical unit; no stake escalation.
"""

from math import isfinite


class PracticalOddsBandError(ValueError):
    pass


BANDS = (
    {"name":"CORE","lo":1.0,"hi":20.0,"min_multiple":1.10,"min_ev":0.10},
    {"name":"MID_HOLE","lo":20.0,"hi":80.0,"min_multiple":1.35,"min_ev":0.35},
    {"name":"LONGSHOT","lo":80.0,"hi":300.0,"min_multiple":1.75,"min_ev":0.75},
    {"name":"EXTREME_LONGSHOT","lo":300.0,"hi":None,"min_multiple":2.50,"min_ev":1.50},
)


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PracticalOddsBandError(f"{label}_must_be_numeric")
    x=float(value)
    if not isfinite(x):
        raise PracticalOddsBandError(f"{label}_must_be_finite")
    return x


def _probability(value, label):
    x=_finite(value,label)
    if not (0.0 < x <= 1.0):
        raise PracticalOddsBandError(f"{label}_must_be_in_(0,1]")
    return x


def band_for_odds(decimal_odds):
    odds=_finite(decimal_odds,"decimal_odds")
    if odds < 1.0:
        raise PracticalOddsBandError("decimal_odds_must_be_at_least_1")
    if odds <= 20.0:
        return BANDS[0]
    if odds <= 80.0:
        return BANDS[1]
    if odds <= 300.0:
        return BANDS[2]
    return BANDS[3]


def evaluate(s0_probability, challenger_probability, decimal_odds):
    s0=_probability(s0_probability,"s0_probability")
    challenger=_probability(challenger_probability,"challenger_probability")
    odds=_finite(decimal_odds,"decimal_odds")
    band=band_for_odds(odds)

    p=min(s0,challenger)
    market_p=1.0/odds
    multiple=p/market_p
    ev=p*odds-1.0
    qualifies=(multiple >= band["min_multiple"] and ev >= band["min_ev"])

    return {
        "band":band["name"],
        "s0_probability":s0,
        "challenger_probability":challenger,
        "conservative_probability":p,
        "current_odds":odds,
        "market_implied_probability":market_p,
        "probability_multiple_vs_market":multiple,
        "guarded_expected_roi":ev,
        "required_probability_multiple":band["min_multiple"],
        "required_expected_roi":band["min_ev"],
        "qualifies":bool(qualifies),
        "owner_action":"BUY_CANDIDATE_100YEN" if qualifies else "NO_BET",
        "automated_execution":False,
        "hard_odds_ceiling":None,
    }
