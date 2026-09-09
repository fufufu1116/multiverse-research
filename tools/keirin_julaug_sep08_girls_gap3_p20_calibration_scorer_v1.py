#!/usr/bin/env python3
"""Score P20 calibration candidate on the blind JulAug+Sep extension."""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
P=0.20

def wilson(k,n,z=1.959963984540054):
    if n==0:return (None,None)
    ph=k/n;d=1+z*z/n
    c=(ph+z*z/(2*n))/d
    h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return c-h,c+h

def maxdd(nets):
    eq=peak=m=0
    for x in nets:
        eq+=x;peak=max(peak,eq);m=max(m,peak-eq)
    return m

def metrics(es):
    if not es:return {'bets':0}
    stake=100*len(es);ret=sum(e['ret'] for e in es);hits=sum(e['hit'] for e in es);lo,hi=wilson(hits,len(es))
    wins=sorted((e['ret'] for e in es if e['ret']>0),reverse=True);largest=wins[0] if wins else 0
    return {'bets':len(es),'hits':hits,'hit_rate':hits/len(es),'wilson95_low':lo,'wilson95_high':hi,
      'absolute_error_vs_p20':abs(hits/len(es)-P),'stake_yen':stake,'return_yen':ret,'net_yen':ret-stake,
      'recovery_rate':ret/stake,'roi':ret/stake-1,'maximum_drawdown_yen':maxdd([e['ret']-100 for e in es]),
      'largest_single_return_yen':largest,'largest_single_return_share':largest/ret if ret else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--payout',required=True);ap.add_argument('--prespec',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'));ps=json.loads(Path(a.prespec).read_text(encoding='utf-8'));s=fr['safeguards']
    if any(s.get(k) is not False for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']):raise SystemExit('FAIL-CLOSED:freeze_not_blind')
    if ps['frozen_probability_model']['exact_order_probability']!=P:raise SystemExit('FAIL-CLOSED:p20')
    sel={r['race_id']:r for r in fr['selected']};pay={}
    with open(a.payout,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['race_id'] in pay:raise SystemExit('duplicate payout race')
            pay[r['race_id']]=json.loads(r['winning_3rentan_settlements_json'])
    miss=set(sel)-set(pay)
    if miss:raise SystemExit(f'FAIL-CLOSED:missing:{len(miss)}')
    es=[]
    for rid,r in sorted(sel.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        matches=[x for x in pay[rid] if x['ticket']==r['ticket_3rentan']]
        if len(matches)>1:raise SystemExit('duplicate matching settlement')
        ret=int(matches[0]['payout_yen_per_100']) if matches else 0
        es.append({'race_id':rid,'race_date':r['race_date'],'hit':int(bool(matches)),'ret':ret})
    half=len(es)//2;overall=metrics(es);first=metrics(es[:half]);second=metrics(es[half:])
    min_n=int(ps['evaluation']['minimum_selected_races']);sufficient=overall['bets']>=min_n
    primary=sufficient and overall['wilson95_low']<=P<=overall['wilson95_high']
    secondary=sufficient and overall['absolute_error_vs_p20']<=float(ps['evaluation']['secondary_absolute_error_max'])
    status='P20_CALIBRATION_PASS' if primary else ('INSUFFICIENT_SAMPLE' if not sufficient else 'P20_CALIBRATION_FAIL')
    out={'record':'KEIRIN_JULAUG_SEP08_GIRLS_GAP3_3RENTAN_P20_CALIBRATION_SCORE_20260909_v1','status':status,
      'prespec_record':ps['record'],'freeze_record':fr['record'],'frozen_probability':P,'frozen_ev10_min_decimal_odds':5.5,
      'overall':overall,'first_half':first,'second_half':second,'minimum_selected_races':min_n,'sample_sufficient':sufficient,
      'primary_calibration_pass':primary,'secondary_abs_error_pass':secondary,
      'economic_interpretation':'Flat100 recovery is descriptive only because timestamped PRE odds were not used.',
      'live_gate_interpretation':'If calibration passes, 5.5x is the pre-registered nominal +10% EV minimum for this regime, subject to actual current PRE odds and further prospective evidence.',
      'hard_boundaries':{'profitability_proven':False,'historical_final_odds_used_as_pre_odds':False,'same_sample_recalibration_authorized':False,
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('P20_VERDICT',status);print('P20_OVERALL',json.dumps(overall,sort_keys=True));print('P20_FIRST',json.dumps(first,sort_keys=True));print('P20_SECOND',json.dumps(second,sort_keys=True))
    print('P20_PRIMARY_PASS',primary);print('P20_SECONDARY_PASS',secondary)
if __name__=='__main__':main()
