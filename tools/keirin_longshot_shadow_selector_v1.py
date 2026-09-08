#!/usr/bin/env python3
"""Select at most one qualified longshot shadow ticket per race.

Caller supplies already-authorized PRE ticket probabilities/odds.
No external fetch, outcome access, payout access, or live execution occurs here.
"""
from typing import Iterable, Dict, List
from keirin_longshot_shadow_guard_v1 import evaluate_ticket

LONGSHOT_BANDS={"MID_HOLE","LONGSHOT","EXTREME_LONGSHOT"}

def select_one(ticket_rows: Iterable[Dict]) -> Dict:
    evaluated: List[Dict] = []
    for row in ticket_rows:
        ev=evaluate_ticket(
            float(row["s0_probability"]),
            float(row["challenger_probability"]),
            float(row["decimal_odds"]),
        )
        merged=dict(row)
        merged.update(ev)
        evaluated.append(merged)

    qualified=[x for x in evaluated if x["qualifies"] and x["band"] in LONGSHOT_BANDS]
    if not qualified:
        return {
            "action":"NO_BET",
            "selected":None,
            "qualified_count":0,
            "evaluated_count":len(evaluated),
            "real_money_instruction":False,
        }

    # Prefer stronger guarded probability ratio. Tie-break on lower odds, then ticket key
    # to avoid choosing a more extreme tail ticket without extra evidence.
    qualified.sort(
        key=lambda x:(
            -float(x["probability_ratio"]),
            float(x["decimal_odds"]),
            str(x.get("ticket","")),
        )
    )
    chosen=qualified[0]
    return {
        "action":"SHADOW_SELECT_ONE",
        "selected":chosen,
        "qualified_count":len(qualified),
        "evaluated_count":len(evaluated),
        "discarded_qualified_count":max(0,len(qualified)-1),
        "race_longshot_ticket_cap":1,
        "real_money_instruction":False,
    }

def _self_test():
    rows=[
        {"ticket":"1=2=3","s0_probability":0.05,"challenger_probability":0.052,"decimal_odds":30.0},
        {"ticket":"1=2=4","s0_probability":0.012,"challenger_probability":0.013,"decimal_odds":150.0},
        {"ticket":"1=2=5","s0_probability":0.006,"challenger_probability":0.007,"decimal_odds":500.0},
    ]
    out=select_one(rows)
    assert out["action"]=="SHADOW_SELECT_ONE"
    assert out["selected"]["ticket"]=="1=2=5"
    assert out["qualified_count"]==3
    assert out["discarded_qualified_count"]==2
    print("PASS")

if __name__=="__main__":
    _self_test()
