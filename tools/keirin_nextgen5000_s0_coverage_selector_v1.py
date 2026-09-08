#!/usr/bin/env python3
"""Choose and freeze an S0 NEXTGEN5000 evaluation rule from PRE-side coverage only.

No outcomes, payouts, odds, forecasts or comments are accepted or read.
The choice rule is fixed by KEIRIN_NEXTGEN5000_S0_COVERAGE_THRESHOLD_SELECTION_PRESPEC_20260909_v1.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

P_THRESHOLDS=[0.40,0.38,0.36,0.34,0.32,0.30,0.28,0.26,0.24,0.22,0.20]
GAPS=[3.0,5.0,None]
MIN_TOTAL=200
MIN_HALF=75
PRESPEC="KEIRIN_NEXTGEN5000_S0_COVERAGE_THRESHOLD_SELECTION_PRESPEC_20260909_v1"

def load_races(paths):
    races=[]
    seen=set()
    for p in paths:
        x=json.loads(Path(p).read_text(encoding="utf-8"))
        s=x.get("safeguards",{})
        if s.get("result_accessed") is not False or s.get("payout_accessed") is not False or s.get("odds_accessed") is not False:
            raise ValueError(f"FAIL-CLOSED:nonblind_input:{p}")
        for r in x["races"]:
            rid=r["race_id"]
            if rid in seen: raise ValueError(f"FAIL-CLOSED:duplicate_race:{rid}")
            seen.add(rid); races.append(r)
    races.sort(key=lambda r:(r["race_date"],r["race_id"]))
    return races

def eligible(r,pthr,gap):
    if r["girls"]: return False
    if float(r["s0_top1_probability"]) < pthr: return False
    if gap is not None and not (float(r["top_score_gap"]) < gap): return False
    return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",action="append",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    races=load_races(a.input)
    n=len(races)
    if n<1000: raise SystemExit("FAIL-CLOSED:too_few_races")
    split=n//2
    early=races[:split]; late=races[split:]
    grid=[]; chosen=None
    for gap in GAPS:
        for p in P_THRESHOLDS:
            total=sum(eligible(r,p,gap) for r in races)
            e=sum(eligible(r,p,gap) for r in early)
            l=sum(eligible(r,p,gap) for r in late)
            row={"gap_lt":gap,"top1_probability_gte":p,"selected_total":total,"selected_early_half":e,"selected_late_half":l,
                 "coverage_pass": total>=MIN_TOTAL and e>=MIN_HALF and l>=MIN_HALF}
            grid.append(row)
            if chosen is None and row["coverage_pass"]:
                chosen=row.copy()
        if chosen is not None: break
    selected=[]
    if chosen is not None:
        for r in races:
            if eligible(r,chosen["top1_probability_gte"],chosen["gap_lt"]):
                selected.append({
                    "race_id":r["race_id"],"race_date":r["race_date"],"venue":r["venue"],"race_no":r["race_no"],
                    "s0_top1_car":r["s0_top1_car"],"s0_top1_probability":r["s0_top1_probability"],
                    "s0_top3_cars":r["s0_top3_cars"],"ticket_3renhuku":r["s0_top3_3renhuku_ticket"],
                    "top_score_gap":r["top_score_gap"],"source_file_sha256":r["source_file_sha256"]
                })
    payload={
      "record":"KEIRIN_NEXTGEN5000_S0_PREOUTCOME_COVERAGE_SELECTION_FREEZE_20260909_v1",
      "status":"PREOUTCOME_SELECTION_FROZEN" if chosen is not None else "NO_S0_COVERAGE_RULE",
      "prespec":PRESPEC,
      "input_races":n,
      "chronological_split":{"early_half_races":len(early),"late_half_races":len(late),
                             "early_last_key":[early[-1]["race_date"],early[-1]["race_id"]],
                             "late_first_key":[late[0]["race_date"],late[0]["race_id"]]},
      "coverage_targets":{"selected_total_gte":MIN_TOTAL,"each_half_gte":MIN_HALF},
      "grid":grid,
      "chosen_rule":chosen,
      "selected_races":selected,
      "selected_count":len(selected),
      "selection_definition":{
        "girls":False,
        "ticket":"one 3renhuku ticket = S0 top3 set",
        "odds_filter":None,
        "flat_hypothetical_stake_yen":100
      },
      "safeguards":{
        "result_accessed":False,"payout_accessed":False,"odds_accessed":False,
        "performance_metric_used_to_choose_threshold":False,
        "selection_count_only":True,"DEV2000_C_scoring_count":0,
        "ECON_HOLDOUT1000_opened":False,"formal_support_increment_authorized":False,
        "model_promotion_authorized":False,"runtime":False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"input_races":n,"chosen_rule":chosen,"selected_count":len(selected)},ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
