#!/usr/bin/env python3
"""Aggregate corrected NEXTGEN5000 CandidateAB PREOUTCOME materializations.

This runs before primary outcome access and produces one immutable selection list.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

QUARANTINE={'8320260327010001'}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    races=[]; seen=set(); inputs=[]; sums=[]
    for p in a.input:
        x=json.loads(Path(p).read_text(encoding='utf-8'))
        s=x.get('safeguards',{})
        must_false=['result_accessed','payout_accessed','odds_accessed','model_refit']
        if any(s.get(k) is not False for k in must_false):
            raise SystemExit(f'FAIL-CLOSED:nonblind_or_refit:{p}:{s}')
        inputs.append({'path':Path(p).name,'sha256':sha(p),'record':x.get('record'),'summary':x.get('summary')})
        sums.append(x['summary'])
        for r in x['races']:
            rid=r['race_id']
            if rid in seen: raise SystemExit(f'FAIL-CLOSED:duplicate_race:{rid}')
            seen.add(rid); races.append(r)
    races.sort(key=lambda r:(r['race_date'],r['race_id']))
    selected=[r for r in races if r['selected_by_frozen_rule']]
    selected_primary=[r for r in selected if r['race_id'] not in QUARANTINE]
    payload={
      'record':'KEIRIN_NEXTGEN5000_CANDIDATE_AB_PREOUTCOME_AGGREGATE_FREEZE_20260909_v1',
      'status':'PRIMARY_OUTCOME_GATE_READY_AFTER_THIS_FREEZE',
      'model_freeze':'KEIRIN_CANDIDATE_A_B1A_RECONSTITUTED_V1_REPRODUCTION_FREEZE_20260909_v1',
      'rule_id':'NON_GIRLS_GAP_LT3_CONF40_TOP3_3RENHUKU_1PT_NO_PRICE_FILTER',
      'inputs':inputs,
      'summary':{
        'materialized_races':len(races),
        'rider_rows':sum(r['rider_count'] for r in races),
        'girls_races':sum(r['girls'] for r in races),
        'top1_agreement_races':sum(r['top1_agree'] for r in races),
        'conf40_agreement_races':sum(r['top1_agree'] and r['conservative_top1_probability']>=.40 for r in races),
        'selected_races_all':len(selected),
        'selected_races_primary_after_process_quarantine':len(selected_primary),
        'process_quarantine_count':sum(r['race_id'] in QUARANTINE for r in races)
      },
      'process_quarantine':sorted(QUARANTINE),
      'selected_primary':[{
        'race_id':r['race_id'],'race_date':r['race_date'],'venue':r['venue'],'race_no':r['race_no'],
        'ticket_3renhuku':r['ticket_3renhuku'],
        'conservative_top1_probability':r['conservative_top1_probability'],
        'conservative_ticket_probability':r['conservative_ticket_probability'],
        'top_score_gap':r['top_score_gap']
      } for r in selected_primary],
      'races':races,
      'safeguards':{
        'result_accessed':False,'payout_accessed':False,'odds_accessed':False,
        'model_refit':False,'primary_outcome_gate_can_open_after_freeze':True,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload['summary'],ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
