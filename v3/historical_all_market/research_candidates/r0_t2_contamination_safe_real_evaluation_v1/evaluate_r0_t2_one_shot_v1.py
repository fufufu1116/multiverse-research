#!/usr/bin/env python3
import argparse, hashlib, json, math, random, statistics
from pathlib import Path

EPS=1e-15
RACE_BOOTSTRAP_SEED=20260918
MEETING_BOOTSTRAP_SEED=20260919
BOOTSTRAP_REPS=10000
ECE_BINS=10
MIN_RACES=24
MIN_MEETINGS=3
MAX_ECE10=0.15
RESULT_KEYS={"race_id","ordered_top3_car_no"}

def canonical_sha(obj):
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(raw).hexdigest()

def uniform_ordered_top3_nll(n):
    return -math.log((1/n)*(1/(n-1))*(1/(n-2)))

def sequential_order_prob(lock, order):
    probs={int(x["car_no"]):float(x["p"]) for x in lock["p_win"]}
    rem=set(probs); out=1.0
    for car in order:
        denom=sum(probs[c] for c in rem)
        if car not in rem or denom<=0: raise SystemExit("FAIL_CLOSED_BAD_ORDER_OR_DENOM")
        out*=probs[car]/denom; rem.remove(car)
    return out

def ece(pairs,bins=ECE_BINS):
    n=len(pairs)
    if n==0: raise SystemExit("FAIL_CLOSED_EMPTY_CALIBRATION")
    total=0.0
    for b in range(bins):
        lo=b/bins; hi=(b+1)/bins
        bucket=[x for x in pairs if x[0]>=lo and (x[0]<hi or (b==bins-1 and x[0]<=hi))]
        if bucket:
            total+=len(bucket)/n*abs(sum(c for c,_ in bucket)/len(bucket)-sum(y for _,y in bucket)/len(bucket))
    return total

