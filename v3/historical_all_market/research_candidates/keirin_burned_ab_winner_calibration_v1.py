#!/usr/bin/env python3
"""Fail-closed burned A+B winner-probability calibration for frozen Candidate A vs B1a.

This tool is intentionally limited to already-burned DEV2000 Segments A/B. It never accepts
Segment C or ECON_HOLDOUT1000 inputs, never refits a model, and verifies frozen SHA-256
bindings before reading settlement content.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from collections import defaultdict
from pathlib import Path

PRED_SHA="772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
SETT_A_SHA="436846591b082689cf29687b2e63e82b0f12b47b4fa70a596d90b00978079cdd"
SETT_B_SHA="95096fac61c320484d6ab0456971a3e7debdf311498b00d6390658c072c71a72"
MODELS=("candidate_a_win_prob","b1a_reconstituted_v1_win_prob")

class FailClosed(RuntimeError): pass

def sha256_file(p: Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def load_jsonl(p: Path):
    out=[]
    with p.open("r",encoding="utf-8") as f:
        for i,line in enumerate(f,1):
            if line.strip():
                x=json.loads(line)
                if not isinstance(x,dict): raise FailClosed(f"{p.name}:{i}: non-object")
                out.append(x)
    return out

def winner_from_settlement(r: dict)->int:
    cats=r.get("settlements_yen_per_100")
    if not isinstance(cats,dict): raise FailClosed(f"{r.get('race_id')}: settlements missing")
    winners=[]
    for market in ("3rentan","2shatan"):
        m=cats.get(market,{})
        if isinstance(m,dict):
            for ticket,pay in m.items():
                if int(pay)>0:
                    try: winners.append(int(str(ticket).split("-")[0]))
                    except Exception as e: raise FailClosed(f"{r.get('race_id')}: bad ordered ticket {ticket}") from e
    if not winners: raise FailClosed(f"{r.get('race_id')}: no ordered-market winning ticket")
    if len(set(winners))!=1: raise FailClosed(f"{r.get('race_id')}: inconsistent winner evidence {winners}")
    return winners[0]

def load_labels(a: Path,b: Path):
    if sha256_file(a)!=SETT_A_SHA: raise FailClosed("Settlement A SHA drift")
    if sha256_file(b)!=SETT_B_SHA: raise FailClosed("Settlement B SHA drift")
    labels={}; seg={}
    for p,expected,n in ((a,"A",1000),(b,"B",500)):
        rows=load_jsonl(p)
        if len(rows)!=n: raise FailClosed(f"Segment {expected} rows={len(rows)} expected={n}")
        for r in rows:
            if r.get("segment")!=expected: raise FailClosed(f"segment drift: {r.get('segment')}")
            rid=str(r["race_id"])
            if rid in labels: raise FailClosed(f"duplicate race {rid}")
            labels[rid]=winner_from_settlement(r); seg[rid]=expected
    if len(labels)!=1500: raise FailClosed(f"label count={len(labels)}")
    return labels,seg

def load_pred(p: Path):
    if sha256_file(p)!=PRED_SHA: raise FailClosed("Prediction SHA drift")
    by=defaultdict(dict); n=0
    with p.open("r",encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            rid=str(r["race_id"]); car=int(r["car_no"]); n+=1
            by[rid][car]={m:float(r[m]) for m in MODELS}
    if n!=14255 or len(by)!=2000: raise FailClosed(f"prediction cardinality rows={n} races={len(by)}")
    for rid,cars in by.items():
        for m in MODELS:
            s=sum(v[m] for v in cars.values())
            if abs(s-1.0)>1e-8: raise FailClosed(f"{rid}/{m}: probability sum {s}")
    return dict(by)

def ece_top1(items,bins=10):
    acc=0.0; n=len(items)
    for b in range(bins):
        lo=b/bins; hi=(b+1)/bins
        xs=[x for x in items if (lo<=x[0]<(hi if b<bins-1 else hi+1e-15))]
        if xs:
            conf=sum(x[0] for x in xs)/len(xs); hit=sum(x[1] for x in xs)/len(xs)
            acc += len(xs)/n*abs(conf-hit)
    return acc

def metrics(pred,labels,rids,model):
    tops=[]; brier=[]; logloss=[]
    for rid in rids:
        cars=pred[rid]; w=labels[rid]
        if w not in cars: raise FailClosed(f"{rid}: winner {w} absent from prediction cars")
        topcar=max(cars,key=lambda c:(cars[c][model],-c)); conf=cars[topcar][model]; hit=int(topcar==w)
        tops.append((conf,hit))
        brier.append(sum((v[model]-(1.0 if c==w else 0.0))**2 for c,v in cars.items()))
        logloss.append(-math.log(max(cars[w][model],1e-15)))
    return {"n":len(rids),"top1_hit_rate":sum(h for _,h in tops)/len(tops),"mean_top1_probability":sum(c for c,_ in tops)/len(tops),"top1_ece_10bin":ece_top1(tops),"multiclass_brier":sum(brier)/len(brier),"winner_log_loss":sum(logloss)/len(logloss)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--predictions",required=True); ap.add_argument("--settlement-a",required=True); ap.add_argument("--settlement-b",required=True); ap.add_argument("--output",required=True)
    a=ap.parse_args(); pred=load_pred(Path(a.predictions)); labels,seg=load_labels(Path(a.settlement_a),Path(a.settlement_b))
    rids=[r for r in labels if r in pred]
    if len(rids)!=1500: raise FailClosed(f"prediction/label join races={len(rids)}")
    out={"record":"KEIRIN_BURNED_AB_WINNER_CALIBRATION_v1","status":"PASS_FIXED_MODEL_DIAGNOSTIC_ONLY","retuned":False,"segment_c_opened":False,"ECON_HOLDOUT1000":"SEALED","bindings":{"prediction_sha256":PRED_SHA,"settlement_a_sha256":SETT_A_SHA,"settlement_b_sha256":SETT_B_SHA},"metrics":{}}
    for scope,scope_rids in (("A",[r for r in rids if seg[r]=="A"]),("B",[r for r in rids if seg[r]=="B"]),("AB",rids)):
        out["metrics"][scope]={m:metrics(pred,labels,scope_rids,m) for m in MODELS}
    changed=[]
    for rid in rids:
        ca=max(pred[rid],key=lambda c:(pred[rid][c][MODELS[0]],-c)); cb=max(pred[rid],key=lambda c:(pred[rid][c][MODELS[1]],-c))
        if ca!=cb: changed.append(rid)
    out["top1_changed_subset"]={"n":len(changed),"candidate_a_hit_rate":sum(max(pred[r],key=lambda c:(pred[r][c][MODELS[0]],-c))==labels[r] for r in changed)/len(changed) if changed else None,"b1a_hit_rate":sum(max(pred[r],key=lambda c:(pred[r][c][MODELS[1]],-c))==labels[r] for r in changed)/len(changed) if changed else None}
    op=Path(a.output); op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"output":str(op),"sha256":sha256_file(op)},ensure_ascii=False))
if __name__=="__main__": main()
