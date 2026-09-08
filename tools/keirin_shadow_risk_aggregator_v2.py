#!/usr/bin/env python3
"""Strict outcome-free per-race shadow risk aggregator v2."""

from math import isfinite
from typing import Iterable, Dict, Mapping

DEFAULT_RACE_RISK_CAP = 1.0


class ShadowRiskError(ValueError):
    pass


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShadowRiskError(f"{label}_must_be_numeric")
    x = float(value)
    if not isfinite(x):
        raise ShadowRiskError(f"{label}_must_be_finite")
    return x


def aggregate(
    selections: Iterable[Dict],
    race_risk_cap: float = DEFAULT_RACE_RISK_CAP,
) -> Dict:
    cap = _finite(race_risk_cap, "race_risk_cap")
    if cap <= 0.0:
        raise ShadowRiskError("race_risk_cap_must_be_positive")

    rows = []
    for index, raw in enumerate(selections):
        if not isinstance(raw, Mapping):
            raise ShadowRiskError(f"selection_must_be_mapping:{index}")
        if "requested_risk_units" not in raw:
            raise ShadowRiskError(f"missing_requested_risk_units:{index}")
        risk = _finite(raw["requested_risk_units"], f"requested_risk_units:{index}")
        if risk < 0.0:
            raise ShadowRiskError("requested_risk_units_must_be_nonnegative")
        if risk == 0.0:
            continue
        row = dict(raw)
        row["requested_risk_units"] = risk
        rows.append(row)

    requested = sum(x["requested_risk_units"] for x in rows)
    if not isfinite(requested):
        raise ShadowRiskError("requested_total_risk_units_must_be_finite")
    scale = 1.0 if requested <= cap or requested == 0.0 else cap / requested
    if not isfinite(scale) or scale < 0.0 or scale > 1.0 + 1e-12:
        raise ShadowRiskError("invalid_risk_scale_factor")

    for row in rows:
        row["allocated_risk_units"] = row["requested_risk_units"] * scale
        if not isfinite(row["allocated_risk_units"]):
            raise ShadowRiskError("nonfinite_allocated_risk_units")

    allocated = sum(x["allocated_risk_units"] for x in rows)
    if not isfinite(allocated) or allocated > cap + 1e-12:
        raise ShadowRiskError("race_risk_cap_violation")

    return {
        "requested_total_risk_units": requested,
        "race_risk_cap": cap,
        "scale_factor": scale,
        "allocated_total_risk_units": allocated,
        "cap_respected": True,
        "selections": rows,
        "real_money_instruction": False,
    }
