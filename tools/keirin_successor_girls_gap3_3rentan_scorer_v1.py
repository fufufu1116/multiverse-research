#!/usr/bin/env python3
"""Score the frozen successor GIRLS GAP>=3 3rentan one-point candidate."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

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
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--payout',required=True);ap.add_argument('--prespec',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'));ps=json.loads(Path(a.prespec).read_text(encoding='utf-8'))
    if fr.get('prespec_record')!=ps.get('record'):raise SystemExit('FAIL-CLOSED:prespec_binding')
    sel={r['race_id']:r for r in fr['selected']}
    pay={}
    with open(a.payout,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):pay[r['race_id']]=r
    miss=set(sel)-set(pay)
    if len(pay)<.98*len(sel):raise SystemExit(f'FAIL-CLOSED:payout_coverage:{len(pay)}/{len(sel)}')
    es=[]
    for rid,r in sorted(sel.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        if rid not in pay:continue
        p=pay[rid];hit=r['ticket_3rentan']==p['winning_3rentan_ticket'];ret=int(p['payout_yen_per_100']) if hit else 0
        es.append({'rid':rid,'date':r['race_date'],'hit':int(hit),'ret':ret})
    n=len(es);half=n//2
    overall=metrics(es);first=metrics(es[:half]);second=metrics(es[half:])
    ev=ps['evaluation'];minbets=int(ev['minimum_selected_bets_for_primary_decision'])
    primary=(overall['bets']>=minbets and overall['recovery_rate']>1.0)
    robustness=(first.get('recovery_rate',0)>1.0 and second.get('recovery_rate',0)>1.0 and (overall.get('largest_single_return_share') or 1)<=0.25)
    out={'record':'KEIRIN_SUCCESSOR_GIRLS_GAP3_3RENTAN_SCORE_20260909_v1',
         'status':'SUCCESSOR_REPLICATION_PASS' if primary else 'SUCCESSOR_REPLICATION_FAIL',
         'prespec_record':ps['record'],'freeze_record':fr['record'],
         'selected_preoutcome_bets':len(sel),'scored_bets':n,'missing_payout_races':sorted(miss),
         'overall':overall,'first_half':first,'second_half':second,
         'primary_replication_pass':primary,'robustness_support':robustness,
         'interpretation':[
           'This is the pre-registered untouched successor test; no same-sample threshold rescue is permitted.',
           'Primary pass requires >=80 selected bets and recovery_rate > 1.0.',
           'Robustness support additionally requires both chronological halves >1.0 and largest single return share <=25%.'
         ],
         'hard_boundaries':{'same_sample_rescue_authorized':False,'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,'profitability_proven':False,'runtime':False}}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_SCORE',json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
