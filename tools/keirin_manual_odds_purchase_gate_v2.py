#!/usr/bin/env python3
"""Hardened owner-manual threshold calculator v2.

No network access and no automated execution. v2 adds strict finite numeric
validation so malformed manual inputs cannot produce a false candidate signal.
"""

from __future__ import annotations

from math import ceil, isfinite


class OddsGateError(ValueError):
    pass


def _finite(value, label: str) -> float:
    try:
        x=float(value)
    except Exception as exc:
        raise OddsGateError(f"{label}_must_be_numeric") from exc
    if not isfinite(x):
        raise OddsGateError(f"{label}_must_be_finite")
    return x


def _check_probability(p: float) -> float:
    p=_finite(p,"probability")
    if not (0.0 < p <= 1.0):
        raise OddsGateError("probability_must_be_in_(0,1]")
    return p


def _check_required_roi(value: float) -> float:
    x=_finite(value,"required_roi")
    if x < 0.0:
        raise OddsGateError("required_roi_must_be_nonnegative")
    return x


def _check_display_step(value: float) -> float:
    x=_finite(value,"display_step")
    if x <= 0.0:
        raise OddsGateError("display_step_must_be_positive")
    return x


def _check_current_odds(value: float) -> float:
    x=_finite(value,"current_odds")
    if x < 1.0:
        raise OddsGateError("current_odds_must_be_at_least_1")
    return x


def break_even_decimal_odds(probability: float) -> float:
    return 1.0/_check_probability(probability)


def minimum_purchase_odds(
    probability: float,
    required_roi: float,
    display_step: float=0.1,
) -> float:
    p=_check_probability(probability)
    roi=_check_required_roi(required_roi)
    step=_check_display_step(display_step)
    raw=(1.0+roi)/p
    threshold=ceil((raw-1e-12)/step)*step
    if not isfinite(threshold) or threshold < 1.0:
        raise OddsGateError("invalid_threshold")
    return round(threshold,10)


def decision(
    probability: float,
    required_roi: float,
    current_odds: float | None=None,
    display_step: float=0.1,
) -> dict:
    p=_check_probability(probability)
    roi=_check_required_roi(required_roi)
    step=_check_display_step(display_step)
    threshold=minimum_purchase_odds(p,roi,step)
    out={
        "model_probability":p,
        "break_even_odds":round(break_even_decimal_odds(p),4),
        "required_roi":roi,
        "minimum_purchase_odds":threshold,
        "manual_comparison_only":True,
        "live_input_required_for_model":False,
        "network_access":False,
        "automated_execution":False,
    }
    if current_odds is not None:
        current=_check_current_odds(current_odds)
        out["current_odds"]=current
        out["threshold_met"]=bool(current>=threshold)
        out["expected_roi_at_current_odds"]=round(p*current-1.0,6)
    return out
