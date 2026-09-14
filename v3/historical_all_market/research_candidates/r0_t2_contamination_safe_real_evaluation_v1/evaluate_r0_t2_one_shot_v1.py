#!/usr/bin/env python3
import argparse, json, math, random, statistics
from pathlib import Path

EPS=1e-15
RACE_BOOTSTRAP_SEED=20260918
MEETING_BOOTSTRAP_SEED=20260919
BOOTSTRAP_REPS=10000
ECE_BINS=10

def uniform_ordered_top3_nll(n):
    return -math.log((1/n)*(1/(n-1))*(1/(n-2)))

def sequential_order_prob(lock, order):
    probs={int(x["car_no"]):float(x["p"]) for x in lock["p_win"]}
    rem=set(probs)
    out=1.0
    for car in order[:3]:
        denom=sum(probs[c] for c in rem)
        if car not in rem or denom<=0: return 0.0
        out*=probs[car]/denom
        rem.remove(car)
    return out

def ece(pairs,bins=ECE_BINS):
    n=len(pairs)
    if n==0: return float("nan")
    total=0.0
    for b in range(bins):
        lo=b/bins; hi=(b+1)/bins
        bucket=[x for x in pairs if x[0]>=lo and (x[0]<hi or (b==bins-1 and x[0]<=hi))]
        if bucket:
            total+=len(bucket)/n*abs(sum(c for c,_ in bucket)/len(bucket)-sum(y for _,y in bucket)/len(bucket))
    return total

def percentile(xs,q):
    ys=sorted(xs)
    if not ys: return float("nan")
    pos=(len(ys)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return ys[lo]
    return ys[lo]*(hi-pos)+ys[hi]*(pos-lo)

def bootstrap_mean(values,reps,seed):
    rng=random.Random(seed); n=len(values)
    return [sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(reps)]

def meeting_bootstrap(rows,reps,seed):
    by={}
    for r in rows: by.setdefault(r["meeting_id"],[]).append(r["primary_improvement"])
    mids=sorted(by); rng=random.Random(seed); out=[]
    for _ in range(reps):
        sampled=[mids[rng.randrange(len(mids))] for _ in mids]
        vals=[v for m in sampled for v in by[m]]
        out.append(sum(vals)/len(vals))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--locks",required=True)
    ap.add_argument("--results",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    locks={r["race_id"]:r for r in (json.loads(x) for x in Path(args.locks).read_text(encoding="utf-8").splitlines() if x.strip())}
    results={r["race_id"]:r for r in (json.loads(x) for x in Path(args.results).read_text(encoding="utf-8").splitlines() if x.strip())}
    if set(locks)!=set(results): raise SystemExit("FAIL_CLOSED_RACE_SET_MISMATCH")
    scored=[]; calib=[]
    for rid in sorted(locks):
        l=locks[rid]; r=results[rid]
        order=[int(x) for x in r["ordered_top3_car_no"]]
        n=len(l["entrants"])
        pord=sequential_order_prob(l,order)
        onll=-math.log(max(EPS,pord)); unll=uniform_ordered_top3_nll(n)
        pmap={int(x["car_no"]):float(x["p"]) for x in l["p_win"]}
        winner=order[0]; pw=pmap[winner]
        wll=-math.log(max(EPS,pw)); uwll=math.log(n)
        wb=sum((p-(1.0 if c==winner else 0.0))**2 for c,p in pmap.items()); uwb=1-1/n
        pred=max(pmap,key=lambda c:(pmap[c],-c))
        pred3=set(sorted(pmap,key=lambda c:(pmap[c],-c),reverse=True)[:3])
        conf=pmap[pred]; correct=1.0 if pred==winner else 0.0; calib.append((conf,correct))
        scored.append({"meeting_id":l["meeting_id"],"race_id":rid,"primary_improvement":unll-onll,
                       "winner_ll_improvement":uwll-wll,"winner_brier_improvement":uwb-wb,
                       "top1":correct,"top3_containment":1.0 if set(order[:3])==pred3 else 0.0})
    prim=[x["primary_improvement"] for x in scored]
    race_bs=bootstrap_mean(prim,BOOTSTRAP_REPS,RACE_BOOTSTRAP_SEED)
    meet_bs=meeting_bootstrap(scored,BOOTSTRAP_REPS,MEETING_BOOTSTRAP_SEED)
    metrics={
        "n_races":len(scored),"n_meetings":len(set(x["meeting_id"] for x in scored)),
        "mean_ordered_top3_nll_improvement_vs_sequential_uniform":statistics.fmean(prim),
        "race_bootstrap_lower95":percentile(race_bs,0.025),
        "meeting_bootstrap_lower95":percentile(meet_bs,0.025),
        "winner_logloss_improvement_vs_uniform":statistics.fmean(x["winner_ll_improvement"] for x in scored),
        "winner_brier_improvement_vs_uniform":statistics.fmean(x["winner_brier_improvement"] for x in scored),
        "top1_accuracy":statistics.fmean(x["top1"] for x in scored),
        "unordered_top3_containment":statistics.fmean(x["top3_containment"] for x in scored),
        "toplabel_ece10":ece(calib)
    }
    passed=(metrics["n_races"]>=24 and metrics["n_meetings"]>=3 and metrics["race_bootstrap_lower95"]>0
            and metrics["meeting_bootstrap_lower95"]>0
            and metrics["winner_logloss_improvement_vs_uniform"]>=0
            and metrics["winner_brier_improvement_vs_uniform"]>=0
            and math.isfinite(metrics["toplabel_ece10"]) and metrics["toplabel_ece10"]<=0.15)
    out={"record":"R0_T2_ONE_SHOT_REAL_EVALUATION_RESULT_V1","metrics":metrics,
         "verdict":"PASS_PREREGISTERED_SIGNAL_GATE" if passed else "FAIL_PREREGISTERED_SIGNAL_GATE",
         "claim_boundary":"INDEPENDENT_FROZEN_EVIDENCE_SET_ONLY_NO_PROMOTION_BY_ITSELF"}
    Path(args.out).write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":
    main()
