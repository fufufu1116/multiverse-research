#!/usr/bin/env python3
"""Burned diagnostic: 3rentan fixed-head under-box formations.

Predicted rank1 is fixed at first place. Second/third are ordered permutations
from predicted ranks 2..N. Finite prespecified family only.
"""
from __future__ import annotations
import argparse,csv,itertools,json
from pathlib import Path

QUARANTINE={'8320260327010001'}
N_VALUES=[3,4,5,6]

def maxdd(nets):
    eq=peak=mdd=0
    for x in nets:
        eq+=x; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    return mdd

def score(es):
    if not es:return {'races':0,'tickets':0}
    tickets=sum(e['tickets'] for e in es); stake=100*tickets
    ret=sum(e['return'] for e in es); hits=sum(e['hit'] for e in es)
    wins=sorted((e['return'] for e in es if e['return']>0),reverse=True)
    largest=wins[0] if wins else 0
    return {'races':len(es),'tickets':tickets,'avg_points_per_race':tickets/len(es),
            'hit_races':hits,'hit_race_rate':hits/len(es),'stake_yen':stake,
            'return_yen':ret,'net_yen':ret-stake,'recovery_rate':ret/stake,
            'roi':ret/stake-1,'maximum_drawdown_yen':maxdd([e['return']-100*e['tickets'] for e in es]),
            'largest_race_return_yen':largest,'largest_race_return_share':largest/ret if ret else None}

def rg(name,e):
    if name=='ALL':return True
    if name=='GIRLS':return e['girls']
    if name=='NON_GIRLS':return not e['girls']
    if name=='AGREE_CONF40':return e['agree'] and e['p']>=.40
    if name=='GIRLS_AGREE_CONF40':return e['girls'] and e['agree'] and e['p']>=.40
    if name=='STRONG_HEAD_GAP_GE3':return e['agree'] and e['gap']>=3
    if name=='VERY_STRONG_HEAD_GAP_GE5':return e['agree'] and e['gap']>=5
    raise KeyError(name)

REGIMES=['ALL','GIRLS','NON_GIRLS','AGREE_CONF40','GIRLS_AGREE_CONF40','STRONG_HEAD_GAP_GE3','VERY_STRONG_HEAD_GAP_GE5']

def load_pred(p):
    x=json.loads(Path(p).read_text(encoding='utf-8')); s=x['safeguards']
    assert s['result_accessed'] is False and s['payout_accessed'] is False and s['odds_accessed'] is False
    return {r['race_id']:r for r in x['races'] if r['race_id'] not in QUARANTINE}

def load_pay(paths):
    d={}
    for p in paths:
        for r in csv.DictReader(open(p,encoding='utf-8',newline='')):
            if r['market']!='3rentan':continue
            if r['race_id'] in d:raise ValueError('duplicate')
            d[r['race_id']]={'ticket':r['winning_ticket'],'payout':int(r['payout_yen_per_100'])}
    return d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prediction',required=True);ap.add_argument('--payout',action='append',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args(); pred=load_pred(a.prediction); pay=load_pay(a.payout)
    ids=sorted(set(pred)&set(pay),key=lambda rid:(pred[rid]['race_date'],rid))
    entries={n:[] for n in N_VALUES}
    for rid in ids:
        r=pred[rid]; rank=list(map(int,r['conservative_rank'])); win=pay[rid]['ticket']
        for n in N_VALUES:
            under=rank[1:n]
            t=[f"{rank[0]}-{a2}-{a3}" for a2,a3 in itertools.permutations(under,2)]
            hit=win in t
            entries[n].append({'race_id':rid,'race_date':r['race_date'],'girls':bool(r['girls']),
                               'agree':bool(r['top1_agree']),'p':float(r['conservative_top1_probability']),
                               'gap':float(r['top_score_gap']),'tickets':len(t),'hit':int(hit),
                               'return':pay[rid]['payout'] if hit else 0})
    strategies={}
    for n,es in entries.items():
        by={name:score([e for e in es if rg(name,e)]) for name in REGIMES}
        blocks=[]
        for i in range(0,len(es),250):
            b=score(es[i:i+250]);b['block_index']=i//250+1;blocks.append(b)
        strategies[f'HEAD_TOP1_UNDER_RANK2_TO_{n}_ORDERED_BOX']={'under_riders':n-1,'nominal_points':(n-1)*(n-2),'regimes':by,'chronological_250race_blocks':blocks}
    out={'record':'KEIRIN_NEXTGEN5000_3RENTAN_FIXED_HEAD_UNDER_BOX_DIAGNOSTIC_v1',
         'status':'POST_OUTCOME_BURNED_DIAGNOSTIC_ONLY_NO_PROMOTION','races_scored':len(ids),
         'strategies':strategies,
         'interpretation_boundary':['Rank1 is fixed first. Only second/third ordered combinations among ranks 2..N are purchased.',
           'No odds are used. Higher hit rate alone is not success.','Any candidate requires untouched successor validation before promotion.'],
         'hard_boundaries':{'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'model_refit':False,'runtime':False,'promotion_authorized':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    for k,v in strategies.items():
        for name in ['ALL','GIRLS','GIRLS_AGREE_CONF40','STRONG_HEAD_GAP_GE3','VERY_STRONG_HEAD_GAP_GE5']:
            print('FORMATION',k,name,json.dumps(v['regimes'][name],sort_keys=True))

if __name__=='__main__':main()