def percentile(xs,q):
    ys=sorted(xs); pos=(len(ys)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    return ys[lo] if lo==hi else ys[lo]*(hi-pos)+ys[hi]*(pos-lo)

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

def read_unique_jsonl(path,key):
    out={}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        row=json.loads(line); k=str(row[key])
        if k in out: raise SystemExit(f"FAIL_CLOSED_DUPLICATE_ID:{k}")
        out[k]=row
    return out

def validate_lock(lock,expected_assignment):
    if lock.get("assignment_id")!=expected_assignment: raise SystemExit("FAIL_CLOSED_ASSIGNMENT_ID")
    n=len(lock.get("entrants",[]))
    if n not in range(5,10): raise SystemExit("FAIL_CLOSED_ENTRANT_COUNT")
    cars=[int(e["car_no"]) for e in lock["entrants"]]
    if len(set(cars))!=n: raise SystemExit("FAIL_CLOSED_DUPLICATE_CAR")
    pitems=lock.get("p_win",[])
    if len(pitems)!=n or {int(x["car_no"]) for x in pitems}!=set(cars): raise SystemExit("FAIL_CLOSED_PROBABILITY_CARS")
    ps=[float(x["p"]) for x in pitems]
    if any((not math.isfinite(p) or p<0) for p in ps) or abs(sum(ps)-1.0)>1e-12: raise SystemExit("FAIL_CLOSED_PROBABILITY_SANITY")
    stored=lock.get("lock_sha256"); base=dict(lock); base.pop("lock_sha256",None)
    if stored!=canonical_sha(base): raise SystemExit("FAIL_CLOSED_LOCK_HASH")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--locks",required=True); ap.add_argument("--results",required=True)
    ap.add_argument("--out",required=True); ap.add_argument("--assignment-id",required=True)
    args=ap.parse_args()
    locks=read_unique_jsonl(args.locks,"race_id"); results=read_unique_jsonl(args.results,"race_id")
    if set(locks)!=set(results): raise SystemExit("FAIL_CLOSED_RACE_SET_MISMATCH")
    if len(locks)<MIN_RACES: raise SystemExit("FAIL_CLOSED_MIN_RACES")
    if len({str(x["meeting_id"]) for x in locks.values()})<MIN_MEETINGS: raise SystemExit("FAIL_CLOSED_MIN_MEETINGS")
    scored=[]; calib=[]
    for rid in sorted(locks):
        l=locks[rid]; r=results[rid]; validate_lock(l,args.assignment_id)
        if set(r)!=RESULT_KEYS: raise SystemExit("FAIL_CLOSED_RESULT_SCHEMA")
        order=[int(x) for x in r["ordered_top3_car_no"]]
        if len(order)!=3 or len(set(order))!=3: raise SystemExit("FAIL_CLOSED_RESULT_ORDER_SHAPE")
        n=len(l["entrants"]); pmap={int(x["car_no"]):float(x["p"]) for x in l["p_win"]}
        if not set(order).issubset(pmap): raise SystemExit("FAIL_CLOSED_RESULT_CAR_NOT_IN_LOCK")
        pord=sequential_order_prob(l,order); onll=-math.log(max(EPS,pord)); unll=uniform_ordered_top3_nll(n)
        winner=order[0]; pw=pmap[winner]; wll=-math.log(max(EPS,pw)); uwll=math.log(n)
        wb=sum((p-(1.0 if c==winner else 0.0))**2 for c,p in pmap.items()); uwb=1-1/n
        pred=max(pmap,key=lambda c:(pmap[c],-c)); pred3=set(sorted(pmap,key=lambda c:(pmap[c],-c),reverse=True)[:3])
        conf=pmap[pred]; correct=1.0 if pred==winner else 0.0; calib.append((conf,correct))
        scored.append({"meeting_id":l["meeting_id"],"race_id":rid,"primary_improvement":unll-onll,
                       "winner_ll_improvement":uwll-wll,"winner_brier_improvement":uwb-wb,
                       "top1":correct,"top3_containment":1.0 if set(order)==pred3 else 0.0})
    prim=[x["primary_improvement"] for x in scored]
    race_bs=bootstrap_mean(prim,BOOTSTRAP_REPS,RACE_BOOTSTRAP_SEED); meet_bs=meeting_bootstrap(scored,BOOTSTRAP_REPS,MEETING_BOOTSTRAP_SEED)
    metrics={"n_races":len(scored),"n_meetings":len(set(x["meeting_id"] for x in scored)),
        "mean_ordered_top3_nll_improvement_vs_sequential_uniform":statistics.fmean(prim),
        "race_bootstrap_lower95":percentile(race_bs,0.025),"meeting_bootstrap_lower95":percentile(meet_bs,0.025),
        "winner_logloss_improvement_vs_uniform":statistics.fmean(x["winner_ll_improvement"] for x in scored),
        "winner_brier_improvement_vs_uniform":statistics.fmean(x["winner_brier_improvement"] for x in scored),
        "top1_accuracy":statistics.fmean(x["top1"] for x in scored),
        "unordered_top3_containment":statistics.fmean(x["top3_containment"] for x in scored),"toplabel_ece10":ece(calib)}
    passed=(metrics["race_bootstrap_lower95"]>0 and metrics["meeting_bootstrap_lower95"]>0
            and metrics["winner_logloss_improvement_vs_uniform"]>=0 and metrics["winner_brier_improvement_vs_uniform"]>=0
            and math.isfinite(metrics["toplabel_ece10"]) and metrics["toplabel_ece10"]<=MAX_ECE10)
    out={"record":"R0_T2_ONE_SHOT_REAL_EVALUATION_RESULT_V1","assignment_id":args.assignment_id,"metrics":metrics,
         "verdict":"PASS_PREREGISTERED_SIGNAL_GATE" if passed else "FAIL_PREREGISTERED_SIGNAL_GATE",
         "claim_boundary":"INDEPENDENT_FROZEN_EVIDENCE_SET_ONLY_NO_PROMOTION_BY_ITSELF"}
    Path(args.out).write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
