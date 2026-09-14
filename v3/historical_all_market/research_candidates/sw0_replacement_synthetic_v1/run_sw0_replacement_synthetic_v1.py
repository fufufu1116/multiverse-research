#!/usr/bin/env python3
import argparse, hashlib, json, math, random
from collections import defaultdict

SEEDS=[104729,130363,155921,181081,207017]
FIELDS=[5,6,7,8,9]
WORLDS=['W0','W1','W2','W3','W4']
RACES_PER_CELL=500
EPS=1e-15

CANDIDATES=[]
for t in (1.5,2.0,3.0): CANDIDATES.append((f'R0_T{t:g}','R0',{'temperature':t}))
for a in (0.25,0.5,0.75): CANDIDATES.append((f'R1_A{a:g}','R1',{'alpha':a,'scale':0.5}))
for m in (0.25,0.5,0.75): CANDIDATES.append((f'R2_M{m:g}','R2',{'uniform_mix':m}))
REFERENCES=[('REF_UNIFORM','UNIFORM',{}),('REF_BASE_SCORE_PL','BASE',{})]


def softmax(xs):
    m=max(xs); z=[math.exp(x-m) for x in xs]; s=sum(z); return [v/s for v in z]

def rank_feature(scores):
    n=len(scores); order=sorted(range(n), key=lambda i:(scores[i],-i), reverse=True)
    r=[0.0]*n
    if n==1: return r
    for pos,i in enumerate(order): r[i]=1.0-2.0*pos/(n-1)
    return r

def true_logits(world,scores):
    r=rank_feature(scores)
    if world=='W0': return [0.35*x for x in scores]
    if world=='W1': return [0.55*x for x in scores]
    if world=='W2': return [0.75*x for x in scores]
    if world=='W3': return [0.45*math.tanh(x)+0.10*x for x in scores]
    if world=='W4': return [0.25*x+0.35*rr for x,rr in zip(scores,r)]
    raise ValueError(world)

def sequential_probs(kind,params,scores,remaining):
    vals=[scores[i] for i in remaining]
    if kind=='UNIFORM': return [1.0/len(remaining)]*len(remaining)
    if kind=='BASE': return softmax(vals)
    if kind=='R0': return softmax([x/params['temperature'] for x in vals])
    if kind=='R1':
        rfull=rank_feature(scores); a=params['alpha']; sc=params['scale']
        return softmax([sc*((1-a)*scores[i]+a*rfull[i]) for i in remaining])
    if kind=='R2':
        p=softmax(vals); m=params['uniform_mix']; u=1.0/len(remaining)
        return [(1-m)*x+m*u for x in p]
    raise ValueError(kind)

def sample_order(rng, logits, k=3):
    rem=list(range(len(logits))); out=[]
    for _ in range(min(k,len(rem))):
        p=softmax([logits[i] for i in rem]); u=rng.random(); c=0.0; chosen=len(rem)-1
        for j,q in enumerate(p):
            c+=q
            if u<=c: chosen=j; break
        out.append(rem.pop(chosen))
    return out

def model_metrics(kind,params,scores,order):
    n=len(scores); pwin=sequential_probs(kind,params,scores,list(range(n)))
    y=order[0]
    ll=-math.log(max(EPS,pwin[y]))
    brier=sum((p-(1.0 if i==y else 0.0))**2 for i,p in enumerate(pwin))
    rem=list(range(n)); pord=1.0
    for yk in order[:3]:
        pk=sequential_probs(kind,params,scores,rem); j=rem.index(yk); pord*=pk[j]; rem.pop(j)
    onll=-math.log(max(EPS,pord))
    pred=max(range(n), key=lambda i:(pwin[i],-i)); top1=1.0 if pred==y else 0.0
    pred3=sorted(range(n), key=lambda i:(pwin[i],-i), reverse=True)[:3]
    contain=1.0 if set(order[:3])==set(pred3) else 0.0
    conf=max(pwin); correct=top1
    sane=all(math.isfinite(p) and p>=0 for p in pwin) and abs(sum(pwin)-1.0)<=1e-12 and math.isfinite(onll)
    return ll,brier,onll,top1,contain,conf,correct,sane

def ece(pairs,bins=10):
    total=len(pairs); acc=0.0
    for b in range(bins):
        lo=b/bins; hi=(b+1)/bins
        bucket=[(c,y) for c,y in pairs if (c>=lo and (c<hi or (b==bins-1 and c<=hi)))]
        if bucket:
            mc=sum(c for c,_ in bucket)/len(bucket); my=sum(y for _,y in bucket)/len(bucket)
            acc += len(bucket)/total*abs(mc-my)
    return acc

