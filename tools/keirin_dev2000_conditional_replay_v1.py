#!/usr/bin/env python3
"""DEV2000 A+B-only conditional Keirin replay.

Research-only diagnostic runner. It accepts A and B settlements only and never
accepts a Segment C settlement path. Combined 2000-row containers may be used
as source archives, but rows outside the exact A+B race-id membership are not
JSON-decoded for scoring.
"""
from __future__ import annotations
import argparse, collections, datetime, gzip, itertools, json, math, re
from pathlib import Path

RID_RE=re.compile(rb'"race_id"\s*:\s*"([^"]+)"')
SOURCES=("candidate_a","b1a_reconstituted_v1")


def iter_jsonl(path):
    op=gzip.open if str(path).endswith('.gz') else open
    with op(path,'rb') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def selective_jsonl(path, allowed):
    out={}
    op=gzip.open if str(path).endswith('.gz') else open
    with op(path,'rb') as f:
        for line in f:
            m=RID_RE.search(line)
            if not m: continue
            rid=m.group(1).decode()
            if rid in allowed:
                out[rid]=json.loads(line)
    return out


def load(args):
    settle={}
    for path in (args.settlement_a,args.settlement_b):
        for x in iter_jsonl(path):
            idx=int(x['dev_index'])
            if str(x.get('segment','')).upper()=='C' or idx>1500:
                raise ValueError('Segment C is prohibited')
            settle[idx]=x
    if set(settle)!=set(range(1,1501)):
        raise ValueError('A+B settlements must be exact dev_index 1..1500')
    ids={settle[i]['race_id'] for i in range(1,1501)}
    price=selective_jsonl(args.price,ids)
    result=selective_jsonl(args.result,ids)
    pre=selective_jsonl(args.pre,ids)
    prob=collections.defaultdict(dict)
    op=gzip.open if str(args.probability).endswith('.gz') else open
    with op(args.probability,'rb') as f:
        for line in f:
            m=RID_RE.search(line)
            if not m: continue
            rid=m.group(1).decode()
            if rid in ids:
                x=json.loads(line); prob[x['probability_source']][rid]=x
    if not (len(price)==len(result)==len(pre)==1500):
        raise ValueError('A+B source membership incomplete')
    for src in SOURCES:
        if set(prob[src])!=ids: raise ValueError(f'probability source incomplete: {src}')
    rid_to_idx={settle[i]['race_id']:i for i in range(1,1501)}
    return settle,price,result,pre,prob,rid_to_idx


def first_rank(rid,prob):
    marg=[]
    for src in SOURCES:
        d=collections.defaultdict(float)
        for t,p in prob[src][rid]['ticket_probabilities']['2shatan'].items():
            a,_=map(int,t.split('-')); d[a]+=float(p)
        marg.append(d)
    cars=sorted(set(marg[0])|set(marg[1]))
    score={c:min(marg[0].get(c,0),marg[1].get(c,0)) for c in cars}
    rank=[c for c,_ in sorted(score.items(),key=lambda kv:(-kv[1],kv[0]))]
    return max(marg[0],key=marg[0].get)==max(marg[1],key=marg[1].get),rank,score


def pmin(prob,rid,market,ticket):
    return min(float(prob[s][rid]['ticket_probabilities'][market][ticket]) for s in SOURCES)


def price_of(price,rid,market,ticket):
    v=price[rid]['closing_price_catalogs'][market][ticket]
    if isinstance(v,dict): v=v.get('low',v.get('high'))
    return float(v)


def payout(settle,rid_to_idx,rid,market,ticket):
    return float(settle[rid_to_idx[rid]]['settlements_yen_per_100'].get(market,{}).get(ticket,0))


def girls(pre,rid):
    cls=[e.get('class') for e in pre[rid]['entrants'] if not e.get('withdrawn')]
    return bool(cls) and all(c=='L1' for c in cls)


def score_gap(pre,rid):
    s=sorted((float(e['score']) for e in pre[rid]['entrants'] if not e.get('withdrawn')),reverse=True)
    return s[0]-s[1]


def evaluate(indices,settle,price,result,pre,prob,rid_to_idx,conditional=False):
    stake=ret=bets=hits=tickets=0; largest=0.0
    weekly=collections.defaultdict(lambda:[0.,0.])
    for idx in indices:
        rid=settle[idx]['race_id']
        agree,rank,score=first_rank(rid,prob)
        if not agree or score[rank[0]]<0.40: continue
        if conditional and (girls(pre,rid) or score_gap(pre,rid)>=5): continue
        first=rank[0]
        pool=rank[1:4] if conditional else rank[1:3]
        cand=[]
        for b,c in itertools.combinations(pool,2):
            t='='.join(map(str,sorted((first,b,c))))
            p=pmin(prob,rid,'3renhuku',t); o=price_of(price,rid,'3renhuku',t)
            if p*o-1>=0.10 and o<=20.0:
                cand.append((t,p,o,payout(settle,rid_to_idx,rid,'3renhuku',t)))
        if not cand: continue
        cand=sorted(cand,key=lambda x:(-x[1],x[2],x[0]))[:(2 if conditional else 1)]
        s=100*len(cand); r=sum(x[3] for x in cand)
        stake+=s; ret+=r; bets+=1; tickets+=len(cand); hits+=r>0; largest=max(largest,r)
        date=result[rid]['race_date']
        y,m,d=map(int,date.split('-')); iso=datetime.date(y,m,d).isocalendar(); key=f'{iso.year}-W{iso.week:02d}'
        weekly[key][0]+=s; weekly[key][1]+=r
    return {
        'bet_races':bets,'tickets':tickets,'stake':stake,'return':ret,
        'roi':ret/stake-1 if stake else None,'hit_rate':hits/bets if bets else None,
        'average_points':tickets/bets if bets else None,
        'largest_single_return_share':largest/ret if ret else None,
        'positive_week_fraction':sum(1 for s,r in weekly.values() if r>s)/len(weekly) if weekly else None,
    }


def main():
    ap=argparse.ArgumentParser()
    for n in ('price','probability','result','pre','settlement-a','settlement-b'):
        ap.add_argument('--'+n,required=True)
    ap.add_argument('--out')
    a=ap.parse_args()
    settle,price,result,pre,prob,rid_to_idx=load(a)
    out={'record':'KEIRIN_DEV2000_CONDITIONAL_REPLAY_v1','C_scoring_count':0,'rules':{}}
    for name,cond in [('CENTER_1PT',False),('NON_GIRLS_GAP_LT5_POOL3_MAX2',True)]:
        out['rules'][name]={
            'A':evaluate(range(1,1001),settle,price,result,pre,prob,rid_to_idx,cond),
            'B':evaluate(range(1001,1501),settle,price,result,pre,prob,rid_to_idx,cond),
            'AB':evaluate(range(1,1501),settle,price,result,pre,prob,rid_to_idx,cond),
        }
    text=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if a.out: Path(a.out).write_text(text,encoding='utf-8')
    else: print(text,end='')

if __name__=='__main__': main()
