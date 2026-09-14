#!/usr/bin/env python3
import argparse, csv, gzip, json, math, random, statistics
from pathlib import Path

EPS = 1e-300

def read_predictions(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    rows = {}
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            rid = str(r["race_id"])
            if rid in rows:
                raise ValueError(f"duplicate prediction race_id: {rid}")
            probs = {}
            cars = set()
            for a,b,c,p in r["ordered_top3_probabilities"]:
                t=(int(a),int(b),int(c))
                probs[t]=float(p)
                cars.update(t)
            mass=sum(probs.values())
            if abs(mass-1.0)>1e-8:
                raise ValueError(f"prediction mass error {rid}: {mass}")
            rows[rid]={"dev_index":int(r["dev_index"]), "probs":probs, "cars":sorted(cars)}
    return rows

def read_outcomes(path):
    p=str(path)
    rows={}
    if p.endswith(".jsonl") or p.endswith(".jsonl.gz"):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(path,"rt",encoding="utf-8") as f:
            it=(json.loads(x) for x in f if x.strip())
            for r in it:
                rid=str(r["race_id"])
                if rid in rows: raise ValueError(f"duplicate outcome race_id: {rid}")
                rows[rid]=r
    else:
        with open(path,newline="",encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rid=str(r["race_id"])
                if rid in rows: raise ValueError(f"duplicate outcome race_id: {rid}")
                rows[rid]=r
    out={}
    for rid,r in rows.items():
        out[rid]=(int(r["first_car_no"]),int(r["second_car_no"]),int(r["third_car_no"]))
    return out

def race_metrics(pred, obs):
    probs=pred["probs"]; cars=pred["cars"]; n=len(cars)
    if len(obs)!=3 or len(set(obs))!=3 or any(c not in cars for c in obs):
        raise ValueError("invalid observed ordered top3")
    q=max(probs.get(tuple(obs),0.0),EPS)
    ordered_ll=-math.log(q)
    m=n*(n-1)*(n-2)
    ordered_impr=math.log(m)-ordered_ll
    sumsq=sum(p*p for p in probs.values())
    ordered_brier=sumsq - 2*q + 1.0
    uniform_brier=1.0 - 1.0/m
    ordered_brier_skill=1.0 - ordered_brier/uniform_brier
    ranked=sorted(probs.items(), key=lambda kv:(-kv[1],kv[0]))
    argmax_hit=1.0 if ranked[0][0]==tuple(obs) else 0.0
    rank=next(i+1 for i,(t,_) in enumerate(ranked) if t==tuple(obs))
    cov={f"top{k}_coverage":1.0 if rank<=k else 0.0 for k in (1,3,5,10,20)}
    win={c:0.0 for c in cars}
    inc={c:0.0 for c in cars}
    for (a,b,c),p in probs.items():
        win[a]+=p
        inc[a]+=p; inc[b]+=p; inc[c]+=p
    w=obs[0]
    wq=max(win[w],EPS)
    winner_ll=-math.log(wq)
    winner_impr=math.log(n)-winner_ll
    winner_brier=sum((win[c]-(1.0 if c==w else 0.0))**2 for c in cars)
    uniform_winner_brier=1.0-1.0/n
    winner_brier_skill=1.0-winner_brier/uniform_winner_brier
    winner_top1=1.0 if max(cars,key=lambda c:(win[c],-c))==w else 0.0
    actual_top3=set(obs)
    top3_brier=sum((inc[c]-(1.0 if c in actual_top3 else 0.0))**2 for c in cars)/n
    d={
      "ordered_top3_log_loss":ordered_ll,
      "ordered_top3_log_loss_improvement_vs_uniform":ordered_impr,
      "ordered_top3_brier":ordered_brier,
      "ordered_top3_brier_skill_vs_uniform":ordered_brier_skill,
      "exact_order_argmax_accuracy":argmax_hit,
      "observed_order_probability_rank":float(rank),
      "winner_log_loss":winner_ll,
      "winner_log_loss_improvement_vs_uniform":winner_impr,
      "winner_multiclass_brier":winner_brier,
      "winner_brier_skill_vs_uniform":winner_brier_skill,
      "winner_top1_accuracy":winner_top1,
      "top3_membership_binary_brier":top3_brier,
    }
    d.update(cov)
    return d

MEAN_KEYS=[
"ordered_top3_log_loss","ordered_top3_log_loss_improvement_vs_uniform",
"ordered_top3_brier","ordered_top3_brier_skill_vs_uniform",
"exact_order_argmax_accuracy","top1_coverage","top3_coverage","top5_coverage",
"top10_coverage","top20_coverage","winner_log_loss",
"winner_log_loss_improvement_vs_uniform","winner_multiclass_brier",
"winner_brier_skill_vs_uniform","winner_top1_accuracy","top3_membership_binary_brier"]

def summarize(items):
    out={k+"_mean":sum(x[k] for x in items)/len(items) for k in MEAN_KEYS}
    out["observed_order_probability_rank_median"]=statistics.median(x["observed_order_probability_rank"] for x in items)
    out["race_count"]=len(items)
    return out

def percentile(xs,p):
    ys=sorted(xs)
    if not ys: return None
    pos=(len(ys)-1)*p
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return ys[lo]
    return ys[lo]*(hi-pos)+ys[hi]*(pos-lo)

def bootstrap(items, reps=10000, seed=20260914):
    rng=random.Random(seed); n=len(items)
    keys=["ordered_top3_log_loss_improvement_vs_uniform","winner_log_loss_improvement_vs_uniform",
          "exact_order_argmax_accuracy","winner_top1_accuracy"]
    vals={k:[] for k in keys}
    for _ in range(reps):
        sample=[items[rng.randrange(n)] for _ in range(n)]
        for k in keys:
            vals[k].append(sum(x[k] for x in sample)/n)
    return {k:{"p2_5":percentile(v,0.025),"p97_5":percentile(v,0.975)} for k,v in vals.items()}

def verdict(segB, bootB):
    oi=segB["ordered_top3_log_loss_improvement_vs_uniform_mean"]
    wi=segB["winner_log_loss_improvement_vs_uniform_mean"]
    lb=bootB["ordered_top3_log_loss_improvement_vs_uniform"]["p2_5"]
    if oi<=0:
        return "DIAGNOSTIC_FAIL"
    if wi>0 and lb>0:
        return "DIAGNOSTIC_SIGNAL_CONSISTENT"
    return "DIAGNOSTIC_SIGNAL_WEAK"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--predictions",required=True)
    ap.add_argument("--outcomes",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    pred=read_predictions(args.predictions)
    out=read_outcomes(args.outcomes)
    if len(pred)!=1500: raise ValueError(f"prediction race count {len(pred)} != 1500")
    if set(pred)!=set(out):
        miss=sorted(set(pred)-set(out))[:5]; extra=sorted(set(out)-set(pred))[:5]
        raise ValueError(f"race_id mismatch missing={miss} extra={extra}")
    byseg={"A":[],"B":[],"A+B":[]}
    for rid,p in pred.items():
        di=p["dev_index"]
        if not 1<=di<=1500: raise ValueError("prediction outside A+B")
        m=race_metrics(p,out[rid]); m["race_id"]=rid; m["dev_index"]=di
        seg="A" if di<=1000 else "B"
        byseg[seg].append(m); byseg["A+B"].append(m)
    summary={s:summarize(v) for s,v in byseg.items()}
    boot={s:bootstrap(v) for s,v in byseg.items()}
    result={
      "record":"KEIRIN_SW0_A_B_PREDICTIVE_EVALUATION_RESULT_v1",
      "evidence_class":"REAL_OUTCOME_DIAGNOSTIC_ONLY_NOT_UNTOUCHED_CONFIRMATORY_NOT_ECONOMIC",
      "segments":summary,
      "bootstrap_95pct":boot,
      "diagnostic_verdict":verdict(summary["B"],boot["B"]),
      "prohibitions_preserved":{
        "DEV2000_C_accessed":False,"ECON_HOLDOUT1000_accessed":False,
        "odds_price_payout_economics_used":False,"model_promotion":False,
        "runtime":"OFF","automatic_betting":False
      }
    }
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
