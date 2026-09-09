#!/usr/bin/env python3
"""Score frozen NEXTGEN5000 S0 PRE materializations against isolated outcomes.

Designed before NEXTGEN5000 outcome access. No payout/odds inputs are accepted.
"""
from __future__ import annotations
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path

def load_materializations(paths):
    out={}
    for p in paths:
        x=json.loads(Path(p).read_text(encoding='utf-8'))
        s=x.get('safeguards',{})
        if s.get('result_accessed') is not False or s.get('payout_accessed') is not False:
            raise ValueError(f'FAIL-CLOSED:materialization_not_blind:{p}')
        for r in x['races']:
            if r['race_id'] in out: raise ValueError(f"duplicate race {r['race_id']}")
            out[r['race_id']]=r
    return out

def load_outcomes(paths):
    out={}
    allowed={'race_id','race_date','venue','race_no','finish_1','finish_2','finish_3','source_url','source_file_sha256','evidence_role'}
    for p in paths:
        with open(p,encoding='utf-8',newline='') as f:
            rd=csv.DictReader(f)
            fields=set(rd.fieldnames or [])
            if not fields<=allowed: raise ValueError(f'FAIL-CLOSED:unexpected_outcome_columns:{sorted(fields-allowed)}')
            for r in rd:
                rid=r['race_id']
                if rid in out: raise ValueError(f'duplicate outcome {rid}')
                out[rid]={
                  'race_id':rid,'race_date':r['race_date'],
                  'finish_1':int(r['finish_1']),'finish_2':int(r['finish_2']),'finish_3':int(r['finish_3'])
                }
    return out

def gap_bin(g):
    g=float(g)
    if g<1: return '<1'
    if g<3: return '1-3'
    if g<5: return '3-5'
    return '>=5'

def acc(rows,key):
    return sum(bool(r[key]) for r in rows)/len(rows) if rows else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--materialization',action='append',required=True)
    ap.add_argument('--outcome',action='append',required=True)
    ap.add_argument('--selection-freeze',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    mats=load_materializations(a.materialization)
    outs=load_outcomes(a.outcome)
    freeze=json.loads(Path(a.selection_freeze).read_text(encoding='utf-8'))
    if freeze['safeguards']['result_accessed'] is not False or freeze['safeguards']['payout_accessed'] is not False:
        raise SystemExit('FAIL-CLOSED:selection_freeze_not_blind')
    selected_ids={r['race_id'] for r in freeze.get('selected_races',[])}
    common=sorted(set(mats)&set(outs),key=lambda rid:(mats[rid]['race_date'],rid))
    scored=[]
    for rid in common:
        m=mats[rid]; o=outs[rid]
        f=[o['finish_1'],o['finish_2'],o['finish_3']]
        top3=list(map(int,m['s0_top3_cars']))
        riders={int(r['car_no']):float(r['s0_probability']) for r in m['riders']}
        pwin=riders.get(o['finish_1'])
        if pwin is None: continue
        scored.append({
          'race_id':rid,'race_date':m['race_date'],'girls':bool(m['girls']),'top_score_gap':float(m['top_score_gap']),
          'top1_hit':int(m['s0_top1_car'])==o['finish_1'],
          'winner_in_top3':o['finish_1'] in top3,
          'exact_top3_set_hit':set(top3)==set(f),
          'selected':rid in selected_ids,
          'selected_hit':(rid in selected_ids) and set(top3)==set(f),
          'winner_probability':pwin,
          'logloss':-math.log(max(pwin,1e-15))
        })
    if len(scored)<1000: raise SystemExit(f'FAIL-CLOSED:too_few_common_scored:{len(scored)}')
    groups={}
    groups['ALL']=scored
    groups['GIRLS']=[r for r in scored if r['girls']]
    groups['NON_GIRLS']=[r for r in scored if not r['girls']]
    for g in ('<1','1-3','3-5','>=5'):
        groups['GAP_'+g]=[r for r in scored if gap_bin(r['top_score_gap'])==g]
    summary={}
    for k,rs in groups.items():
        sel=[r for r in rs if r['selected']]
        summary[k]={
          'races':len(rs),
          'top1_hit_rate':acc(rs,'top1_hit'),
          'winner_in_top3_rate':acc(rs,'winner_in_top3'),
          'exact_top3_set_hit_rate':acc(rs,'exact_top3_set_hit'),
          'mean_winner_logloss':sum(r['logloss'] for r in rs)/len(rs) if rs else None,
          'selected_races':len(sel),
          'selected_ticket_hit_rate':acc(sel,'selected_hit')
        }
    blocks=[]
    for i in range(0,len(scored),250):
        rs=scored[i:i+250]; sel=[r for r in rs if r['selected']]
        blocks.append({
          'block_index':i//250+1,'start_key':[rs[0]['race_date'],rs[0]['race_id']],
          'end_key':[rs[-1]['race_date'],rs[-1]['race_id']],'races':len(rs),
          'top1_hit_rate':acc(rs,'top1_hit'),'winner_in_top3_rate':acc(rs,'winner_in_top3'),
          'exact_top3_set_hit_rate':acc(rs,'exact_top3_set_hit'),
          'selected_races':len(sel),'selected_ticket_hit_rate':acc(sel,'selected_hit')
        })
    payload={
      'record':'KEIRIN_NEXTGEN5000_S0_OUTCOME_SCORE_v1',
      'status':'SPORTING_SCORE_ONLY_NO_PAYOUT_ECONOMICS',
      'common_scored_races':len(scored),
      'pre_materialization_races':len(mats),'outcome_rows':len(outs),
      'selection_freeze_record':freeze['record'],
      'chosen_rule':freeze.get('chosen_rule'),
      'metrics':summary,'chronological_250race_blocks':blocks,
      'safeguards':{
        'payout_accessed':False,'odds_accessed':False,'DEV2000_C_scoring_count':0,
        'ECON_HOLDOUT1000_opened':False,'formal_support_increment_authorized':False,
        'model_promotion_authorized':False,'profitability_claim_authorized':False,'runtime':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'common_scored_races':len(scored),'ALL':summary['ALL'],'chosen_rule':freeze.get('chosen_rule')},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
