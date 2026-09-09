#!/usr/bin/env python3
"""Post-result calibration diagnostic for the failed frozen GIRLS GAP>=3 3rentan candidate.

Separates exact-order sporting probability from payout economics. No odds and no
same-sample rule changes are allowed.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

def exact_order(pmap,a,b,c):
    pa=pmap[a]
    d2=1-pa
    d3=1-pa-pmap[b]
    if d2<=0 or d3<=0:raise ValueError('bad PL denominator')
    return pa*(pmap[b]/d2)*(pmap[c]/d3)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--payout',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'))
    races={r['race_id']:r for r in fr['races']}
    selected={r['race_id']:r for r in fr['selected']}
    settlements={}
    with open(a.payout,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):settlements[r['race_id']]=json.loads(r['winning_3rentan_settlements_json'])
    rows=[]
    for rid,s in sorted(selected.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        r=races[rid];ticket=s['ticket_3rentan'];a1,a2,a3=map(int,ticket.split('-'))
        pa={int(x['car_no']):float(x['candidate_a_win_probability']) for x in r['riders']}
        pb={int(x['car_no']):float(x['b1a_win_probability']) for x in r['riders']}
        pA=exact_order(pa,a1,a2,a3);pB=exact_order(pb,a1,a2,a3);pc=min(pA,pB)
        ss=settlements[rid];match=[x for x in ss if x['ticket']==ticket]
        hit=int(bool(match));payout=int(match[0]['payout_yen_per_100']) if match else 0
        rows.append({'race_id':rid,'race_date':s['race_date'],'ticket':ticket,'pA':pA,'pB':pB,'p':pc,'hit':hit,'payout':payout,
                     'fair_decimal_odds':1/pc,'ev10_min_decimal_odds':1.10/pc})
    n=len(rows);obs=sum(x['hit'] for x in rows)/n;mp=sum(x['p'] for x in rows)/n
    brier=sum((x['p']-x['hit'])**2 for x in rows)/n
    ll=sum(-(x['hit']*math.log(max(x['p'],1e-15))+(1-x['hit'])*math.log(max(1-x['p'],1e-15))) for x in rows)/n
    expected=sum(x['p'] for x in rows)
    # fixed quartiles by predicted probability, descriptive only
    sr=sorted(rows,key=lambda x:(x['p'],x['race_id']));qs=[]
    for q in range(4):
        sub=sr[(n*q)//4:(n*(q+1))//4]
        qs.append({'quartile':q+1,'n':len(sub),'min_p':sub[0]['p'],'max_p':sub[-1]['p'],
                   'mean_p':sum(x['p'] for x in sub)/len(sub),'observed_hit_rate':sum(x['hit'] for x in sub)/len(sub)})
    out={'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_EXACT_ORDER_CALIBRATION_DIAGNOSTIC_v1',
      'status':'POST_RESULT_DIAGNOSTIC_ONLY_NO_RESCUE','n':n,'observed_hits':sum(x['hit'] for x in rows),
      'observed_hit_rate':obs,'mean_predicted_exact_order_probability':mp,'expected_hits_sum_probability':expected,
      'observed_to_predicted_ratio':obs/mp if mp else None,'brier':brier,'logloss':ll,'probability_quartiles':qs,
      'fair_price_summary':{
        'mean_fair_decimal_odds':sum(x['fair_decimal_odds'] for x in rows)/n,
        'median_fair_decimal_odds':sorted(x['fair_decimal_odds'] for x in rows)[n//2],
        'mean_ev10_min_decimal_odds':sum(x['ev10_min_decimal_odds'] for x in rows)/n
      },
      'interpretation_boundary':['No historical odds are used.','This audit cannot prove a price gate; it only checks whether exact-order probability itself collapsed.',
        'Any new purchase rule must be frozen on a separate untouched universe.'],
      'rows':rows,
      'hard_boundaries':{'same_sample_rescue_authorized':False,'model_refit':False,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('CALIBRATION',json.dumps({k:out[k] for k in ['n','observed_hits','observed_hit_rate','mean_predicted_exact_order_probability','expected_hits_sum_probability','observed_to_predicted_ratio','brier','logloss','fair_price_summary']},sort_keys=True))
    print('QUARTILES',json.dumps(qs,sort_keys=True))
if __name__=='__main__':main()
