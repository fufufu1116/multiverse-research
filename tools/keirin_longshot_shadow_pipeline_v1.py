#!/usr/bin/env python3
"""End-to-end outcome-free shadow pipeline for core + hole research candidates.

Pipeline:
1. Evaluate caller-supplied hole tickets against the frozen band guard.
2. Select at most one qualifying hole ticket.
3. Combine any prequalified CORE selection with the selected hole.
4. Proportionally cap total race risk at one research unit.

This module fetches nothing and issues no real-money instruction.
"""
from typing import Dict, Iterable, Optional
from keirin_longshot_shadow_selector_v1 import select_one
from keirin_shadow_risk_aggregator_v1 import aggregate

BAND_RISK={"MID_HOLE":0.50,"LONGSHOT":0.25,"EXTREME_LONGSHOT":0.10}

def run_pipeline(
    hole_ticket_rows: Iterable[Dict],
    core_selection: Optional[Dict]=None,
    race_risk_cap: float=1.0,
) -> Dict:
    hole=select_one(hole_ticket_rows)
    selections=[]

    if core_selection is not None:
        c=dict(core_selection)
        c.setdefault("lane","CORE")
        c.setdefault("requested_risk_units",1.0)
        selections.append(c)

    if hole["action"]=="SHADOW_SELECT_ONE":
        h=dict(hole["selected"])
        band=h["band"]
        h["lane"]=band
        h["requested_risk_units"]=BAND_RISK[band]
        selections.append(h)

    risk=aggregate(selections,race_risk_cap=race_risk_cap)
    return {
        "hole_selector":hole,
        "risk_aggregation":risk,
        "real_money_instruction":False,
    }

def _self_test():
    rows=[
        {
            "ticket":"MID",
            "s0_probability":0.050,
            "challenger_probability":0.052,
            "decimal_odds":30.0,
        },
        {
            "ticket":"LONG_FAIL",
            "s0_probability":0.010,
            "challenger_probability":0.012,
            "decimal_odds":150.0,
        },
        {
            "ticket":"EXTREME",
            "s0_probability":0.006,
            "challenger_probability":0.007,
            "decimal_odds":500.0,
        },
    ]
    out=run_pipeline(
        rows,
        core_selection={"ticket":"CORE","requested_risk_units":1.0},
    )
    assert out["hole_selector"]["selected"]["ticket"]=="EXTREME"
    assert out["hole_selector"]["qualified_count"]==2
    assert out["risk_aggregation"]["cap_respected"] is True
    assert abs(out["risk_aggregation"]["allocated_total_risk_units"]-1.0)<1e-12

    only_core=run_pipeline(
        [{"ticket":"NO","s0_probability":0.005,"challenger_probability":0.005,"decimal_odds":100.0}],
        core_selection={"ticket":"CORE","requested_risk_units":1.0},
    )
    assert only_core["hole_selector"]["action"]=="NO_BET"
    assert abs(only_core["risk_aggregation"]["allocated_total_risk_units"]-1.0)<1e-12
    print("PASS")

if __name__=="__main__":
    _self_test()
