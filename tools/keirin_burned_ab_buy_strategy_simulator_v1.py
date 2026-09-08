#!/usr/bin/env python3
import argparse, collections, itertools, json, math
from pathlib import Path

MARKETS=("3rentan","3renhuku","2shatan","2shahuku","wide")

def iter_jsonl(path):
    with open(path,"rb") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def by_race(path):
    return {x["race_id"]:x for x in iter_jsonl(path)}

def wide_odds(v):
    if isinstance(v,dict):
        return float(v.get("low",v.get("high")))
    return float(v)

def unordered2(a,b):
    return f"{min(a,b)}={max(a,b)}"

def unordered3(a,b,c):
    return "=".join(map(str,sorted((a,b,c))))

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
        if "candidate_a" not in self.prob or "b1a_reconstituted_v1" not in self.prob:
            raise ValueError("required probability sources missing")

    def cons_first(self,idx):
        rid=self.settle[idx]["race_id"]
        out=[]
        marg=[]
        for src in ("candidate_a","b1a_reconstituted_v1"):
            d=collections.defaultdict(float)
            for t,p in self.prob[src][rid]["ticket_probabilities"]["2shatan"].items():
                i,_=map(int,t.split("-"))
                d[i]+=float(p)
            marg.append(d)
        cars=sorted(set(marg[0])|set(marg[1]))
        score={c:min(marg[0].get(c,0),marg[1].get(c,0)) for c in cars}
        topa=max(marg[0],key=marg[0].get); topb=max(marg[1],key=marg[1].get)
        rank=[c for c,_ in sorted(score.items(),key=lambda kv:kv[1],reverse=True)]
        return topa==topb,rank,score

    def pmin(self,rid,market,ticket):
        a=float(self.prob["candidate_a"][rid]["ticket_probabilities"][market][ticket])
        b=float(self.prob["b1a_reconstituted_v1"][rid]["ticket_probabilities"][market][ticket])
        return min(a,b)

    def payout(self,rid,market,ticket):
        x=next(v for v in self.settle.values() if v["race_id"]==rid)
        return float(x["settlements_yen_per_100"].get(market,{}).get(ticket,0))

def select(fx,idx,kind,k,confidence):
    rid=fx.settle[idx]["race_id"]
    agree,rank,score=fx.cons_first(idx)
    if not agree or score[rank[0]]<confidence:
        return []
    a=rank[0]; others=rank[1:1+k]; pairs=[]
    if kind=="wide_axis1":
        pairs=[("wide",unordered2(a,b)) for b in others]
    elif kind=="2shahuku_axis1":
        pairs=[("2shahuku",unordered2(a,b)) for b in others]
    elif kind=="2shatan_axis1":
        pairs=[("2shatan",f"{a}-{b}") for b in others]
    elif kind=="3renhuku_axis1":
        pairs=[("3renhuku",unordered3(a,b,c)) for b,c in itertools.combinations(others,2)]
    elif kind=="3rentan_axis1":
        pairs=[("3rentan",f"{a}-{b}-{c}") for b,c in itertools.permutations(others,2)]
    else:
        raise ValueError(kind)
    return pairs

def evaluate(fx,lo,hi,kind,k,confidence):
    stake=ret=bets=hits=tickets=0
    bank=100000.0; peak=bank; maxdd=0.0; largest=0.0
    weekly=collections.defaultdict(lambda:[0.0,0.0])
    for idx in range(lo,hi+1):
        rid=fx.settle[idx]["race_id"]
        sels=select(fx,idx,kind,k,confidence)
        if not sels: continue
        s=100*len(sels)
        r=sum(fx.payout(rid,m,t) for m,t in sels)
        stake+=s; ret+=r; bets+=1; tickets+=len(sels); hits+=r>0; largest=max(largest,r)
        bank+=r-s; peak=max(peak,bank); maxdd=max(maxdd,(peak-bank)/peak)
        date=fx.result[rid]["race_date"]
        # ISO week via stdlib
        y,m,d=map(int,date.split("-")); import datetime
        iso=datetime.date(y,m,d).isocalendar()
        key=f"{iso.year}-W{iso.week:02d}"
        weekly[key][0]+=s; weekly[key][1]+=r
    weekly_roi={k:(v[1]/v[0]-1 if v[0] else None) for k,v in sorted(weekly.items())}
    return {
        "bet_races":bets,"tickets":tickets,"stake":stake,"return":ret,
        "roi":ret/stake-1 if stake else None,"hit_rate":hits/bets if bets else None,
        "ending_bankroll":bank,"max_drawdown":maxdd,
        "largest_single_race_return_share":largest/ret if ret else None,
        "weekly_roi":weekly_roi,
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
    specs=[
        ("3renhuku_axis1",2,0.40),
        ("wide_axis1",1,0.40),
        ("wide_axis1",2,0.40),
        ("wide_axis1",3,0.40),
        ("2shatan_axis1",1,0.40),
        ("3rentan_axis1",2,0.40),
    ]
    rows=[]
    for kind,k,thr in specs:
        rows.append({
            "rule":{"kind":kind,"k":k,"confidence":thr},
            "A":evaluate(fx,1,1000,kind,k,thr),
            "B":evaluate(fx,1001,1500,kind,k,thr),
        })
    out={
        "record":"KEIRIN_BURNED_AB_BUY_STRATEGY_SIMULATOR_OUTPUT",
        "role":"BURNED_DIAGNOSTIC_DEV_ONLY",
        "C_opened":False,
        "ECON_HOLDOUT1000_opened":False,
        "stake_policy":"flat_100_yen_per_elementary_ticket",
        "rules":rows,
    }
    txt=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out: Path(args.out).write_text(txt,encoding="utf-8")
    else: print(txt,end="")

if __name__=="__main__":
    main()
