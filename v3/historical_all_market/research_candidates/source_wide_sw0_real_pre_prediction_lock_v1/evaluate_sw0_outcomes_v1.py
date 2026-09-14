#!/usr/bin/env python3
import argparse, csv, gzip, hashlib, json, math, random
from collections import defaultdict
from pathlib import Path

ALLOWED_OUTCOME_FIELDS = ["race_id","first","second","third"]

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_predictions(path, expected_sha):
    if sha256_file(path) != expected_sha:
        raise SystemExit("FAIL_CLOSED:PREDICTION_SHA_MISMATCH")
    rows=[]
    with gzip.open(path,"rt",encoding="utf-8") as f:
        for line in f:
            x=json.loads(line)
            if set(x.keys()) != {"race_id","dev_index","ordered_top3_probabilities"}:
                raise SystemExit("FAIL_CLOSED:PREDICTION_SCHEMA")
            probs=x["ordered_top3_probabilities"]
            if not probs:
                raise SystemExit("FAIL_CLOSED:EMPTY_PROBABILITY_TABLE")
            mass=sum(float(t[3]) for t in probs)
            if not math.isfinite(mass) or abs(mass-1.0)>1e-8:
                raise SystemExit("FAIL_CLOSED:PROBABILITY_MASS")
            rows.append(x)
    if len(rows)!=1500 or sorted(r["dev_index"] for r in rows)!=list(range(1,1501)):
        raise SystemExit("FAIL_CLOSED:PREDICTION_UNIVERSE")
    return rows

def _accept_outcome_row(row, out):
    if list(row.keys()) != ALLOWED_OUTCOME_FIELDS and set(row.keys()) != set(ALLOWED_OUTCOME_FIELDS):
        raise SystemExit("FAIL_CLOSED:OUTCOME_SCHEMA_OR_EXTRA_FIELDS")
    rid=str(row["race_id"])
    if rid in out:
        raise SystemExit("FAIL_CLOSED:DUPLICATE_OUTCOME_RACE")
    vals=tuple(int(row[k]) for k in ("first","second","third"))
    if len(set(vals))!=3:
        raise SystemExit("FAIL_CLOSED:MALFORMED_FINISH_ORDER")
    out[rid]=vals

