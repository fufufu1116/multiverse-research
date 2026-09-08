#!/usr/bin/env python3
"""Manual real-time odds gate for owner-assisted Keirin execution.

The prediction/simulation layer does not need live odds.
This tool converts a frozen model probability into a minimum displayed
decimal odds threshold. The owner can compare that threshold with the
current market odds at purchase time.

No network access. No odds scraping. No bet execution.
"""

from __future__ import annotations

from math import ceil


class OddsGateError(ValueError):
    pass


def _check_probability(p: float) -> float:
    p=float(p)
    if not (0.0 < p <= 1.0):
        raise OddsGateError("probability_must_be_in_(0,1]")
    return p


def break_even_decimal_odds(probability: float) -> float:
    p=_check_probability(probability)
    return 1.0/p


def minimum_purchase_odds(
    probability: float,
    required_roi: float,
    display_step: float=0.1,
) -> float:
    p=_check_probability(probability)
    required_roi=float(required_roi)
    display_step=float(display_step)
    if required_roi < 0:
        raise OddsGateError("required_roi_must_be_nonnegative")
    if display_step <= 0:
        raise OddsGateError("display_step_must_be_positive")
    raw=(1.0+required_roi)/p
    return round(ceil((raw-1e-12)/display_step)*display_step,10)


def decision(
    probability: float,
    required_roi: float,
    current_odds: float | None=None,
    display_step: float=0.1,
) -> dict:
    p=_check_probability(probability)
    threshold=minimum_purchase_odds(p,required_roi,display_step)
    out={
        "model_probability":p,
        "break_even_odds":round(break_even_decimal_odds(p),4),
        "required_roi":float(required_roi),
        "minimum_purchase_odds":threshold,
        "owner_instruction":f"現在オッズが {threshold:.1f}倍以上なら購入候補、未満なら見送り",
        "live_odds_required_for_model":False,
        "live_odds_source":"OWNER_MANUAL_CHECK_AT_PURCHASE_TIME",
    }
    if current_odds is not None:
        current=float(current_odds)
        out["current_odds"]=current
        out["decision"]="BUY_CANDIDATE" if current>=threshold else "SKIP"
        out["expected_roi_at_current_odds"]=round(p*current-1.0,6)
    return out


def selftest():
    x=decision(0.072,0.10)
    assert x["minimum_purchase_odds"]==15.3
    assert decision(0.072,0.10,15.3)["decision"]=="BUY_CANDIDATE"
    assert decision(0.072,0.10,15.2)["decision"]=="SKIP"
    assert minimum_purchase_odds(0.10,0.0)==10.0
    return {
        "status":"PASS",
        "example_probability":0.072,
        "required_roi":0.10,
        "minimum_purchase_odds":15.3,
        "manual_gate_boundary":"15.3以上 BUY_CANDIDATE / 15.2以下 SKIP",
    }


if __name__=="__main__":
    print(selftest())
