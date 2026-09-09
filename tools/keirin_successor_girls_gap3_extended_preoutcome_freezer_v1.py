#!/usr/bin/env python3
"""Combine the original 5001..9000 PREOUTCOME freeze with the pre-authorized
9001..9201 PRE-only extension, preserving the exact candidate rule.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
EXT_RECORD='KEIRIN_SUCCESSOR_GIRLS_3RENTAN_GAP3_UNTOUCHED_SAMPLE_SIZE_EXTENSION_20260909_v1'
RULE='GIRLS_GAP_GE3_3RENTAN_CONSERVATIVE_TOP123_1PT'

def chkblind(x,label):
    s=x.get('safeguards',{})
    for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']:
        if s.get(k) is not False: raise SystemExit(f'FAIL-CLOSED:{label}:{k}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--extension-spec',required=True);ap.add_argument('--base-freeze',required=True);ap.add_argument('--extension-materialization',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    ex=json.loads(Path(a.extension_spec).read_text());bf=json.loads(Path(a.base_freeze).read_text());xm=json.loads(Path(a.extension_materialization).read_text())
    if ex.get('record')!=EXT_RECORD or ex.get('status')!='FROZEN_BEFORE_ANY_SUCCESSOR_OUTCOME_OR_PAYOUT_ACCESS':raise SystemExit('FAIL-CLOSED:extension_spec')
    if bf.get('record')!='KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_PREOUTCOME_FREEZE_20260909_v1':raise SystemExit('FAIL-CLOSED:base_freeze')
    chkblind(bf,'base');chkblind(xm,'extension')
    races=list(bf['races']);seen={r['race_id'] for r in races}
    for r in xm['races']:
        if r['race_id'] in seen:raise SystemExit(f'FAIL-CLOSED:duplicate:{r["race_id"]}')
        seen.add(r['race_id']);races.append(r)
    races.sort(key=lambda r:(r['race_date'],r['race_id']))
    selected=[]
    for r in races:
        if bool(r['girls']) and float(r['top_score_gap'])>=3.0:
            rank=list(map(int,r['conservative_rank']))
            selected.append({'race_id':r['race_id'],'race_date':r['race_date'],'venue':r['venue'],'race_no':r['race_no'],
              'top_score_gap':float(r['top_score_gap']),'top1_agree':bool(r['top1_agree']),
              'conservative_top1_probability':float(r['conservative_top1_probability']),
              'ticket_3rentan':f'{rank[0]}-{rank[1]}-{rank[2]}','stake_yen':100})
    payload={'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_PREOUTCOME_FREEZE_EXTENDED_20260909_v1',
      'status':'SUCCESSOR_OUTCOME_GATE_READY_AFTER_THIS_FREEZE','rule_id':RULE,'extension_spec_record':EXT_RECORD,
      'base_freeze_record':bf['record'],
      'summary':{'materialized_races':len(races),'base_materialized_races':len(bf['races']),
        'extension_materialized_races':len(xm['races']),'girls_races':sum(bool(r['girls']) for r in races),
        'girls_gap_ge3_races':len(selected),'selected_races':len(selected)},
      'selected':selected,'races':races,
      'safeguards':{'result_accessed':False,'payout_accessed':False,'odds_accessed':False,'model_refit':False,
        'successor_outcome_gate_can_open_after_freeze':True,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('PASS_EXTENDED_FREEZE',json.dumps(payload['summary'],sort_keys=True))
if __name__=='__main__':main()
