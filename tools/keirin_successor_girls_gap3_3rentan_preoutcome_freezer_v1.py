#!/usr/bin/env python3
"""Aggregate successor CandidateAB PREOUTCOME materializations and freeze the
pre-registered GIRLS + score-gap>=3 3rentan top1-top2-top3 one-point rule.

Must run before any successor outcome/payout access.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

PRESPEC_RECORD='KEIRIN_SUCCESSOR_GIRLS_3RENTAN_GAP3_UNTOUCHED_PRESPEC_20260909_v1'
RULE_ID='GIRLS_GAP_GE3_3RENTAN_CONSERVATIVE_TOP123_1PT'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prespec',required=True)
    ap.add_argument('--input',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    ps=json.loads(Path(a.prespec).read_text(encoding='utf-8'))
    if ps.get('record')!=PRESPEC_RECORD or ps.get('status')!='FROZEN_BEFORE_SUCCESSOR_PRE_AND_OUTCOME_ACCESS':
        raise SystemExit('FAIL-CLOSED:prespec_mismatch')
    u=ps['untouched_successor_universe']
    if (u['positions_start'],u['positions_end'],u['requested_positions'])!=(5001,9000,4000):
        raise SystemExit('FAIL-CLOSED:universe_mismatch')
    fr=ps['frozen_candidate_rule']
    if not (fr['girls_only'] is True and fr['top_score_gap_min_inclusive']==3.0 and fr['market']=='3rentan' and fr['points_per_selected_race']==1):
        raise SystemExit('FAIL-CLOSED:rule_mismatch')

    races=[];seen=set();inputs=[]
    for p in a.input:
        x=json.loads(Path(p).read_text(encoding='utf-8'))
        s=x.get('safeguards',{})
        for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']:
            if s.get(k) is not False: raise SystemExit(f'FAIL-CLOSED:{k}:{p}')
        inputs.append({'path':Path(p).name,'sha256':sha(p),'record':x.get('record'),'summary':x.get('summary')})
        for r in x['races']:
            rid=r['race_id']
            if rid in seen: raise SystemExit(f'FAIL-CLOSED:duplicate:{rid}')
            seen.add(rid);races.append(r)
    races.sort(key=lambda r:(r['race_date'],r['race_id']))
    selected=[]
    for r in races:
        if bool(r['girls']) and float(r['top_score_gap'])>=3.0:
            rank=list(map(int,r['conservative_rank']))
            selected.append({
              'race_id':r['race_id'],'race_date':r['race_date'],'venue':r['venue'],'race_no':r['race_no'],
              'top_score_gap':float(r['top_score_gap']),'top1_agree':bool(r['top1_agree']),
              'conservative_top1_probability':float(r['conservative_top1_probability']),
              'ticket_3rentan':f'{rank[0]}-{rank[1]}-{rank[2]}',
              'stake_yen':100
            })
    payload={
      'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_PREOUTCOME_FREEZE_20260909_v1',
      'status':'SUCCESSOR_OUTCOME_GATE_READY_AFTER_THIS_FREEZE',
      'prespec_record':PRESPEC_RECORD,'rule_id':RULE_ID,'inputs':inputs,
      'summary':{
        'materialized_races':len(races),'rider_rows':sum(r['rider_count'] for r in races),
        'girls_races':sum(bool(r['girls']) for r in races),
        'girls_gap_ge3_races':len(selected),'selected_races':len(selected)
      },
      'selected':selected,'races':races,
      'safeguards':{
        'result_accessed':False,'payout_accessed':False,'odds_accessed':False,'model_refit':False,
        'successor_outcome_gate_can_open_after_freeze':True,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False
      }
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_FREEZE',json.dumps(payload['summary'],sort_keys=True))
if __name__=='__main__':main()
