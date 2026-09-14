#!/usr/bin/env python3
import json, math
import numpy as np

PRIMARY_SEED = 20260916
REPLICATION_SEED = 20260917
PRIMARY_RACES_PER_WORLD = 2500
REPLICATION_RACES_PER_WORLD = 1800
TEMPERATURES = [0.75,1.0,1.25,1.5,2.0,2.5,3.0,4.0,5.0,6.0]
MIXTURES = {
    "MIX_1_2_3": ([1.0,2.0,3.0],[1/3,1/3,1/3]),
    "MIX_075_15_3_6": ([0.75,1.5,3.0,6.0],[0.25]*4),
    "MIX_1_2_4": ([1.0,2.0,4.0],[1/3,1/3,1/3]),
    "MIX_1_15_2_3_4": ([1.0,1.5,2.0,3.0,4.0],[0.2]*5),
}

def pl_sample(latent,rng):
    rem=list(range(len(latent))); out=[]
    for _ in range(len(latent)):
        v=np.array([latent[i] for i in rem],dtype=float); v-=v.max(); p=np.exp(v); p/=p.sum()
        j=rng.choice(len(rem),p=p); out.append(rem.pop(j))
    return out

def nll_temp(scores,order,t):
    rem=list(range(len(scores))); nll=0.0
    for w in order[:3]:
        v=np.array([scores[i]/t for i in rem],dtype=float); v-=v.max(); p=np.exp(v); p/=p.sum()
        idx=rem.index(w); nll-=math.log(max(float(p[idx]),1e-300)); rem.pop(idx)
    return nll

def nll_mix(scores,order,ts,weights):
    rem=list(range(len(scores))); nll=0.0
    for w in order[:3]:
        pm=None
        for t,wt in zip(ts,weights):
            v=np.array([scores[i]/t for i in rem],dtype=float); v-=v.max(); p=np.exp(v); p/=p.sum()
            pm=wt*p if pm is None else pm+wt*p
        idx=rem.index(w); nll-=math.log(max(float(pm[idx]),1e-300)); rem.pop(idx)
    return nll

def worlds():
    out={}
    for t in [0.7,0.9,1.1,1.3,1.6,2.0,2.5,3.0,3.5,4.0,5.0,6.0]: out[f"latent_T{t}"]=lambda s,r,t=t:s/t
    for q in [0.05,0.10,0.15,0.20,0.30,0.40]: out[f"rankrev_{q}"]=lambda s,r,q=q:np.where(r.random(len(s))<q,-s/2.0,s/2.0)
    for sd in [0.5,1.0,1.5,2.0]: out[f"measnoise_{sd}"]=lambda s,r,sd=sd:(s+r.normal(0,sd,len(s)))/2.0
    for c in [0.75,1.0,1.5,2.0]: out[f"tanh_{c}"]=lambda s,r,c=c:np.tanh(s/c)*c
    for q in [0.05,0.10,0.20]: out[f"upset_{q}"]=lambda s,r,q=q:s/2.0+(r.random(len(s))<q)*r.normal(0,2.2,len(s))
    out["hetero"]=lambda s,r:s/2.0+r.normal(0,0.25+0.18*np.abs(s),len(s))
    out["heavy_tail"]=lambda s,r:s/2.0+r.standard_t(3,len(s))*0.55
    out["mix_sharp_flat"]=lambda s,r:s/(1.0 if r.random()<0.5 else 5.0)
    return out

def run(seed,races_per_world):
    defs=worlds(); master=np.random.default_rng(seed); cand={f"T{t}":("t",t) for t in TEMPERATURES}
    for k,v in MIXTURES.items(): cand[k]=("m",v)
    per_world={}
    for name,transform in defs.items():
        seeds=master.integers(0,2**32-1,races_per_world,dtype=np.uint64); sums={k:0.0 for k in cand}
        for sk in seeds:
            rng=np.random.default_rng(int(sk)); n=int(rng.integers(5,10)); scores=rng.normal(0,1.4,n); order=pl_sample(np.array(transform(scores,rng)),rng)
            for k,spec in cand.items(): sums[k]+=nll_temp(scores,order,spec[1]) if spec[0]=="t" else nll_mix(scores,order,*spec[1])
        means={k:v/races_per_world for k,v in sums.items()}; best=min(means.values())
        per_world[name]={k:means[k]-best for k in cand}
    aggregate={}
    for k in cand:
        rs=[w[k] for w in per_world.values()]
        aggregate[k]={"mean_regret":float(np.mean(rs)),"max_regret":float(max(rs)),"p90_regret":float(np.quantile(rs,0.9))}
    return {"seed":seed,"races_per_world":races_per_world,"worlds":len(defs),"aggregate":aggregate}

if __name__=="__main__":
    print(json.dumps({"record":"R0_T2_SIMWORLD_FINE_SWEEP_v2","guard":"simulation-only; no promotion authority","primary":run(PRIMARY_SEED,PRIMARY_RACES_PER_WORLD),"replication":run(REPLICATION_SEED,REPLICATION_RACES_PER_WORLD)},indent=2,sort_keys=True))
