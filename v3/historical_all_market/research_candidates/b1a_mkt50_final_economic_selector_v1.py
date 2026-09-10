#!/usr/bin/env python3
"""Frozen final economic selector for B1a_MKT50_v1.

Pre-holdout rule:
- race competition_score >= 0.40
- markets: 3rentan / 2shatan only
- q = fixed B1a_MKT50_v1 ticket probability
- eligible if q*odds-1 >= 0 and q/market_shape >= 1
- SINGLE: choose exactly the globally highest-ranked eligible ticket
- stake: frozen FK10_R2 semantics, 100-yen floor
"""
from __future__ import annotations
import math
from typing import Mapping
from b1a_mkt50_v1 import market_shape_from_decimal_odds, transform_race_market, FailClosed

COMPETITION_THRESHOLD=0.40
SUPPORTED_MARKETS=("3rentan","2shatan")
START_BANKROLL=100000
KELLY_MULT=0.10
TICKET_CAP=0.0025
RACE_CAP=0.02
STAKE_UNIT=100

def _clean_model(d: Mapping[str,float]) -> dict[str,float]:
    if not isinstance(d,Mapping) or not d: raise FailClosed("empty model distribution")
    out={str(k):float(v) for k,v in d.items()}
    if any((not math.isfinite(v) or v<0) for v in out.values()): raise FailClosed("invalid model probability")
    z=sum(out.values())
    if z<=0 or not math.isfinite(z): raise FailClosed("invalid model total")
    return {k:v/z for k,v in out.items()}

def select_single(race_markets: Mapping[str,dict], competition_score: float, bankroll: int):
    score=float(competition_score)
    if not math.isfinite(score): raise FailClosed("invalid competition score")
    if bankroll<0: raise FailClosed("negative bankroll")
    if score < COMPETITION_THRESHOLD or bankroll < STAKE_UNIT:
        return None
    pool=[]
    for market in SUPPORTED_MARKETS:
        row=race_markets.get(market)
        if row is None: continue
        model=_clean_model(row.get("b1a_ticket_probability") or {})
        odds={str(k):float(v) for k,v in (row.get("decimal_odds") or {}).items()}
        market_shape=market_shape_from_decimal_odds(odds)
        if set(model)!=set(market_shape): raise FailClosed(f"{market}: ticket universe mismatch")
        q=transform_race_market(market,model,market_shape)
        for ticket,p in q.items():
            o=odds[ticket]
            ev=o*p-1.0
            ratio=p/market_shape[ticket]
            if ev>=0.0 and ratio>=1.0:
                pool.append((market,ticket,p,ev,ratio,o))
    if not pool: return None
    pool.sort(key=lambda x:(-x[3],-x[4],-x[2],x[0],x[1]))
    market,ticket,p,ev,ratio,o=pool[0]
    kelly=max(0.0,(o*p-1.0)/(o-1.0)) if o>1.0 else 0.0
    frac=min(TICKET_CAP,max(0.0,KELLY_MULT*kelly),RACE_CAP)
    stake=int(math.floor((bankroll*frac)/STAKE_UNIT + 1e-12))*STAKE_UNIT
    if stake < STAKE_UNIT: return None
    if stake > bankroll: raise FailClosed("stake exceeds bankroll")
    return {"market":market,"ticket":ticket,"q":p,"odds":o,"raw_ev":ev,"shape_edge_ratio":ratio,"stake_yen":stake}

if __name__=="__main__":
    raise SystemExit("library module; use final holdout evaluator")
