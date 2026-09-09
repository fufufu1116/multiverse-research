#!/usr/bin/env python3
"""Score extended untouched GIRLS GAP>=3 3rentan one-point successor."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
FR='KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_PREOUTCOME_FREEZE_EXTENDED_20260909_v1'
EX='KEIRIN_SUCCESSOR_GIRLS_3RENTAN_GAP3_UNTOUCHED_SAMPLE_SIZE_EXTENSION_20260909_v1'

def maxdd(nets):
    eq=peak=m=0
    for x in nets:
        eq+=x;peak=max(peak,eq);m=max(m,peak-eq)
    return m

def metrics(es):
    if not es:return {'bets':0}
    stake=100*len(es);ret=sum(e['ret'] for e in es);hits=sum(e['hit'] for e in es)
    wins=sorted((e['ret'] for e in es if e['ret']>0),reverse=True);largest=wins[0] if wins else 0
    return {'bets':len(es),'hits':hits,'hit_rate':hits/len(es),'stake_yen':stake,'return_yen':ret,
            'net_yen':ret-stake,'recovery_rate':ret/stake,'roi':ret/stake-1,
            'maximum_drawdown_yen':maxdd([e['ret']-100 for e in es]),
            'largest_single_return_yen':largest,'largest_single_return_share':largest/ret if ret else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--payout',required=True);ap.add_argument('--extension-spec',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text());ex=json.loads(Path(a.extension_spec).read_text())
    if fr.get('record')!=FR or ex.get('record')!=EX:raise SystemExit('FAIL-CLOSED:binding')
    if fr.get('extension_spec_record')!=EX:raise SystemExit('FAIL-CLOSED:extension_binding')
    s=fr['safeguards']
    if s['result_accessed'] is not False or s['payout_accessed'] is not False or s['odds_accessed'] is not False:raise SystemExit('FAIL-CLOSED:freeze_not_blind')
    sel={r['race_id']:r for r in fr['selected']};pay={}
    with open(a.payout,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):pay[r['race_id']]=r
    if len(pay)<.98*len(sel):raise SystemExit(f'FAIL-CLOSED:payout_coverage:{len(pay)}/{len(sel)}')
    miss=set(sel)-set(pay);es=[]
    for rid,r in sorted(sel.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        if rid not in pay:continue
        p=pay[rid];hit=r['ticket_3rentan']==p['winning_3rentan_ticket'];ret=int(p['payout_yen_per_100']) if hit else 0
        es.append({'rid':rid,'date':r['race_date'],'hit':int(hit),'ret':ret})
    half=len(es)//2
    overall=metrics(es);first=metrics(es[:half]);second=metrics(es[half:])
    minbets=int(ex['evaluation_unchanged']['minimum_selected_bets_for_primary_decision'])
    sufficient=overall['bets']>=minbets
    primary=sufficient and overall['recovery_rate']>1.0
    robustness=sufficient and first.get('recovery_rate',0)>1.0 and second.get('recovery_rate',0)>1.0 and (overall.get('largest_single_return_share') or 1)<=0.25
    status='SUCCESSOR_REPLICATION_PASS' if primary else ('SUCCESSOR_INSUFFICIENT_SAMPLE' if not sufficient else 'SUCCESSOR_REPLICATION_FAIL')
    out={'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_EXTENDED_SCORE_20260909_v1','status':status,
      'extension_spec_record':EX,'freeze_record':FR,'selected_preoutcome_bets':len(sel),'scored_bets':len(es),'missing_payout_races':sorted(miss),
      'overall':overall,'first_half':first,'second_half':second,'minimum_bets':minbets,'sample_sufficient':sufficient,
      'primary_replication_pass':primary,'robustness_support':robustness,
      'interpretation':['Pre-registered rule and primary threshold were unchanged after burned discovery.',
        '201-position extension was frozen before any successor outcome/payout access and only because the original blind freeze yielded 79 selections versus minimum 80.',
        'No same-sample rescue is authorized after this score.'],
      'hard_boundaries':{'same_sample_rescue_authorized':False,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'profitability_proven':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('PASS_EXTENDED_SCORE',json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
