#!/usr/bin/env python3
"""Evidence sufficiency diagnostics for future longshot shadow validation.

No fetching is performed. Caller supplies already-authorized, frozen decision rows.
The purpose is to prevent claiming stability from too little expected-hit mass.
"""
from collections import defaultdict
from typing import Iterable, Dict, List

BANDS=("MID_HOLE","LONGSHOT","EXTREME_LONGSHOT")
MIN_EXPECTED_HITS=5.0
MIN_ACTUAL_HITS=5
MIN_WEEKS=8

def evaluate(rows: Iterable[Dict]) -> Dict:
    xs=list(rows)
    out=[]
    for band in BANDS:
        bs=[x for x in xs if x["band"]==band]
        expected_hits=sum(float(x["conservative_probability"]) for x in bs)
        actual_hits=sum(1 for x in bs if float(x.get("return_units",0.0))>0)
        weeks=len(set(str(x["iso_week"]) for x in bs if x.get("iso_week") is not None))
        out.append({
            "band":band,
            "decisions":len(bs),
            "expected_hits_under_frozen_conservative_probability":expected_hits,
            "actual_hits":actual_hits,
            "calendar_weeks":weeks,
            "minimum_expected_hits":MIN_EXPECTED_HITS,
            "minimum_actual_hits":MIN_ACTUAL_HITS,
            "minimum_weeks":MIN_WEEKS,
            "evidence_sufficient":(
                expected_hits>=MIN_EXPECTED_HITS
                and actual_hits>=MIN_ACTUAL_HITS
                and weeks>=MIN_WEEKS
            ),
        })
    return {
        "status":"PROPOSED_EVIDENCE_SUFFICIENCY_ONLY",
        "bands":out,
        "all_bands_sufficient":all(x["evidence_sufficient"] for x in out),
        "real_money_authorized":False,
    }

def required_decisions_for_expected_hits(avg_probability: float, expected_hits: float=MIN_EXPECTED_HITS) -> float:
    if avg_probability<=0:
        raise ValueError("avg_probability must be positive")
    return expected_hits/avg_probability

def _self_test():
    assert abs(required_decisions_for_expected_hits(0.05)-100.0)<1e-9
    assert abs(required_decisions_for_expected_hits(0.01)-500.0)<1e-9
    assert abs(required_decisions_for_expected_hits(0.002)-2500.0)<1e-9
    print("PASS")

if __name__=="__main__":
    _self_test()
