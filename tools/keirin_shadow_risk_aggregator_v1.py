#!/usr/bin/env python3
"""Outcome-free per-race shadow risk aggregator.

The caller supplies already-qualified research selections with requested risk units.
If combined requested exposure exceeds the per-race cap, all allocations are
scaled proportionally so strategy mix is preserved without increasing exposure.
No external data, odds, outcomes, payouts, or real-money execution occurs here.
"""
from typing import Iterable, Dict, List

DEFAULT_RACE_RISK_CAP=1.0

def aggregate(selections: Iterable[Dict], race_risk_cap: float=DEFAULT_RACE_RISK_CAP) -> Dict:
    if race_risk_cap <= 0:
        raise ValueError("race_risk_cap must be positive")
    rows=[]
    for x in selections:
        r=float(x["requested_risk_units"])
        if r < 0:
            raise ValueError("requested_risk_units must be non-negative")
        if r == 0:
            continue
        y=dict(x)
        y["requested_risk_units"]=r
        rows.append(y)

    requested=sum(x["requested_risk_units"] for x in rows)
    scale=1.0 if requested <= race_risk_cap or requested == 0 else race_risk_cap/requested
    for x in rows:
        x["allocated_risk_units"]=x["requested_risk_units"]*scale

    allocated=sum(x["allocated_risk_units"] for x in rows)
    return {
        "requested_total_risk_units":requested,
        "race_risk_cap":race_risk_cap,
        "scale_factor":scale,
        "allocated_total_risk_units":allocated,
        "cap_respected":allocated <= race_risk_cap + 1e-12,
        "selections":rows,
        "real_money_instruction":False,
    }

def _self_test():
    one=aggregate([{"id":"CORE","requested_risk_units":1.0}])
    assert abs(one["allocated_total_risk_units"]-1.0)<1e-12

    both=aggregate([
        {"id":"CORE","requested_risk_units":1.0},
        {"id":"MID","requested_risk_units":0.5},
    ])
    assert abs(both["allocated_total_risk_units"]-1.0)<1e-12
    assert abs(both["selections"][0]["allocated_risk_units"]-(2/3))<1e-12
    assert abs(both["selections"][1]["allocated_risk_units"]-(1/3))<1e-12

    sparse=aggregate([
        {"id":"LONG","requested_risk_units":0.25},
        {"id":"EXTREME","requested_risk_units":0.10},
    ])
    assert abs(sparse["allocated_total_risk_units"]-0.35)<1e-12
    print("PASS")

if __name__=="__main__":
    _self_test()
