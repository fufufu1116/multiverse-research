#!/usr/bin/env python3
"""Burned-development simulator for 3rentan fixed-first / narrow-second / wide-third.

Research-only. Requires the same burned A+B fixtures used by the existing
Keirin buy-strategy simulator. Segment C and ECON_HOLDOUT are intentionally
unsupported.
"""
from __future__ import annotations
import argparse, collections, itertools, json, math, datetime
from pathlib import Path

def iter_jsonl(path):
    with open(path,"rb") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def by_race(path):
    return {x["race_id"]:x for x in iter_jsonl(path)}

class Fixture:
    def __init__(self,args):
        self.price=by_race(args.price)
        self.result=by_race(args.result)
        self.settle={}
        for x in itertools.chain(iter_jsonl(args.settlement_a),iter_jsonl(args.settlement_b)):
            self.settle[int(x["dev_index"])]=x
        self.prob=collections.defaultdict(dict)
        for x in iter_jsonl(args.probability):
            self.prob[x["probability_source"]][x["race_id"]]=x
        if set(self.settle)!=set(range(1,1501)):
            raise ValueError("A+B fixture must be dev_index 1..1500 exactly; C is intentionally unsupported")
        for src in ("candidate_a","b1a_reconstituted_v1"):
            if src not in self.prob:
                raise ValueError(f"required probability source missing: {src}")

    def cons_first(self,idx):
        rid=self.settle[idx]["race_id"]
        marg=[]
        for src in ("candidate_a","b1a_reconstituted_v1"):
            d=collections.defaultdict(float)
            for t,p in self.prob[src][rid]["ticket_probabilities"]["2shatan"].items():
                i,_=map(int,t.split("-"))
                d[i]+=float(p)
            marg.append(d)
        cars=sorted(set(marg[0])|set(marg[1]))
        score={c:min(marg[0].get(c,0.0),marg[1].get(c,0.0)) for c in cars}
        topa=max(marg[0],key=marg[0].get)
        topb=max(marg[1],key=marg[1].get)
        rank=[c for c,_ in sorted(score.items(),key=lambda kv:(-kv[1],kv[0]))]
        return topa==topb,rank,score

    def pmin(self,rid,ticket):
        return min(
            float(self.prob["candidate_a"][rid]["ticket_probabilities"]["3rentan"][ticket]),
            float(self.prob["b1a_reconstituted_v1"][rid]["ticket_probabilities"]["3rentan"][ticket]),
        )

    def decimal_odds(self,rid,ticket):
        market=self.price[rid].get("market_prices",self.price[rid].get("prices",self.price[rid]))
        raw=market.get("3rentan",{})[ticket]
        if isinstance(raw,dict):
            for k in ("decimal_odds","odds","value"):
                if k in raw:
                    raw=raw[k]; break
        x=float(raw)
        if not math.isfinite(x) or x<=0:
            raise ValueError("invalid 3rentan decimal odds")
        return x

    def payout(self,rid,ticket):
        x=next(v for v in self.settle.values() if v["race_id"]==rid)
        return float(x["settlements_yen_per_100"].get("3rentan",{}).get(ticket,0.0))

def select(fx,idx,second_group_size,third_pool_size,confidence):
    rid=fx.settle[idx]["race_id"]
    agree,rank,score=fx.cons_first(idx)
    if not agree or score[rank[0]] < confidence:
        return []
    first=rank[0]
    others=rank[1:]
    if not (1 <= second_group_size <= len(others)):
        raise ValueError("invalid second_group_size")
    if not (2 <= third_pool_size <= len(others)):
        raise ValueError("invalid third_pool_size")
    if second_group_size > third_pool_size:
        raise ValueError("second_group_size cannot exceed third_pool_size")
    seconds=others[:second_group_size]
    thirds=others[:third_pool_size]
    return [f"{first}-{s}-{t}" for s in seconds for t in thirds if t!=s]

def guarded_portfolio_ev(fx,rid,tickets):
    if not tickets:
        return None
    return sum(fx.pmin(rid,t)*fx.decimal_odds(rid,t) for t in tickets)/len(tickets)-1.0

def evaluate(fx,lo,hi,second_group_size,third_pool_size,confidence,ev_min=None):
    stake=ret=bets=hits=tickets_n=0
    bank=100000.0; peak=bank; maxdd=0.0; largest=0.0
    weekly=collections.defaultdict(lambda:[0.0,0.0])
    for idx in range(lo,hi+1):
        rid=fx.settle[idx]["race_id"]
        sels=select(fx,idx,second_group_size,third_pool_size,confidence)
        if not sels:
            continue
        gev=guarded_portfolio_ev(fx,rid,sels)
        if ev_min is not None and gev < ev_min:
            continue
        s=100*len(sels)
        r=sum(fx.payout(rid,t) for t in sels)
        stake+=s; ret+=r; bets+=1; tickets_n+=len(sels); hits+=r>0; largest=max(largest,r)
        bank+=r-s; peak=max(peak,bank); maxdd=max(maxdd,(peak-bank)/peak)
        y,m,d=map(int,fx.result[rid]["race_date"].split("-"))
        iso=datetime.date(y,m,d).isocalendar(); key=f"{iso.year}-W{iso.week:02d}"
        weekly[key][0]+=s; weekly[key][1]+=r
    return {
        "bet_races":bets,"tickets":tickets_n,"stake":stake,"return":ret,
        "roi":ret/stake-1 if stake else None,"hit_rate":hits/bets if bets else None,
        "average_points_per_bet":tickets_n/bets if bets else None,
        "ending_bankroll":bank,"max_drawdown":maxdd,
        "largest_single_race_return_share":largest/ret if ret else None,
        "weekly_roi":{k:(v[1]/v[0]-1 if v[0] else None) for k,v in sorted(weekly.items())},
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--price",required=True)
    ap.add_argument("--probability",required=True)
    ap.add_argument("--result",required=True)
    ap.add_argument("--settlement-a",required=True)
    ap.add_argument("--settlement-b",required=True)
    ap.add_argument("--out")
    args=ap.parse_args()
    fx=Fixture(args)
    specs=[]
    for second in (1,2):
        for third in (3,4,5,6):
            if second<=third:
                for ev in (None,0.10):
                    specs.append((second,third,0.40,ev))
    rows=[]
    for second,third,confidence,ev in specs:
        rows.append({
            "rule":{
                "market":"3rentan",
                "first":"consensus_top1_fixed",
                "second_group_size":second,
                "third_pool_size":third,
                "confidence":confidence,
                "portfolio_guarded_ev_min":ev,
                "stake":"100_yen_each_ticket",
            },
            "A":evaluate(fx,1,1000,second,third,confidence,ev),
            "B":evaluate(fx,1001,1500,second,third,confidence,ev),
        })
    out={
        "record":"KEIRIN_BURNED_AB_3RENTAN_THIRD_SPREAD_SIMULATOR_OUTPUT_v1",
        "role":"BURNED_DIAGNOSTIC_DEV_ONLY",
        "A_races":1000,"B_races":500,
        "C_opened":False,"ECON_HOLDOUT1000_opened":False,
        "selection_note":"1st fixed to agreed model top1; 2nd narrow; 3rd widened by frozen ranking; optional portfolio-level conservative EV filter.",
        "rules":rows,
    }
    txt=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out: Path(args.out).write_text(txt,encoding="utf-8")
    else: print(txt,end="")

if __name__=="__main__":
    main()
