from __future__ import annotations
import json, hashlib, math
from collections import defaultdict

HAIRCUTS=(1.00,0.95,0.90,0.85)
DECISION_HAIRCUT=0.90
UNCERTAINTY_LIMIT=0.20
EXCLUSION_RATE_LIMIT=0.15

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def effective_odds(proxy_odds:float,haircut:float)->float:
    x=float(proxy_odds); h=float(haircut)
    if not math.isfinite(x) or x<1.0: raise ValueError("proxy_odds must be finite and >=1.00")
    if h not in HAIRCUTS: raise ValueError("unfrozen haircut")
    return max(1.00,x*h)

def exclusion_fail_closed(total_frozen_races:int,excluded_races:int):
    if total_frozen_races<=0: raise ValueError("empty universe")
    rate=excluded_races/total_frozen_races
    return {"rate":rate,"forced_no_signal":rate>EXCLUSION_RATE_LIMIT}

def blocked_date_folds(rows,k=5):
    if k!=5: raise ValueError("frozen k=5")
    bydate=defaultdict(list)
    for r in rows: bydate[str(r["race_date"])].append(str(r["race_id"]))
    dates=sorted(bydate)
    if len(dates)<k: raise ValueError("fewer unique dates than folds")
    total=sum(len(bydate[d]) for d in dates)
    targets=[total*i/k for i in range(1,k)]
    fold=1; cumulative=0; ti=0; mapping={}
    for d in dates:
        for rid in bydate[d]: mapping[rid]=fold
        cumulative+=len(bydate[d])
        if fold<k and ti<len(targets) and cumulative>=targets[ti]:
            fold+=1; ti+=1
    datefolds=defaultdict(set)
    for d in dates:
        for rid in bydate[d]: datefolds[d].add(mapping[rid])
    if any(len(x)!=1 for x in datefolds.values()): raise AssertionError("same date crossed folds")
    if sorted(set(mapping.values()))!=[1,2,3,4,5]: raise ValueError("not all 5 folds populated")
    return mapping

def commitment(payload):
    return {"commitment":payload,"commitment_sha256":sha256_bytes(canonical(payload).encode("utf-8"))}