def load_outcomes(path, expected_sha):
    if sha256_file(path) != expected_sha:
        raise SystemExit("FAIL_CLOSED:OUTCOME_SHA_MISMATCH")
    out={}
    suffix=Path(path).suffix.lower()
    if suffix==".csv":
        with open(path,newline="",encoding="utf-8") as f:
            r=csv.DictReader(f)
            if r.fieldnames != ALLOWED_OUTCOME_FIELDS:
                raise SystemExit("FAIL_CLOSED:OUTCOME_SCHEMA_OR_EXTRA_COLUMNS")
            for row in r:
                _accept_outcome_row(row,out)
    elif suffix==".jsonl":
        with open(path,encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    raise SystemExit("FAIL_CLOSED:BLANK_OUTCOME_RECORD")
                row=json.loads(line)
                if not isinstance(row,dict):
                    raise SystemExit("FAIL_CLOSED:OUTCOME_RECORD_NOT_OBJECT")
                _accept_outcome_row(row,out)
    else:
        raise SystemExit("FAIL_CLOSED:OUTCOME_FORMAT_NOT_ALLOWED")
    return out

def race_metrics(pred, outcome):
    table={(int(a),int(b),int(c)):float(p) for a,b,c,p in pred["ordered_top3_probabilities"]}
    entrants=sorted({k for t in table for k in t})
    n=len(entrants)
    if outcome not in table:
        raise SystemExit("FAIL_CLOSED:OUTCOME_CAR_NOT_IN_PREDICTION")
    p_exact=table[outcome]
    if p_exact<=0 or not math.isfinite(p_exact):
        raise SystemExit("FAIL_CLOSED:ZERO_OR_NONFINITE_OBSERVED_PROB")
    win=defaultdict(float)
    for (a,b,c),p in table.items():
        win[a]+=p
    y=outcome[0]
    pwin=win[y]
    if pwin<=0 or pwin>=1+1e-10:
        raise SystemExit("FAIL_CLOSED:WINNER_MARGINAL")
    top1=max(entrants, key=lambda car:(win[car],-car))
    pred_exact=max(table, key=lambda t:(table[t], tuple(-x for x in t)))
    setp=defaultdict(float)
    for t,p in table.items():
        setp[tuple(sorted(t))]+=p
    pred_set=max(setp, key=lambda s:(setp[s], tuple(-x for x in s)))
    brier=sum((win[c]-(1.0 if c==y else 0.0))**2 for c in entrants)
    uniform_exact=1.0/(n*(n-1)*(n-2))
    uniform_win=1.0/n
    uniform_brier=sum((uniform_win-(1.0 if c==y else 0.0))**2 for c in entrants)
    return {
      "dev_index": pred["dev_index"],
      "sw0_exact_nll": -math.log(p_exact),
      "uniform_exact_nll": -math.log(uniform_exact),
      "sw0_win_nll": -math.log(pwin),
      "uniform_win_nll": -math.log(uniform_win),
      "sw0_brier": brier,
      "uniform_brier": uniform_brier,
      "top1_hit": int(top1==y),
      "ordered_top3_hit": int(pred_exact==outcome),
      "unordered_top3_hit": int(tuple(sorted(outcome))==pred_set),
    }

def mean(xs): return sum(xs)/len(xs)

def summarize(ms):
    return {
      "race_count":len(ms),
      "mean_sw0_exact_nll":mean([m["sw0_exact_nll"] for m in ms]),
      "mean_uniform_exact_nll":mean([m["uniform_exact_nll"] for m in ms]),
      "primary_effect_uniform_minus_sw0":mean([m["uniform_exact_nll"]-m["sw0_exact_nll"] for m in ms]),
      "mean_sw0_win_nll":mean([m["sw0_win_nll"] for m in ms]),
      "mean_uniform_win_nll":mean([m["uniform_win_nll"] for m in ms]),
      "mean_sw0_brier":mean([m["sw0_brier"] for m in ms]),
      "mean_uniform_brier":mean([m["uniform_brier"] for m in ms]),
      "winner_brier_improvement":mean([m["uniform_brier"]-m["sw0_brier"] for m in ms]),
      "top1_accuracy":mean([m["top1_hit"] for m in ms]),
      "ordered_top3_hit_rate":mean([m["ordered_top3_hit"] for m in ms]),
      "unordered_top3_set_hit_rate":mean([m["unordered_top3_hit"] for m in ms]),
    }

def bootstrap_effect(ms, reps=10000, seed=20260914):
    rng=random.Random(seed)
    vals=[m["uniform_exact_nll"]-m["sw0_exact_nll"] for m in ms]
    n=len(vals); out=[]
    for _ in range(reps):
        out.append(sum(vals[rng.randrange(n)] for __ in range(n))/n)
    out.sort()
    return [out[int(0.025*reps)], out[int(0.975*reps)-1]]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--predictions",required=True)
    ap.add_argument("--prediction-sha256",required=True)
    ap.add_argument("--outcomes",required=True)
    ap.add_argument("--outcome-sha256",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    preds=load_predictions(args.predictions,args.prediction_sha256)
    outs=load_outcomes(args.outcomes,args.outcome_sha256)
    pids={p["race_id"] for p in preds}
    if set(outs)!=pids:
        raise SystemExit("FAIL_CLOSED:OUTCOME_RACE_SET_NOT_EXACT_PREDICTION_SET")
    ms=[race_metrics(p,outs[p["race_id"]]) for p in preds]
    pooled=summarize(ms)
    a=summarize([m for m in ms if m["dev_index"]<=1000])
    b=summarize([m for m in ms if m["dev_index"]>=1001])
    ci=bootstrap_effect(ms)
    strong=(pooled["primary_effect_uniform_minus_sw0"]>0 and ci[0]>0
            and a["primary_effect_uniform_minus_sw0"]>0
            and b["primary_effect_uniform_minus_sw0"]>0
            and pooled["winner_brier_improvement"]>0)
    if strong: verdict="STRONG_PREDICTIVE_SIGNAL"
    elif pooled["primary_effect_uniform_minus_sw0"]>0: verdict="POSITIVE_BUT_UNCERTAIN"
    else: verdict="NO_PREDICTIVE_SIGNAL"
    result={"verdict":verdict,"evidence_class":"LINEAGE_LOCAL_PREOUTCOME_HISTORICAL_PREDICTIVE_EVALUATION_NOT_GLOBAL_UNTOUCHED_HOLDOUT",
            "pooled":pooled,"segment_A":a,"segment_B":b,"primary_effect_bootstrap_95pct":ci,
            "prohibitions":{"model_promotion":True,"odds_price_payout_economics":True,"DEV2000_C":True,"ECON_HOLDOUT1000":True}}
    with open(args.output,"w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2); f.write("\n")

if __name__=="__main__":
    main()
