#!/usr/bin/env python3
"""Score extended untouched GIRLS GAP>=3 3rentan candidate against complete
official settlement sets, including dead heats.
"""
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
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'));ex=json.loads(Path(a.extension_spec).read_text(encoding='utf-8'))
    if fr.get('record')!=FR or ex.get('record')!=EX or fr.get('extension_spec_record')!=EX:raise SystemExit('FAIL-CLOSED:binding')
    s=fr['safeguards']
    if any(s.get(k) is not False for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']):raise SystemExit('FAIL-CLOSED:freeze_not_blind')
    sel={r['race_id']:r for r in fr['selected']}
    pay={}
    with open(a.payout,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            rid=r['race_id']
            if rid in pay:raise SystemExit(f'FAIL-CLOSED:duplicate_payout_race:{rid}')
            ss=json.loads(r['winning_3rentan_settlements_json'])
            if not ss:raise SystemExit(f'FAIL-CLOSED:no_settlements:{rid}')
            pay[rid]=ss
    miss=set(sel)-set(pay)
    if miss:raise SystemExit(f'FAIL-CLOSED:missing_payouts:{len(miss)}:{sorted(miss)[:5]}')
    es=[];multi=0
    for rid,r in sorted(sel.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        ss=pay[rid];multi+=len(ss)>1
        matches=[x for x in ss if x['ticket']==r['ticket_3rentan']]
        if len(matches)>1:raise SystemExit(f'FAIL-CLOSED:duplicate_ticket_settlement:{rid}')
        ret=int(matches[0]['payout_yen_per_100']) if matches else 0
        es.append({'rid':rid,'date':r['race_date'],'hit':int(bool(matches)),'ret':ret,'official_settlement_count':len(ss)})
    half=len(es)//2
    overall=metrics(es);first=metrics(es[:half]);second=metrics(es[half:])
    minbets=int(ex['evaluation_unchanged']['minimum_selected_bets_for_primary_decision'])
    sufficient=overall['bets']>=minbets
    primary=sufficient and overall['recovery_rate']>1.0
    robustness=sufficient and first.get('recovery_rate',0)>1.0 and second.get('recovery_rate',0)>1.0 and (overall.get('largest_single_return_share') or 1)<=0.25
    status='SUCCESSOR_REPLICATION_PASS' if primary else ('SUCCESSOR_INSUFFICIENT_SAMPLE' if not sufficient else 'SUCCESSOR_REPLICATION_FAIL')
    out={'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_COMPLETE_SETTLEMENT_SCORE_20260909_v1','status':status,
      'extension_spec_record':EX,'freeze_record':FR,'selected_preoutcome_bets':len(sel),'scored_bets':len(es),
      'multiple_official_settlement_races':multi,'overall':overall,'first_half':first,'second_half':second,
      'minimum_bets':minbets,'sample_sufficient':sufficient,'primary_replication_pass':primary,'robustness_support':robustness,
      'interpretation':['Exact frozen ticket matched against all official winning 3rentan settlements; dead-heat alternatives are handled without changing selection.',
        'Primary pass threshold remains >=80 bets and recovery_rate > 1.0.','No same-sample rescue is authorized.'],
      'hard_boundaries':{'same_sample_rescue_authorized':False,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'profitability_proven':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('FINAL_VERDICT',status)
    print('FINAL_OVERALL',json.dumps(overall,sort_keys=True))
    print('FINAL_FIRST_HALF',json.dumps(first,sort_keys=True))
    print('FINAL_SECOND_HALF',json.dumps(second,sort_keys=True))
    print('PRIMARY_PASS',primary)
    print('ROBUSTNESS_SUPPORT',robustness)
if __name__=='__main__':main()
