#!/usr/bin/env python3
"""Economic scorer for pre-frozen NEXTGEN5000 CandidateAB 3renhuku selections.

No odds inputs. Flat 100-yen price-independent settlement only.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

QUARANTINE={'8320260327010001'}
ALLOWED_PAYOUT={'race_id','race_date','winning_3renhuku_ticket','payout_yen_per_100','source_url','source_file_sha256','evidence_role'}

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

def load_payout(paths):
    out={}
    for p in paths:
        with open(p,encoding='utf-8',newline='') as f:
            rd=csv.DictReader(f)
            fields=set(rd.fieldnames or [])
            extra=fields-ALLOWED_PAYOUT
            if extra: raise ValueError(f'FAIL-CLOSED:unexpected_payout_columns:{sorted(extra)}')
            for r in rd:
                rid=r['race_id']
                if rid in out: raise ValueError(f'duplicate payout {rid}')
                out[rid]={
                  'race_id':rid,'race_date':r['race_date'],
                  'winning_3renhuku_ticket':'='.join(map(str,sorted(map(int,r['winning_3renhuku_ticket'].split('='))))),
                  'payout_yen_per_100':int(r['payout_yen_per_100'])
                }
    return out

def max_drawdown(nets):
    equity=0; peak=0; mdd=0
    for x in nets:
        equity+=x
        peak=max(peak,equity)
        mdd=max(mdd,peak-equity)
    return mdd

def segment(rs):
    n=len(rs)
    if not n: return {'bets':0,'status':'NO_BETS'}
    stake=100*n
    ret=sum(r['return_yen'] for r in rs)
    hits=sum(r['hit'] for r in rs)
    wins=sorted((r['return_yen'] for r in rs if r['return_yen']>0),reverse=True)
    largest=wins[0] if wins else 0
    share=largest/ret if ret>0 else None
    if largest>0 and n>1:
        stake_ex=100*(n-1)
        ret_ex=ret-largest
        roi_ex=ret_ex/stake_ex-1 if stake_ex else None
    else:
        roi_ex=None
    roi=ret/stake-1
    status='LOW_POWER' if n<30 else ('CONCENTRATED' if roi>0 and share is not None and share>.50 else 'DESCRIPTIVE_ONLY')
    return {
      'bets':n,'hits':hits,'hit_rate':hits/n,'stake_yen':stake,'return_yen':ret,'net_yen':ret-stake,
      'roi':roi,'maximum_drawdown_yen':max_drawdown([r['return_yen']-100 for r in rs]),
      'largest_single_return_yen':largest,'largest_single_return_share':share,
      'roi_omitting_largest_winning_bet_entirely':roi_ex,'status':status
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prediction',action='append',required=True)
    ap.add_argument('--payout',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    pred=load_preds(a.prediction); pay=load_payout(a.payout)
    selected=[r for r in pred.values() if r['selected_by_frozen_rule'] and r['race_id'] not in QUARANTINE]
    selected.sort(key=lambda r:(r['race_date'],r['race_id']))
    missing=[r['race_id'] for r in selected if r['race_id'] not in pay]
    if missing:
        raise SystemExit(f'FAIL-CLOSED:missing_payout_for_selected count={len(missing)} first={missing[:10]}')
    rows=[]
    for r in selected:
        p=pay[r['race_id']]
        ticket='='.join(map(str,sorted(map(int,r['ticket_3renhuku'].split('=')))))
        hit=ticket==p['winning_3renhuku_ticket']
        rows.append({
          'race_id':r['race_id'],'race_date':r['race_date'],'ticket':ticket,
          'winning_ticket':p['winning_3renhuku_ticket'],'hit':hit,
          'return_yen':p['payout_yen_per_100'] if hit else 0
        })
    mid=len(rows)//2
    payload={
      'record':'KEIRIN_NEXTGEN5000_CANDIDATE_AB_PRICE_INDEPENDENT_ECON_SCORE_v1',
      'status':'FROZEN_SELECTION_FLAT100_NO_ODDS',
      'process_quarantine':sorted(QUARANTINE),
      'overall':segment(rows),'chronological_first_half':segment(rows[:mid]),
      'chronological_second_half':segment(rows[mid:]),
      'bets':rows,
      'safeguards':{
        'odds_accessed':False,'stake_escalation':False,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'formal_support_increment_authorized':False,'model_promotion_authorized':False,
        'profitability_claim_authorized':False,'runtime':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='bets'},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
