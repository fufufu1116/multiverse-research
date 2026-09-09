#!/usr/bin/env python3
"""Prespecified sporting scorer for frozen Candidate_A/B1a NEXTGEN5000 predictions.

Accepts only outcome-label CSVs and PREOUTCOME materialization JSONs.
No payout/odds input exists in this interface.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

ALLOWED_OUTCOME={'race_id','race_date','venue','race_no','finish_1','finish_2','finish_3','source_url','source_file_sha256','evidence_role'}

def load_preds(paths):
    out={}
    for p in paths:
        x=json.loads(Path(p).read_text(encoding='utf-8'))
        s=x.get('safeguards',{})
        if s.get('result_accessed') is not False or s.get('payout_accessed') is not False or s.get('odds_accessed') is not False:
            raise ValueError(f'FAIL-CLOSED:prediction_not_blind:{p}')
        for r in x['races']:
            if r['race_id'] in out: raise ValueError(f"duplicate prediction {r['race_id']}")
            out[r['race_id']]=r
    return out

def load_outcomes(paths):
    out={}
    for p in paths:
        with open(p,encoding='utf-8',newline='') as f:
            rd=csv.DictReader(f)
            fields=set(rd.fieldnames or [])
            extra=fields-ALLOWED_OUTCOME
            if extra: raise ValueError(f'FAIL-CLOSED:unexpected_outcome_columns:{sorted(extra)}')
            for r in rd:
                rid=r['race_id']
                if rid in out: raise ValueError(f'duplicate outcome {rid}')
                out[rid]={'race_id':rid,'race_date':r['race_date'],
                          'finish_1':int(r['finish_1']),'finish_2':int(r['finish_2']),'finish_3':int(r['finish_3'])}
    return out

def gap_bin(g):
    if g<1: return '<1'
    if g<3: return '1-3'
    if g<5: return '3-5'
    return '>=5'

def summarize(rs):
    if not rs:
        return {'races':0}
    def mean(k): return sum(float(r[k]) for r in rs)/len(rs)
    sel=[r for r in rs if r['selected']]
    return {
      'races':len(rs),
      'candidate_a_top1_hit_rate':mean('a_top1_hit'),
      'b1a_top1_hit_rate':mean('b_top1_hit'),
      'model_top1_agreement_rate':mean('top1_agree'),
      'agreed_top1_hit_rate':(
        sum(r['consensus_top1_hit'] for r in rs if r['top1_agree']) /
        sum(r['top1_agree'] for r in rs)
      ) if sum(r['top1_agree'] for r in rs) else None,
      'consensus_winner_in_top3_rate':mean('winner_in_top3'),
      'consensus_exact_top3_set_hit_rate':mean('exact_top3_hit'),
      'candidate_a_mean_logloss':mean('a_logloss'),
      'b1a_mean_logloss':mean('b_logloss'),
      'candidate_a_mean_multiclass_brier':mean('a_brier'),
      'b1a_mean_multiclass_brier':mean('b_brier'),
      'selected_races':len(sel),
      'selected_ticket_hit_rate':(
        sum(r['selected_hit'] for r in sel)/len(sel)
      ) if sel else None
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prediction',action='append',required=True)
    ap.add_argument('--outcome',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    pred=load_preds(a.prediction); outc=load_outcomes(a.outcome)
    common=sorted(set(pred)&set(outc),key=lambda rid:(pred[rid]['race_date'],rid))
    rows=[]
    for rid in common:
        p=pred[rid]; o=outc[rid]; winner=o['finish_1']
        rr={int(x['car_no']):x for x in p['riders']}
        if winner not in rr: continue
        pa={c:float(x['candidate_a_win_probability']) for c,x in rr.items()}
        pb={c:float(x['b1a_win_probability']) for c,x in rr.items()}
        top3=set(map(int,p['conservative_top3_cars']))
        actual3={o['finish_1'],o['finish_2'],o['finish_3']}
        ya={c:float(c==winner) for c in rr}
        rows.append({
          'race_id':rid,'race_date':p['race_date'],'girls':bool(p['girls']),
          'gap':float(p['top_score_gap']),
          'a_top1_hit':int(p['candidate_a_top1_car'])==winner,
          'b_top1_hit':int(p['b1a_top1_car'])==winner,
          'top1_agree':bool(p['top1_agree']),
          'consensus_top1_hit':int(p['conservative_top1_car'])==winner,
          'winner_in_top3':winner in top3,
          'exact_top3_hit':top3==actual3,
          'selected':bool(p['selected_by_frozen_rule']),
          'selected_hit':bool(p['selected_by_frozen_rule']) and top3==actual3,
          'a_logloss':-math.log(max(pa[winner],1e-15)),
          'b_logloss':-math.log(max(pb[winner],1e-15)),
          'a_brier':sum((pa[c]-ya[c])**2 for c in rr),
          'b_brier':sum((pb[c]-ya[c])**2 for c in rr)
        })
    if len(rows)<1000: raise SystemExit(f'FAIL-CLOSED:too_few_common={len(rows)}')

    groups={
      'ALL':rows,
      'GIRLS':[r for r in rows if r['girls']],
      'NON_GIRLS':[r for r in rows if not r['girls']],
    }
    for g in ('<1','1-3','3-5','>=5'):
        groups['GAP_'+g]=[r for r in rows if gap_bin(r['gap'])==g]

    blocks=[]
    for i in range(0,len(rows),250):
        rs=rows[i:i+250]
        s=summarize(rs)
        s.update({'block_index':i//250+1,'start_key':[rs[0]['race_date'],rs[0]['race_id']],
                  'end_key':[rs[-1]['race_date'],rs[-1]['race_id']]})
        blocks.append(s)

    payload={
      'record':'KEIRIN_NEXTGEN5000_CANDIDATE_AB_SPORTING_SCORE_v1',
      'status':'SPORTING_SCORE_ONLY_NO_PAYOUT_OR_ODDS',
      'common_scored_races':len(rows),'prediction_races':len(pred),'outcome_races':len(outc),
      'metrics':{k:summarize(v) for k,v in groups.items()},
      'chronological_250race_blocks':blocks,
      'safeguards':{
        'payout_accessed':False,'odds_accessed':False,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,
        'profitability_claim_authorized':False,'runtime':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'common_scored_races':len(rows),'ALL':payload['metrics']['ALL']},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
