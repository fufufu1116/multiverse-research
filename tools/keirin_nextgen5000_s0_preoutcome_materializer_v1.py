#!/usr/bin/env python3
"""Materialize outcome-blind S0 selections from strict NEXTGEN5000 PRE-only CSV.

This tool is intentionally price-, result-, payout-, forecast- and comment-blind.
It freezes a simple score-only baseline before any outcome join.

Research role: RETROSPECTIVE_PRE_DEVELOPMENT_ONLY_UNPROVEN_PIT.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import defaultdict
from pathlib import Path

BETA=0.22260435254784533
RULE_ID="S0_NON_GIRLS_GAP_LT3_CONF40_TOP3_3RENHUKU_1PT_NO_PRICE_FILTER"
FORBIDDEN={"result","finish","payout","settlement","odds","forecast","prediction","tips","comment","narabiyoso","roi","ev"}

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def softmax(xs):
    m=max(xs); z=[math.exp(x-m) for x in xs]; s=sum(z)
    return [x/s for x in z]

def materialize(rows):
    races=defaultdict(list)
    for r in rows:
        races[r["race_id"]].append(r)
    out=[]
    for rid, rr in races.items():
        rr=sorted(rr,key=lambda x:int(x["car_no"]))
        cars=[int(x["car_no"]) for x in rr]
        if cars != list(range(1,max(cars)+1)):
            raise ValueError(f"FAIL-CLOSED:car_continuity:{rid}")
        scores=[float(x["competition_score"]) for x in rr]
        ps=softmax([BETA*s for s in scores])
        rec=[]
        for r,p in zip(rr,ps):
            rec.append({
                "car_no":int(r["car_no"]),
                "rider_name_raw":r["rider_name_raw"],
                "class":r["class"],
                "style":r.get("style") or None,
                "competition_score":float(r["competition_score"]),
                "s0_probability":p
            })
        order=sorted(rec,key=lambda x:(-x["s0_probability"],x["car_no"]))
        top_scores=sorted(scores,reverse=True)
        gap=top_scores[0]-top_scores[1]
        girls=all(x["class"]=="L1" for x in rec)
        top1=order[0]
        top3=[x["car_no"] for x in order[:3]]
        ticket="=".join(map(str,sorted(top3)))
        selected=(not girls) and gap<3.0 and top1["s0_probability"]>=0.40
        src_hashes=sorted({r["source_file_sha256"] for r in rr})
        if len(src_hashes)!=1:
            raise ValueError(f"FAIL-CLOSED:mixed_source_hash:{rid}")
        out.append({
            "race_id":rid,
            "race_date":rr[0]["race_date"],
            "venue":rr[0]["venue"],
            "race_no":int(rr[0]["race_no"]),
            "rider_count":len(rr),
            "girls":girls,
            "top_score_gap":gap,
            "s0_top1_car":top1["car_no"],
            "s0_top1_probability":top1["s0_probability"],
            "s0_top3_cars":top3,
            "s0_top3_3renhuku_ticket":ticket,
            "selected_by_frozen_rule":selected,
            "source_file_sha256":src_hashes[0],
            "riders":rec
        })
    out.sort(key=lambda x:(x["race_date"],x["race_id"]))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pre-csv",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    with open(a.pre_csv,encoding="utf-8",newline="") as f:
        rd=csv.DictReader(f)
        fields={x.lower() for x in (rd.fieldnames or [])}
        bad=FORBIDDEN & fields
        if bad: raise SystemExit(f"FAIL-CLOSED:forbidden_columns:{sorted(bad)}")
        rows=list(rd)
    if not rows: raise SystemExit("FAIL-CLOSED:no_rows")
    required={"race_id","race_date","venue","race_no","car_no","rider_name_raw","class","competition_score","source_file_sha256"}
    missing=required-{k for k in rows[0]}
    if missing: raise SystemExit(f"FAIL-CLOSED:missing_columns:{sorted(missing)}")
    races=materialize(rows)
    payload={
        "record":"KEIRIN_NEXTGEN5000_S0_PREOUTCOME_SELECTION_MATERIALIZATION_v1",
        "status":"PRE_ONLY_SELECTION_FROZEN_NO_OUTCOME_ACCESS",
        "evidence_role":"RETROSPECTIVE_PRE_DEVELOPMENT_ONLY_UNPROVEN_PIT",
        "pre_csv_sha256":sha256_file(a.pre_csv),
        "model":{
            "name":"S0_SCORE_ONLY_SOFTMAX",
            "beta":BETA,
            "beta_frozen":True,
            "result_fit":False
        },
        "selection_rule":{
            "id":RULE_ID,
            "girls":False,
            "top_score_gap_lt":3.0,
            "s0_top1_probability_gte":0.40,
            "ticket":"one 3renhuku ticket using S0 top3 set",
            "odds_filter":None,
            "flat_hypothetical_stake_yen":100
        },
        "safeguards":{
            "result_accessed":False,
            "payout_accessed":False,
            "odds_accessed":False,
            "forecast_or_comment_accessed":False,
            "circumference_required":False,
            "model_refit":False,
            "formal_support_increment_authorized":False,
            "model_promotion_authorized":False,
            "runtime":False
        },
        "summary":{
            "races":len(races),
            "rider_rows":sum(x["rider_count"] for x in races),
            "girls_races":sum(x["girls"] for x in races),
            "selected_races":sum(x["selected_by_frozen_rule"] for x in races)
        },
        "races":races
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload["summary"],ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
