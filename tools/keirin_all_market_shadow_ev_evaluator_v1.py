#!/usr/bin/env python3
"""Research-only all-market shadow EV evaluator.

Consumes a coherent ordered-top3 probability object plus timestamped observed odds.
Derives 3rentan / 3renhuku / 2shatan / 2shahuku / wide probabilities from the
single probability source of truth and computes fair odds and shadow EV.
No network access and no bet placement.
"""
from __future__ import annotations
import argparse, json, math
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def derive(ordered_top3):
    out = {m: defaultdict(float) for m in ("3rentan","3renhuku","2shatan","2shahuku","wide")}
    for key, p in ordered_top3.items():
        a,b,c = key
        out["3rentan"][key] += p
        out["3renhuku"][tuple(sorted(key))] += p
        out["2shatan"][(a,b)] += p
        out["2shahuku"][tuple(sorted((a,b)))] += p
        for x,y in combinations(key,2):
            out["wide"][tuple(sorted((x,y)))] += p
    return {k: dict(v) for k,v in out.items()}


def parse_ticket(market, ticket):
    vals = tuple(int(x) for x in str(ticket).replace("-", " ").split())
    need = 3 if market in ("3rentan","3renhuku") else 2
    if len(vals) != need or len(set(vals)) != need:
        raise ValueError("invalid_ticket")
    if market in ("3renhuku","2shahuku","wide"):
        vals = tuple(sorted(vals))
    return vals


def load_probability(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    records = obj.get("ordered_top3") or obj.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("missing_ordered_top3")
    d = {}
    for r in records:
        key=(int(r["first"]),int(r["second"]),int(r["third"]))
        p=float(r["p"])
        if key in d or len(set(key)) != 3 or not math.isfinite(p) or p < 0:
            raise ValueError("invalid_probability_record")
        d[key]=p
    mass=sum(d.values())
    if abs(mass-1.0)>1e-9:
        raise ValueError(f"probability_mass={mass}")
    return obj,d


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("probability_json")
    ap.add_argument("odds_jsonl")
    ap.add_argument("output_jsonl")
    ap.add_argument("receipt_json")
    a=ap.parse_args()
    pobj, ordered = load_probability(a.probability_json)
    markets=derive(ordered)
    supported=set(markets)
    rows=[]; rejects=[]
    for ln,line in enumerate(Path(a.odds_jsonl).read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try:
            x=json.loads(line); market=x["market"]
            if market not in supported: raise ValueError("unsupported_market")
            if x.get("result_known") is not False: raise ValueError("result_known_must_be_false")
            ticket=parse_ticket(market,x["ticket"]); odds=float(x["decimal_odds"])
            if not math.isfinite(odds) or odds <= 1.0: raise ValueError("invalid_decimal_odds")
            p=markets[market].get(ticket)
            if p is None or p <= 0: raise ValueError("ticket_not_in_probability_support")
            ev=p*odds-1.0
            rows.append({
                "race_id":x["race_id"],"market":market,"ticket":"-".join(map(str,ticket)),
                "model_probability":p,"fair_decimal_odds":1.0/p,"observed_decimal_odds":odds,
                "expected_return_multiple":p*odds,"shadow_ev_per_unit":ev,
                "shadow_label":"SHADOW_POSITIVE_EV_CANDIDATE" if ev>0 else "SHADOW_PASS",
                "observed_at":x["observed_at"],"source_or_observer":x["source_or_observer"],
                "result_known":False,"model_version":pobj.get("model_version"),"model_hash":pobj.get("model_hash")
            })
        except Exception as e:
            rejects.append({"line":ln,"reason":str(e)})
    Path(a.output_jsonl).write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows),encoding="utf-8")
    receipt={"record":"KEIRIN_ALL_MARKET_SHADOW_EV_EVALUATION_RECEIPT_v1","accepted":len(rows),"rejected":len(rejects),"rejects":rejects[:50],"markets_seen":sorted(set(x["market"] for x in rows)),"network_access":False,"real_money_execution":False,"automated_bet_placement":False}
    Path(a.receipt_json).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
