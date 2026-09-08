#!/usr/bin/env python3
"""Prospective validation gate for longshot shadow ledgers.

Input rows are already-settled research/shadow records supplied by caller.
This tool does not fetch outcomes, payouts, odds, or external data.
"""

from collections import defaultdict
from datetime import date
from typing import Iterable, Dict, List

MIN_DECISIONS={"MID_HOLE":100,"LONGSHOT":200,"EXTREME_LONGSHOT":500}
MIN_HITS={"MID_HOLE":5,"LONGSHOT":5,"EXTREME_LONGSHOT":5}

def _roi(stake, ret):
    return None if stake <= 0 else ret/stake - 1.0

def evaluate_band(rows: Iterable[Dict], band: str) -> Dict:
    xs=[dict(x) for x in rows if x["band"]==band]
    stake=sum(float(x["stake_units"]) for x in xs)
    ret=sum(float(x["return_units"]) for x in xs)
    hits=[x for x in xs if float(x["return_units"])>0]
    largest=max(hits,key=lambda x: float(x["return_units"]),default=None)
    leave_rows=[x for x in xs if x is not largest]
    leave_stake=sum(float(x["stake_units"]) for x in leave_rows)
    leave_ret=sum(float(x["return_units"]) for x in leave_rows)
    roi=_roi(stake,ret)
    leave_roi=_roi(leave_stake,leave_ret)
    profit=max(ret-stake,0.0)
    largest_profit_contribution=0.0
    if largest is not None and profit>0:
        largest_profit_contribution=max(float(largest["return_units"])-float(largest["stake_units"]),0.0)/profit

    weeks=defaultdict(lambda:[0.0,0.0])
    for x in xs:
        d=date.fromisoformat(x["date"])
        iso=d.isocalendar()
        key=f"{iso.year}-W{iso.week:02d}"
        weeks[key][0]+=float(x["stake_units"])
        weeks[key][1]+=float(x["return_units"])
    weekly_roi={k:_roi(v[0],v[1]) for k,v in sorted(weeks.items())}

    proposed_pass=(
        len(xs)>=MIN_DECISIONS[band]
        and len(hits)>=MIN_HITS[band]
        and roi is not None and roi>0
        and leave_roi is not None and leave_roi>0
        and largest_profit_contribution<=0.50
        and len(weeks)>=8
    )
    return {
        "band":band,
        "decisions":len(xs),
        "hits":len(hits),
        "stake_units":stake,
        "return_units":ret,
        "roi":roi,
        "leave_largest_hit_out_roi":leave_roi,
        "largest_hit_share_of_profit":largest_profit_contribution,
        "calendar_weeks":len(weeks),
        "weekly_roi":weekly_roi,
        "proposed_min_decisions":MIN_DECISIONS[band],
        "proposed_min_hits":MIN_HITS[band],
        "proposed_stable_pass":proposed_pass,
    }

def evaluate(rows: Iterable[Dict]) -> Dict:
    rows=list(rows)
    bands=[evaluate_band(rows,b) for b in ("MID_HOLE","LONGSHOT","EXTREME_LONGSHOT")]
    return {
        "status":"PROPOSED_VALIDATION_GATE_ONLY",
        "bands":bands,
        "any_band_stable_pass":any(x["proposed_stable_pass"] for x in bands),
        "real_money_authorized":False,
    }

def _self_test():
    rows=[]
    # Synthetic MID_HOLE fixture: 100 decisions over 10 weeks, 10 hits,
    # distributed returns so no single hit creates all profit.
    for i in range(100):
        week=(i//10)+1
        day=min(28,1+(i%10))
        ret=0.0
        if i%10==0:
            ret=13.0
        rows.append({
            "band":"MID_HOLE",
            "date":f"2026-{1+(week-1)//4:02d}-{day:02d}",
            "stake_units":1.0,
            "return_units":ret,
        })
    out=evaluate(rows)
    mid=out["bands"][0]
    assert mid["decisions"]==100
    assert mid["hits"]==10
    print("PASS")

if __name__=="__main__":
    _self_test()