def run():
    specs=REFERENCES+CANDIDATES
    agg={name:defaultdict(float) for name,_,_ in specs}; counts=defaultdict(int)
    calib={name:defaultdict(list) for name,_,_ in specs}; sane={name:True for name,_,_ in specs}
    cellmetrics={name:{} for name,_,_ in specs}
    for world in WORLDS:
      for n in FIELDS:
       for seed in SEEDS:
        cell=(world,n,seed); local_rng=random.Random(seed*1000003+n*1009+WORLDS.index(world)*9176)
        sums={name:[0.0]*5 for name,_,_ in specs}; cpairs={name:[] for name,_,_ in specs}; csane={name:True for name,_,_ in specs}
        for _ in range(RACES_PER_CELL):
            scores=[local_rng.gauss(0.0,1.0) for _ in range(n)]
            order=sample_order(local_rng,true_logits(world,scores),3)
            for name,kind,params in specs:
                vals=model_metrics(kind,params,scores,order)
                for j in range(5): sums[name][j]+=vals[j]
                cpairs[name].append((vals[5],vals[6])); csane[name]=csane[name] and vals[7]
        counts[cell]=RACES_PER_CELL
        for name,_,_ in specs:
            means=[x/RACES_PER_CELL for x in sums[name]]; ce=ece(cpairs[name])
            cellmetrics[name][f'{world}|{n}|{seed}']={'winner_logloss':means[0],'winner_brier':means[1],'ordered_top3_nll':means[2],'top1_accuracy':means[3],'unordered_top3_containment':means[4],'toplabel_ece10':ce,'sane':csane[name]}
            for j,key in enumerate(['winner_logloss','winner_brier','ordered_top3_nll','top1_accuracy','unordered_top3_containment']): agg[name][key]+=sums[name][j]
            calib[name]['pairs'].extend(cpairs[name]); sane[name]=sane[name] and csane[name]
    total=sum(counts.values())
    pooled={}
    for name,_,_ in specs:
        pooled[name]={k:agg[name][k]/total for k in ['winner_logloss','winner_brier','ordered_top3_nll','top1_accuracy','unordered_top3_containment']}
        pooled[name]['toplabel_ece10']=ece(calib[name]['pairs']); pooled[name]['sane']=sane[name]
        pooled[name]['worst_cell_toplabel_ece10']=max(v['toplabel_ece10'] for v in cellmetrics[name].values())
    u=pooled['REF_UNIFORM']; eligible=[]
    for name,fam,params in CANDIDATES:
        p=pooled[name]
        ok=(p['sane'] and p['worst_cell_toplabel_ece10']<=0.15 and p['ordered_top3_nll']<=u['ordered_top3_nll']+1e-12 and p['winner_logloss']<=u['winner_logloss']+1e-12 and p['winner_brier']<=u['winner_brier']+1e-12)
        if ok: eligible.append(name)
        p['eligible']=ok
    eligible.sort(key=lambda name:(pooled[name]['ordered_top3_nll'],pooled[name]['winner_logloss'],pooled[name]['winner_brier'],name))
    winner=eligible[0] if eligible else None
    return {'record':'KEIRIN_SW0_REPLACEMENT_SYNTHETIC_RESULT_v1','design':{'seeds':SEEDS,'field_sizes':FIELDS,'worlds':WORLDS,'races_per_cell':RACES_PER_CELL,'total_races':total},'references':[x[0] for x in REFERENCES],'candidate_ids':[x[0] for x in CANDIDATES],'pooled':pooled,'eligible_candidates':eligible,'winner':winner,'verdict':('SYNTHETICALLY_ELIGIBLE_REPLACEMENT_FROZEN' if winner else 'NO_SYNTHETICALLY_ELIGIBLE_REPLACEMENT'),'cell_metrics':cellmetrics,'protected_access':{'gate487':False,'dev2000_c':False,'econ_holdout1000':False,'result_payout':False,'odds_economics':False,'runtime':'OFF','automatic_betting':False}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args()
    result=run(); raw=json.dumps(result,sort_keys=True,indent=2,separators=(',',': '))+'\n'
    with open(args.out,'w',encoding='utf-8') as f: f.write(raw)
    print(json.dumps({'verdict':result['verdict'],'winner':result['winner'],'sha256':hashlib.sha256(raw.encode()).hexdigest(),'total_races':result['design']['total_races']},sort_keys=True))
if __name__=='__main__': main()
