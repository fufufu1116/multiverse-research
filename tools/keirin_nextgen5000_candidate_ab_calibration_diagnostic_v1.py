#!/usr/bin/env python3
"""Diagnostic calibration audit for burned NEXTGEN5000 CandidateAB predictions.

This is post-outcome diagnostic only. It does not alter the frozen rule on the
same sample. Outputs ticket-probability and top1-confidence calibration tables
to design a NEW lineage for a later untouched sample.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

FIXED_BINS=[0.0,.05,.10,.15,.20,.25,.30,.40,.50,.65,1.0000001]

def fixed_bin(p):
    for lo,hi in zip(FIXED_BINS[:-1],FIXED_BINS[1:]):
        if lo<=p<hi: return (lo,hi)
    raise ValueError(p)

def summarize(rs, pkey, ykey):
    if not rs: return None
    n=len(rs); pred=sum(r[pkey] for r in rs)/n; obs=sum(r[ykey] for r in rs)/n
    return {
      'n':n,'mean_predicted_probability':pred,'observed_rate':obs,
      'observed_to_predicted_ratio':obs/pred if pred>0 else None,
      'bias_observed_minus_predicted':obs-pred,
      'brier_binary':sum((r[pkey]-r[ykey])**2 for r in rs)/n,
      'logloss_binary':sum(-(r[ykey]*math.log(max(r[pkey],1e-15))+(1-r[ykey])*math.log(max(1-r[pkey],1e-15))) for r in rs)/n
    }

def table(rs,pkey,ykey):
    out=[]
    for lo,hi in zip(FIXED_BINS[:-1],FIXED_BINS[1:]):
        sub=[r for r in rs if lo<=r[pkey]<hi]
        s=summarize(sub,pkey,ykey)
        if s: out.append({'lo':lo,'hi':hi,**s})
    return out

def quantile_table(rs,pkey,ykey,k=10):
    ss=sorted(rs,key=lambda r:(r[pkey],r['race_id']))
    out=[]
    for q in range(k):
        a=(len(ss)*q)//k; b=(len(ss)*(q+1))//k
        sub=ss[a:b]
        if sub:
            s=summarize(sub,pkey,ykey)
            out.append({'quantile':q+1,'min_probability':sub[0][pkey],'max_probability':sub[-1][pkey],**s})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prediction',required=True)
    ap.add_argument('--outcome',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    p=json.loads(Path(a.prediction).read_text(encoding='utf-8'))
    if p['safeguards']['result_accessed'] is not False:
        raise SystemExit('FAIL-CLOSED:prediction_not_preoutcome')
    pred={r['race_id']:r for r in p['races']}
    out={}
    with open(a.outcome,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            out[r['race_id']]={int(r['finish_1']),int(r['finish_2']),int(r['finish_3'])}
    common=sorted(set(pred)&set(out),key=lambda rid:(pred[rid]['race_date'],rid))
    rs=[]
    for rid in common:
        r=pred[rid]; actual=out[rid]
        top3=set(map(int,r['conservative_top3_cars']))
        top1=int(r['conservative_top1_car'])
        rs.append({
          'race_id':rid,
          'girls':bool(r['girls']),
          'selected':bool(r['selected_by_frozen_rule']),
          'ticket_hit':float(top3==actual),
          'ticket_p_conservative':float(r['conservative_ticket_probability']),
          'ticket_p_candidate_a':float(r['candidate_a_ticket_probability']),
          'ticket_p_b1a':float(r['b1a_ticket_probability']),
          'top1_hit':float(top1 in actual and top1==next(iter([int(x) for x in [0] if False]),-999)), # overwritten below
          'top1_p':float(r['conservative_top1_probability']),
          'top1_car':top1
        })
    # Need ordered finish1 separately.
    finish1={}
    with open(a.outcome,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f): finish1[r['race_id']]=int(r['finish_1'])
    for r in rs: r['top1_hit']=float(r['top1_car']==finish1[r['race_id']])

    selected=[r for r in rs if r['selected']]
    non_girls=[r for r in rs if not r['girls']]
    payload={
      'record':'KEIRIN_NEXTGEN5000_CANDIDATE_AB_CALIBRATION_DIAGNOSTIC_v1',
      'status':'POST_OUTCOME_BURNED_DIAGNOSTIC_NEW_LINEAGE_INPUT_ONLY',
      'races':len(rs),'selected_races':len(selected),
      'ticket_calibration_all':{
        'overall':summarize(rs,'ticket_p_conservative','ticket_hit'),
        'fixed_bins':table(rs,'ticket_p_conservative','ticket_hit'),
        'deciles':quantile_table(rs,'ticket_p_conservative','ticket_hit')
      },
      'ticket_calibration_non_girls':{
        'overall':summarize(non_girls,'ticket_p_conservative','ticket_hit'),
        'fixed_bins':table(non_girls,'ticket_p_conservative','ticket_hit')
      },
      'ticket_calibration_frozen_selected':{
        'overall':summarize(selected,'ticket_p_conservative','ticket_hit'),
        'fixed_bins':table(selected,'ticket_p_conservative','ticket_hit'),
        'deciles':quantile_table(selected,'ticket_p_conservative','ticket_hit',5)
      },
      'top1_calibration_all':{
        'overall':summarize(rs,'top1_p','top1_hit'),
        'fixed_bins':table(rs,'top1_p','top1_hit'),
        'deciles':quantile_table(rs,'top1_p','top1_hit')
      },
      'interpretation_boundary':[
        'No threshold/model change on NEXTGEN5000 positions 2001..5000 is authorized from this diagnostic.',
        'Any calibration mapping derived from this artifact is a new candidate and must be frozen before outcomes on a later untouched sample.',
        'No historical odds are used in this calibration diagnostic.'
      ]
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('TICKET_SELECTED',json.dumps(payload['ticket_calibration_frozen_selected']['overall'],sort_keys=True))
    print('TICKET_ALL',json.dumps(payload['ticket_calibration_all']['overall'],sort_keys=True))
    print('TOP1_ALL',json.dumps(payload['top1_calibration_all']['overall'],sort_keys=True))

if __name__=='__main__':
    main()
