#!/usr/bin/env python3
"""Aggregate Jul-Aug outcome-blind CandidateAB materializations and freeze the
pre-registered GIRLS GAP>=3 3rentan P20 calibration candidate.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
PRESPEC='KEIRIN_JULAUG2026_GIRLS_GAP3_3RENTAN_P20_CALIBRATION_PRESPEC_20260909_v1'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prespec',required=True);ap.add_argument('--input',action='append',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    ps=json.loads(Path(a.prespec).read_text(encoding='utf-8'))
    if ps.get('record')!=PRESPEC or ps.get('status')!='FROZEN_BEFORE_JULAUG_OUTCOME_OR_PAYOUT_ACCESS':raise SystemExit('FAIL-CLOSED:prespec')
    r=ps['frozen_rule'];pm=ps['frozen_probability_model']
    if not (r['girls_only'] and r['top_score_gap_min_inclusive']==3.0 and r['market']=='3rentan' and r['points']==1):raise SystemExit('FAIL-CLOSED:rule')
    if pm['exact_order_probability']!=0.20 or pm['ev10_min_decimal_odds']!=5.5:raise SystemExit('FAIL-CLOSED:p20')
    races=[];seen=set();inputs=[]
    for p in a.input:
        x=json.loads(Path(p).read_text(encoding='utf-8'));s=x['safeguards']
        if any(s.get(k) is not False for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']):raise SystemExit(f'FAIL-CLOSED:not_blind:{p}')
        inputs.append({'path':Path(p).name,'sha256':sha(p),'summary':x['summary']})
        for rr in x['races']:
            if rr['race_id'] in seen:raise SystemExit(f'FAIL-CLOSED:duplicate:{rr["race_id"]}')
            seen.add(rr['race_id']);races.append(rr)
    races.sort(key=lambda x:(x['race_date'],x['race_id']))
    selected=[]
    for rr in races:
        if bool(rr['girls']) and float(rr['top_score_gap'])>=3.0:
            rank=list(map(int,rr['conservative_rank']))
            selected.append({'race_id':rr['race_id'],'race_date':rr['race_date'],'venue':rr['venue'],'race_no':rr['race_no'],
              'top_score_gap':float(rr['top_score_gap']),'ticket_3rentan':f'{rank[0]}-{rank[1]}-{rank[2]}',
              'frozen_exact_order_probability':0.20,'fair_decimal_odds':5.0,'ev10_min_decimal_odds':5.5,'stake_yen':100})
    out={'record':'KEIRIN_JULAUG2026_GIRLS_GAP3_3RENTAN_P20_PREOUTCOME_FREEZE_20260909_v1',
      'status':'JULAUG_OUTCOME_GATE_READY_AFTER_THIS_FREEZE','prespec_record':PRESPEC,
      'summary':{'materialized_races':len(races),'rider_rows':sum(x['rider_count'] for x in races),'girls_races':sum(bool(x['girls']) for x in races),
        'selected_girls_gap_ge3_races':len(selected)},
      'inputs':inputs,'selected':selected,'races':races,
      'safeguards':{'result_accessed':False,'payout_accessed':False,'odds_accessed':False,'model_refit':False,
        'julaug_outcome_gate_can_open_after_freeze':True,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('PASS_JULAUG_P20_FREEZE',json.dumps(out['summary'],sort_keys=True))
if __name__=='__main__':main()
