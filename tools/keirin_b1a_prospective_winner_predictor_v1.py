#!/usr/bin/env python3
"""Fail-closed prospective winner-probability adapter for frozen B1a_RECONSTITUTED_v1.

This module does not fit or tune anything. It applies only the exact frozen
winner layer recovered from MULTIVERSE_B1A_RECONSTITUTED_v1_FREEZE and rejects
outcome/result/payout-bearing payloads.

Expected PRE race JSON:
{
  "race_id": "...",
  "event_date": "YYYY-MM-DD",
  "venue": "...",
  "race_number": 1,
  "entrants": [
    {"car_no":1,"score":...,"win_rate":...,"quinella_rate":...,"trio_rate":...,
     "B":...,"S":...,"style":"逃|追|両","class":"SS|S1|S2|A1|A2|A3|L1","withdrawn":false}
  ]
}
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from typing import Any

MODEL_NAME="B1a_RECONSTITUTED_v1"
FREEZE_IMPLEMENTATION_SHA256="10e2ae81380c98df52845646cdc7a288f022ffac3a226004651e8abb80ade28b"
FREEZE_MODEL_SHA256="f5c0f1226a7552cb1f807e559f9409773b532934502f6a2ae5bb9b302a730481"
FREEZE_SPEC_SHA256="a5c896f6d56a55c0f10859b356b91a9b8756bdc90305da8c94b2a3a66c1490b3"
HISTORICAL_PREDICTION_LOCK_SHA256="772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
TEMPERATURE=1.15
STYLES=("逃","追","両")
CLASSES=("SS","S1","S2","A1","A2","A3","L1")
BASE_WEIGHTS={"score":0.55,"win_rate":0.18,"quinella_rate":0.12,"trio_rate":0.08,"B":0.04,"S":0.03}
BETA={
"class_A1":0.10862511799550383,"class_A2":-0.10862511799550574,"class_A3":4.991005121158697e-16,
"class_L1":-1.446593378458555e-16,"class_S1":-0.12658801568020364,"class_S2":-0.9504993423499002,
"class_SS":1.0770873580301035,"style_両":0.10822708520060681,"style_追":-0.3773237125550861,
"style_逃":0.26909662735448}
REQUIRED=("car_no","score","win_rate","quinella_rate","trio_rate","B","S","style","class")
FORBIDDEN_TOKENS=("result","payout","refund","finish","winner","着順","払戻","確定")

class FailClosed(ValueError): pass

def _forbidden_key(k:str)->bool:
    x=str(k).lower()
    return any(t.lower() in x for t in FORBIDDEN_TOKENS)

def reject_outcome_fields(obj:Any,path:str="$')->None:
    if isinstance(obj,dict):
        for k,v in obj.items():
            if _forbidden_key(k):
                raise FailClosed(f"outcome_or_settlement_field_forbidden:{path}.{k}")
            reject_outcome_fields(v,f"{path}.{k}")
    elif isinstance(obj,list):
        for i,v in enumerate(obj): reject_outcome_fields(v,f"{path}[{i}]")

def _mean(xs:list[float])->float: return sum(xs)/len(xs)
def _std_pop(xs:list[float],mean:float)->float:
    s=math.sqrt(sum((x-mean)**2 for x in xs)/len(xs))
    return s if s != 0.0 else 1.0

def predict(race:dict[str,Any])->dict[str,Any]:
    reject_outcome_fields(race)
    for k in ("race_id","event_date","venue","race_number","entrants"):
        if k not in race: raise FailClosed(f"missing:{k}")
    if not isinstance(race["entrants"],list) or len(race["entrants"])<2:
        raise FailClosed("entrants_invalid")
    ents=[e for e in race["entrants"] if not bool(e.get("withdrawn",False))]
    if len(ents)<2: raise FailClosed("active_entrants_lt_2")
    cars=[]
    vals={k:[] for k in BASE_WEIGHTS}
    for i,e in enumerate(ents):
        miss=[k for k in REQUIRED if k not in e]
        if miss: raise FailClosed(f"entrant_{i}_missing="+",".join(miss))
        car=int(e["car_no"])
        if car<=0 or car in cars: raise FailClosed("car_no_invalid_or_duplicate")
        cars.append(car)
        style=str(e["style"]).strip(); cls=str(e["class"]).strip()
        if style not in STYLES or cls not in CLASSES: raise FailClosed(f"unknown_category:{style}/{cls}")
        for k in vals:
            x=float(e[k])
            if not math.isfinite(x): raise FailClosed(f"nonfinite:{car}:{k}")
            vals[k].append(x)
    z={}
    for k,xs in vals.items():
        m=_mean(xs); sd=_std_pop(xs,m); z[k]=[(x-m)/sd for x in xs]
    logits=[]
    for i,e in enumerate(ents):
        base=sum(BASE_WEIGHTS[k]*z[k][i] for k in BASE_WEIGHTS)/TEMPERATURE
        residual=BETA["style_"+str(e["style"]).strip()]+BETA["class_"+str(e["class"]).strip()]
        logits.append(base+residual)
    mx=max(logits); ex=[math.exp(x-mx) for x in logits]; den=sum(ex)
    probs=[x/den for x in ex]
    if not math.isfinite(den) or den<=0 or abs(sum(probs)-1.0)>1e-12 or any(p<=0 for p in probs):
        raise FailClosed("probability_invariant_failed")
    return {
        "record":"KEIRIN_B1A_PROSPECTIVE_WINNER_PROBABILITY_v1",
        "status":"PASS_FROZEN_B1A_NO_RETUNE",
        "race_id":str(race["race_id"]),
        "event_date":str(race["event_date"]),
        "venue":str(race["venue"]),
        "race_number":int(race["race_number"]),
        "model_name":MODEL_NAME,
        "probabilities":[{"car_no":c,"b1a_reconstituted_v1_win_prob":p} for c,p in zip(cars,probs)],
        "frozen_lineage":{
            "implementation_sha256":FREEZE_IMPLEMENTATION_SHA256,
            "model_sha256":FREEZE_MODEL_SHA256,
            "spec_sha256":FREEZE_SPEC_SHA256,
            "historical_prediction_lock_sha256":HISTORICAL_PREDICTION_LOCK_SHA256,
        },
        "retune":False,"result_access":False,"payout_access":False
    }

def selftest()->dict[str,Any]:
    base={"race_id":"T","event_date":"2026-09-12","venue":"松山","race_number":1,"entrants":[
        {"car_no":1,"score":90,"win_rate":0.2,"quinella_rate":0.4,"trio_rate":0.5,"B":2,"S":3,"style":"逃","class":"A3"},
        {"car_no":2,"score":85,"win_rate":0.1,"quinella_rate":0.3,"trio_rate":0.4,"B":1,"S":2,"style":"追","class":"A3"},
        {"car_no":3,"score":80,"win_rate":0.05,"quinella_rate":0.2,"trio_rate":0.3,"B":0,"S":1,"style":"両","class":"A3"}]}
    tests={}
    o=predict(base); tests["valid"]=o["status"].startswith("PASS") and abs(sum(x["b1a_reconstituted_v1_win_prob"] for x in o["probabilities"])-1)<1e-12
    bad=json.loads(json.dumps(base)); bad["result"]={"winner":1}
    try: predict(bad); tests["outcome_reject"]=False
    except FailClosed: tests["outcome_reject"]=True
    bad=json.loads(json.dumps(base)); bad["entrants"][0]["class"]="X"
    try: predict(bad); tests["unknown_class_reject"]=False
    except FailClosed: tests["unknown_class_reject"]=True
    bad=json.loads(json.dumps(base)); bad["entrants"][1]["car_no"]=1
    try: predict(bad); tests["duplicate_car_reject"]=False
    except FailClosed: tests["duplicate_car_reject"]=True
    return {"record":"KEIRIN_B1A_PROSPECTIVE_WINNER_PREDICTOR_SELFTEST_v1","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"test_count":len(tests),"network_access":False,"retune":False}

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest")
    p=sub.add_parser("predict"); p.add_argument("--input",required=True); p.add_argument("--output")
    a=ap.parse_args()
    if a.cmd=="selftest": out=selftest()
    else:
        try: out=predict(json.loads(Path(a.input).read_text(encoding="utf-8")))
        except (OSError,json.JSONDecodeError,ValueError) as exc:
            print(json.dumps({"status":"FAIL_CLOSED","reason":str(exc)},ensure_ascii=False,sort_keys=True)); return 3
        if a.output: Path(a.output).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if out["status"].startswith("PASS") else 2
if __name__=="__main__": raise SystemExit(main())
