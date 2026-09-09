#!/usr/bin/env python3
"""Coarse burned audit for GIRLS 3rentan top1-top2-top3 1pt.

Finite simple gates only. Intended to decide whether a successor untouched
candidate is worth freezing; never promotes on this burned sample.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
Q={'8320260327010001'}

def maxdd(es):
    eq=peak=m=0
    for e in es:
        eq+=e['net'];peak=max(peak,eq);m=max(m,peak-eq)
    return m
def score(es):
    if not es:return {'races':0}
    stake=100*len(es);ret=sum(e['ret'] for e in es);hits=sum(e['hit'] for e in es)
    return {'races':len(es),'hits':hits,'hit_rate':hits/len(es),'stake_yen':stake,'return_yen':ret,
            'net_yen':ret-stake,'recovery_rate':ret/stake,'roi':ret/stake-1,'maximum_drawdown_yen':maxdd(es)}
def loadp(path):
    x=json.loads(Path(path).read_text());s=x['safeguards'];assert not s['result_accessed'] and not s['payout_accessed'] and not s['odds_accessed']
    return {r['race_id']:r for r in x['races'] if r['race_id'] not in Q}
def loadpay(paths):
    d={}
    for p in paths:
        for r in csv.DictReader(open(p,encoding='utf-8',newline='')):
            if r['market']=='3rentan':d[r['race_id']]=(r['winning_ticket'],int(r['payout_yen_per_100']))
    return d
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prediction',required=True);ap.add_argument('--payout',action='append',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();pred=loadp(a.prediction);pay=loadpay(a.payout)
    es=[]
    for rid in sorted(set(pred)&set(pay),key=lambda r:(pred[r]['race_date'],r)):
        x=pred[rid]
        if not x['girls']:continue
        rank=list(map(int,x['conservative_rank']));t=f"{rank[0]}-{rank[1]}-{rank[2]}";win,payout=pay[rid]
        hit=t==win
        es.append({'rid':rid,'date':x['race_date'],'hit':int(hit),'ret':payout if hit else 0,'net':(payout if hit else 0)-100,
                   'agree':bool(x['top1_agree']),'p':float(x['conservative_top1_probability']),'gap':float(x['top_score_gap'])})
    gates={
      'ALL_GIRLS':lambda e:True,
      'GIRLS_TOP1_AGREE':lambda e:e['agree'],
      'GIRLS_CONF40':lambda e:e['p']>=.40,
      'GIRLS_AGREE_CONF40':lambda e:e['agree'] and e['p']>=.40,
      'GIRLS_TOP1_P_GE50':lambda e:e['p']>=.50,
      'GIRLS_TOP1_P_GE60':lambda e:e['p']>=.60,
      'GIRLS_GAP_GE3':lambda e:e['gap']>=3,
      'GIRLS_GAP_GE5':lambda e:e['gap']>=5,
    }
    results={}
    for name,fn in gates.items():
        sub=[e for e in es if fn(e)]
        half=len(sub)//2
        results[name]={'overall':score(sub),'first_half':score(sub[:half]),'second_half':score(sub[half:])}
    blocks=[]
    for i in range(0,len(es),40):
        b=score(es[i:i+40]);b['block_index']=i//40+1;blocks.append(b)
    out={'record':'KEIRIN_NEXTGEN5000_GIRLS_3RENTAN_1PT_COARSE_AUDIT_v1','status':'POST_OUTCOME_BURNED_DIAGNOSTIC_ONLY',
         'gates':results,'chronological_40race_blocks_all_girls':blocks,
         'interpretation_boundary':['Only coarse predefined PRE-known gates are reported.','Any successor candidate must be frozen on untouched races before outcomes.','No odds are used.'],
         'hard_boundaries':{'promotion_authorized':False,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    for k,v in results.items():
        print('GATE',k,'OVERALL',json.dumps(v['overall'],sort_keys=True))
        print('GATE',k,'HALVES',json.dumps({'first':v['first_half'],'second':v['second_half']},sort_keys=True))
    print('BLOCKS',json.dumps(blocks,sort_keys=True))
if __name__=='__main__':main()
