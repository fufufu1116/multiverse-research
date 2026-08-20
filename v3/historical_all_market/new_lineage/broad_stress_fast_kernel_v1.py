from __future__ import annotations
from itertools import permutations
import math
import random
from typing import Mapping, Tuple
import numpy as np
from digital_twin_v1 import Race
from digital_twin_stress_grid_v1 import StressAssumptions

Top3 = Tuple[int,int,int]
TOP3_KEYS: tuple[Top3,...] = tuple(permutations(range(1,8),3))
TOP3_INDEX = {k:i for i,k in enumerate(TOP3_KEYS)}

_CLASS = {"S1":0.08,"S2":-0.03,"A1":0.05,"A2":-0.03,"A3":0.0}
_STYLE = {"逃":0.06,"両":0.04,"追":0.0}

def _base_utility(r, race:Race, cfg:StressAssumptions)->float:
    wind_penalty=0.035*cfg.wind_effect_scale*race.wind_speed_mps*(1.0 if r.style=="逃" else 0.25)
    bank_term=0.04*cfg.bank_effect_scale if (race.bank_length_m<=333 and r.style in {"逃","両"}) else 0.0
    return r.latent_skill+_CLASS[r.rider_class]+_STYLE[r.style]+bank_term-wind_penalty

def _softmax_for(cars:list[int], values:dict[int,float])->dict[int,float]:
    m=max(values[c] for c in cars)
    ex=[math.exp(values[c]-m) for c in cars]
    z=sum(ex)
    return {c:e/z for c,e in zip(cars,ex)}

def _joint_cached(race:Race, util:dict[int,float], relation_strength:float)->np.ndarray:
    cars=[r.car_no for r in race.riders]
    rider={r.car_no:r for r in race.riders}
    p1=_softmax_for(cars,util)
    p2_cache={}
    p3_cache={}
    for i in cars:
        rem2=[c for c in cars if c!=i]
        if relation_strength<=0.0:
            u2={c:util[c] for c in rem2}
        else:
            ri=rider[i]; u2={}
            for c in rem2:
                rc=rider[c]
                same=1.0 if rc.line_id==ri.line_id else 0.0
                follower=1.0 if same and rc.line_position==ri.line_position+1 else 0.0
                u2[c]=util[c]+relation_strength*(0.30*same+0.28*follower)
        p2_cache[i]=_softmax_for(rem2,u2)
        for j in rem2:
            rem3=[c for c in rem2 if c!=j]
            if relation_strength<=0.0:
                u3={c:util[c] for c in rem3}
            else:
                ri=rider[i]; rj=rider[j]; u3={}
                for c in rem3:
                    rc=rider[c]
                    same_i=1.0 if rc.line_id==ri.line_id else 0.0
                    same_j=1.0 if rc.line_id==rj.line_id else 0.0
                    chain=1.0 if (ri.line_id==rj.line_id==rc.line_id and ri.line_position<rj.line_position<rc.line_position) else 0.0
                    u3[c]=util[c]+relation_strength*(0.17*same_i+0.14*same_j+0.30*chain)
            p3_cache[(i,j)]=_softmax_for(rem3,u3)
    out=np.empty(len(TOP3_KEYS),dtype=np.float64)
    for idx,(i,j,k) in enumerate(TOP3_KEYS):
        out[idx]=p1[i]*p2_cache[i][j]*p3_cache[(i,j)][k]
    out/=out.sum()
    return out

def stress_truth_array(race:Race,cfg:StressAssumptions)->np.ndarray:
    groups={}
    for r in race.riders: groups.setdefault(r.line_id,[]).append(r.latent_skill)
    line_strength={line:sum(vals)/len(vals) for line,vals in groups.items()}
    stable_util={}
    for r in race.riders:
        value=_base_utility(r,race,cfg)
        if cfg.line_static_scale>0.0:
            pos_bonus={0:0.04,1:0.10,2:0.05}.get(r.line_position,0.0)
            size_bonus=0.025*max(0,r.line_size-1)
            value += cfg.line_static_scale*(0.16*line_strength[r.line_id]+pos_bonus+size_bonus)
        stable_util[r.car_no]=value
    stable=_joint_cached(race,stable_util,cfg.relation_strength)
    if cfg.disruption_weight<=0.0: return stable
    no_line={r.car_no:_base_utility(r,race,cfg) for r in race.riders}
    disrupted_util={}
    for car_no,value in no_line.items():
        rng=random.Random(f"{cfg.scenario_id}-shock:{race.race_id}:{car_no}")
        shock=rng.gauss(0.0,cfg.shock_sigma)
        disrupted_util[car_no]=value/cfg.shock_temperature+shock
    disrupted=_joint_cached(race,disrupted_util,cfg.disrupted_relation_strength)
    out=(1.0-cfg.disruption_weight)*stable+cfg.disruption_weight*disrupted
    out/=out.sum()
    return out

def pred_array(pred:Mapping[Top3,float])->np.ndarray:
    if set(pred)!=set(TOP3_KEYS): raise AssertionError('fast_kernel_support_mismatch')
    return np.fromiter((float(pred[k]) for k in TOP3_KEYS),dtype=np.float64,count=len(TOP3_KEYS))

def score_arrays(truth:np.ndarray,pred:np.ndarray)->tuple[float,float,float]:
    eps=1e-300
    ll=float(-np.dot(truth,np.log(np.maximum(pred,eps))))
    entropy=float(-np.dot(truth,np.log(np.maximum(truth,eps))))
    brier=float(np.dot(pred-truth,pred-truth))
    return ll,ll-entropy,brier
