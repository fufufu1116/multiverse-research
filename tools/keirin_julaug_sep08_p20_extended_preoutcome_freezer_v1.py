#!/usr/bin/env python3
"""Extend the blind Jul-Aug P20 freeze with blind Sep1-8 PRE materializations."""
from __future__ import annotations
import argparse,json
from pathlib import Path
BASE='KEIRIN_JULAUG2026_GIRLS_GAP3_3RENTAN_P20_PREOUTCOME_FREEZE_20260909_v1'
EXT='KEIRIN_JULAUG2026_P20_SAMPLE_SIZE_EXTENSION_SEP01_08_20260909_v1'

def blind(x,label):
    s=x['safeguards']
    for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']:
        if s.get(k) is not False:raise SystemExit(f'FAIL-CLOSED:{label}:{k}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--extension-spec',required=True);ap.add_argument('--base-freeze',required=True);ap.add_argument('--extension-input',action='append',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    ex=json.loads(Path(a.extension_spec).read_text(encoding='utf-8'));bf=json.loads(Path(a.base_freeze).read_text(encoding='utf-8'))
    if ex.get('record')!=EXT or bf.get('record')!=BASE:raise SystemExit('FAIL-CLOSED:binding')
    blind(bf,'base')
    races=list(bf['races']);seen={r['race_id'] for r in races};ext_races=0
    for p in a.extension_input:
        x=json.loads(Path(p).read_text(encoding='utf-8'));blind(x,'extension')
        for r in x['races']:
            if r['race_id'] in seen:raise SystemExit(f'FAIL-CLOSED:duplicate:{r["race_id"]}')
            seen.add(r['race_id']);races.append(r);ext_races+=1
    races.sort(key=lambda r:(r['race_date'],r['race_id']))
    selected=[]
    for r in races:
        if bool(r['girls']) and float(r['top_score_gap'])>=3.0:
            rank=list(map(int,r['conservative_rank']))
            selected.append({'race_id':r['race_id'],'race_date':r['race_date'],'venue':r['venue'],'race_no':r['race_no'],
              'top_score_gap':float(r['top_score_gap']),'ticket_3rentan':f'{rank[0]}-{rank[1]}-{rank[2]}',
              'frozen_exact_order_probability':0.20,'fair_decimal_odds':5.0,'ev10_min_decimal_odds':5.5,'stake_yen':100})
    out={'record':'KEIRIN_JULAUG_SEP08_GIRLS_GAP3_3RENTAN_P20_PREOUTCOME_FREEZE_20260909_v1',
      'status':'EXTENDED_OUTCOME_GATE_READY_AFTER_THIS_FREEZE','extension_spec_record':EXT,'base_freeze_record':BASE,
      'summary':{'materialized_races':len(races),'base_materialized_races':len(bf['races']),'extension_materialized_races':ext_races,
        'girls_races':sum(bool(r['girls']) for r in races),'selected_girls_gap_ge3_races':len(selected)},
      'selected':selected,'races':races,
      'safeguards':{'result_accessed':False,'payout_accessed':False,'odds_accessed':False,'model_refit':False,
        'outcome_gate_can_open_after_freeze':True,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_P20_EXTENDED_FREEZE',json.dumps(out['summary'],sort_keys=True))
if __name__=='__main__':main()
