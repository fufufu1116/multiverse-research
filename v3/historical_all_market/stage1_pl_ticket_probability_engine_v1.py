#!/usr/bin/env python3
"""Stage-1 all-market elementary ticket probability engine v1.

Inputs:
- immutable DEV2000 Candidate A + B1a winner-probability CSV
- MARKET-STRUCTURE-ONLY JSONL (no numeric odds values)

Outputs probability catalogs only. No RESULT/PAYOUT/refund/EV/ROI.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any

EXPECTED_PREDICTION_SHA256 = "772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
EXPECTED_RACES = 2000
EXPECTED_ROWS = 14255
SUM_TOL = 1e-10
MODELS = {
    "candidate_a": "candidate_a_win_prob",
    "b1a_reconstituted_v1": "b1a_reconstituted_v1_win_prob",
}

class FailClosed(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def frame_map_for_nominal(n:int)->dict[int,int]:
    if n not in (7,8,9): raise FailClosed(f'unsupported nominal frame field={n}')
    singles=12-n
    out={c:c for c in range(1,singles+1)}
    frame=singles+1; c=singles+1
    while c<=n:
        out[c]=frame
        if c+1<=n: out[c+1]=frame
        c+=2; frame+=1
    return out

def frame_key_sets(active:list[int], fm:dict[int,int])->tuple[set[str],set[str]]:
    op=set(); un=set()
    for i in active:
        for j in active:
            if i==j: continue
            op.add(f'{fm[i]}-{fm[j]}')
    for a,b in itertools.combinations(active,2):
        fa,fb=fm[a],fm[b]
        un.add(f'{min(fa,fb)}={max(fa,fb)}')
    return op,un

def infer_frame_map(active:list[int], ticket_keys:dict[str,list[str]])->tuple[int,dict[int,int]]:
    pub_op=set(ticket_keys['2wakutan']); pub_un=set(ticket_keys['2wakuhuku'])
    valid=[]
    for nominal in (7,8,9):
        if max(active)>nominal: continue
        fm=frame_map_for_nominal(nominal)
        if not all(c in fm for c in active): continue
        op,un=frame_key_sets(active,fm)
        if op==pub_op and un==pub_un: valid.append((nominal,fm))
    if len(valid)!=1: raise FailClosed(f'frame-map ambiguity active={active} candidates={[n for n,_ in valid]}')
    return valid[0]

def exact_order_probs(cars:list[int], p:dict[int,float])->dict[str,float]:
    out={}
    for i in cars:
        d2=1.0-p[i]
        if d2<=0: raise FailClosed('invalid PL denominator after first')
        for j in cars:
            if j==i: continue
            d3=1.0-p[i]-p[j]
            if d3<=0: raise FailClosed('invalid PL denominator after second')
            for k in cars:
                if k==i or k==j: continue
                out[f'{i}-{j}-{k}']=p[i]*(p[j]/d2)*(p[k]/d3)
    return out

def build_market_probs(cars:list[int], p:dict[int,float], sold:list[str], ticket_keys:dict[str,list[str]])->tuple[dict[str,dict[str,float]],int|None]:
    out={}; ordered_pair={}
    if any(m in sold for m in ('2shatan','2shahuku','2wakutan','2wakuhuku')):
        for i in cars:
            d=1-p[i]
            if d<=0: raise FailClosed('invalid pair denominator')
            for j in cars:
                if i==j: continue
                ordered_pair[f'{i}-{j}']=p[i]*p[j]/d
        if '2shatan' in sold: out['2shatan']=dict(ordered_pair)
        if '2shahuku' in sold:
            out['2shahuku']={f'{a}={b}':ordered_pair[f'{a}-{b}']+ordered_pair[f'{b}-{a}'] for a,b in itertools.combinations(cars,2)}
    exact=None
    if any(m in sold for m in ('3rentan','3renhuku','wide')):
        exact=exact_order_probs(cars,p)
        if '3rentan' in sold: out['3rentan']=exact
        if '3renhuku' in sold:
            d={}
            for comb in itertools.combinations(cars,3):
                d['='.join(map(str,comb))]=sum(exact['-'.join(map(str,perm))] for perm in itertools.permutations(comb))
            out['3renhuku']=d
        if 'wide' in sold:
            d={}
            for a,b in itertools.combinations(cars,2):
                s=0.0
                for k in cars:
                    if k in (a,b): continue
                    for perm in itertools.permutations((a,b,k)):
                        s += exact['-'.join(map(str,perm))]
                d[f'{a}={b}']=s
            out['wide']=d
    nominal=None
    if '2wakutan' in sold or '2wakuhuku' in sold:
        if not ('2wakutan' in sold and '2wakuhuku' in sold): raise FailClosed('frame markets not paired')
        nominal,fm=infer_frame_map(cars,ticket_keys)
        wt=defaultdict(float); wh=defaultdict(float)
        for key,val in ordered_pair.items():
            i,j=map(int,key.split('-'))
            wt[f'{fm[i]}-{fm[j]}'] += val
        for a,b in itertools.combinations(cars,2):
            val=ordered_pair[f'{a}-{b}']+ordered_pair[f'{b}-{a}']
            fa,fb=fm[a],fm[b]
            wh[f'{min(fa,fb)}={max(fa,fb)}'] += val
        out['2wakutan']=dict(wt); out['2wakuhuku']=dict(wh)
    return out,nominal

def assert_market_invariants(rid:str,model:str,out:dict[str,dict[str,float]],ticket_keys:dict[str,list[str]])->dict[str,float]:
    sums={}
    for m,cat in out.items():
        if set(cat)!=set(ticket_keys[m]):
            miss=set(ticket_keys[m])-set(cat); extra=set(cat)-set(ticket_keys[m])
            raise FailClosed(f'{rid}/{model}/{m}: ticket-key mismatch missing={list(miss)[:5]} extra={list(extra)[:5]}')
        for k,v in cat.items():
            if not math.isfinite(v) or v<=0: raise FailClosed(f'{rid}/{model}/{m}/{k}: invalid probability={v}')
        s=sum(cat.values()); target=3.0 if m=='wide' else 1.0
        if abs(s-target)>SUM_TOL: raise FailClosed(f'{rid}/{model}/{m}: probability sum={s} target={target}')
        sums[m]=s
    return sums

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('prediction_csv')
    ap.add_argument('market_structure_jsonl')
    ap.add_argument('output_jsonl')
    ap.add_argument('quality_json')
    a=ap.parse_args()
    pred_path=Path(a.prediction_csv); struct_path=Path(a.market_structure_jsonl)
    out_path=Path(a.output_jsonl); quality_path=Path(a.quality_json)
    if sha256_file(pred_path)!=EXPECTED_PREDICTION_SHA256: raise FailClosed('prediction CSV SHA mismatch')

    # prediction input
    by_race=defaultdict(list); rows=0
    with pred_path.open('r',encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            rid=str(r['race_id']); car=int(r['car_no']); rows+=1
            by_race[rid].append({
                'car_no':car,
                'candidate_a':float(r['candidate_a_win_prob']),
                'b1a_reconstituted_v1':float(r['b1a_reconstituted_v1_win_prob']),
            })
    if rows!=EXPECTED_ROWS or len(by_race)!=EXPECTED_RACES: raise FailClosed(f'prediction cardinality rows={rows} races={len(by_race)}')

    structs=[]; seen=set()
    with struct_path.open('r',encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line); rid=str(r['race_id'])
            if rid in seen: raise FailClosed(f'duplicate structure race={rid}')
            seen.add(rid); structs.append(r)
    if len(structs)!=EXPECTED_RACES or set(by_race)!=seen: raise FailClosed('prediction/structure race-set mismatch')

    model_market_counts=Counter(); frame_nominal_counts=Counter(); max_sum_error=Counter(); out_rows=0
    out_path.parent.mkdir(parents=True,exist_ok=True)
    with out_path.open('w',encoding='utf-8',newline='\n') as w:
        for st in structs:
            rid=str(st['race_id']); cars=[int(x) for x in st['active_car_numbers']]; sold=list(st['sold_markets']); keys=st['ticket_keys']
            prows=by_race[rid]; pred_cars=sorted(x['car_no'] for x in prows)
            if pred_cars!=cars: raise FailClosed(f'{rid}: prediction cars={pred_cars} structure cars={cars}')
            pmap_by_model={m:{x['car_no']:float(x[m]) for x in prows} for m in MODELS}
            for model,p in pmap_by_model.items():
                if any((not math.isfinite(v) or v<=0) for v in p.values()): raise FailClosed(f'{rid}/{model}: invalid winner probability')
                ps=sum(p.values())
                if abs(ps-1.0)>SUM_TOL: raise FailClosed(f'{rid}/{model}: winner sum={ps}')
                markets,nominal=build_market_probs(cars,p,sold,keys)
                sums=assert_market_invariants(rid,model,markets,keys)
                if nominal is not None: frame_nominal_counts[nominal]+=1
                for m,s in sums.items():
                    model_market_counts[f'{model}:{m}']+=1
                    target=3.0 if m=='wide' else 1.0
                    max_sum_error[f'{model}:{m}']=max(max_sum_error[f'{model}:{m}'],abs(s-target))
                rec={
                    'race_id':rid,
                    'probability_source':model,
                    'active_car_numbers':cars,
                    'sold_markets':sold,
                    'frame_nominal_field':nominal,
                    'ticket_probabilities':markets,
                    'probability_sums':sums,
                    'closing_odds_values_included':False,
                    'result_fields_included':False,
                    'settlement_fields_included':False,
                    'ev_roi_computed':False,
                }
                w.write(json.dumps(rec,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'); out_rows+=1
    if out_rows!=EXPECTED_RACES*len(MODELS): raise FailClosed(f'output rows={out_rows}')
    quality={
        'record':'STAGE1_PL_TICKET_PROBABILITY_QUALITY_v1',
        'status':'PASS',
        'prediction_sha256':EXPECTED_PREDICTION_SHA256,
        'market_structure_sha256':sha256_file(struct_path),
        'output_sha256':sha256_file(out_path),
        'prediction_rows':rows,
        'races':EXPECTED_RACES,
        'probability_sources':list(MODELS),
        'output_rows':out_rows,
        'model_market_race_counts':dict(model_market_counts),
        'frame_nominal_inferences_across_model_rows':{str(k):v for k,v in sorted(frame_nominal_counts.items())},
        'max_probability_sum_error':dict(max_sum_error),
        'ticket_key_mismatches':0,
        'closing_odds_values_included':False,
        'result_fields_included':False,
        'settlement_fields_included':False,
        'ev_roi_computed':False,
        'scientific_trial_count':0,
        'ECON_HOLDOUT1000':'SEALED',
    }
    quality_path.parent.mkdir(parents=True,exist_ok=True)
    quality_path.write_text(json.dumps(quality,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(quality,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
