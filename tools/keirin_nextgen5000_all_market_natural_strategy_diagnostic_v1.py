#!/usr/bin/env python3
"""Post-outcome burned all-market strategy diagnostic for NEXTGEN5000.

Natural, finite market mappings only. This does not promote a strategy on the
same sample; it is hypothesis discovery for a later untouched universe.
"""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path

QUARANTINE={'8320260327010001'}
STRATEGIES=[
 '2SHAHUKU_TOP12_1PT',
 '2SHATAN_TOP1_TOP2_1PT',
 'WIDE_TOP12_1PT',
 'WIDE_TOP13_1PT',
 'WIDE_TOP12_TOP13_2PT',
 '3RENHUKU_TOP123_1PT',
 '3RENTAN_TOP1_TOP2_TOP3_1PT',
]

def canon_unordered(cars):
    return '='.join(map(str,sorted(map(int,cars))))

def ticket_map(r):
    rank=list(map(int,r['conservative_rank']))
    a,b,c=rank[:3]
    return {
      '2SHAHUKU_TOP12_1PT':[('2shahuku',canon_unordered([a,b]))],
      '2SHATAN_TOP1_TOP2_1PT':[('2shatan',f'{a}-{b}')],
      'WIDE_TOP12_1PT':[('wide',canon_unordered([a,b]))],
      'WIDE_TOP13_1PT':[('wide',canon_unordered([a,c]))],
      'WIDE_TOP12_TOP13_2PT':[('wide',canon_unordered([a,b])),('wide',canon_unordered([a,c]))],
      '3RENHUKU_TOP123_1PT':[('3renhuku',canon_unordered([a,b,c]))],
      '3RENTAN_TOP1_TOP2_TOP3_1PT':[('3rentan',f'{a}-{b}-{c}')],
    }

def load_prediction(path):
    x=json.loads(Path(path).read_text(encoding='utf-8'))
    s=x.get('safeguards',{})
    if s.get('result_accessed') is not False or s.get('payout_accessed') is not False or s.get('odds_accessed') is not False:
        raise ValueError('FAIL-CLOSED:prediction_not_preoutcome')
    return {r['race_id']:r for r in x['races'] if r['race_id'] not in QUARANTINE}

def load_payout(paths):
    d=defaultdict(dict)
    for p in paths:
        with open(p,encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                rid=r['race_id']; m=r['market']; t=r['winning_ticket']
                if m=='wide':
                    d[rid].setdefault(m,{})[t]=int(r['payout_yen_per_100'])
                else:
                    if m in d[rid]: raise ValueError(f'duplicate market {rid} {m}')
                    d[rid][m]={t:int(r['payout_yen_per_100'])}
    return d

def gap_bin(g):
    g=float(g)
    if g<1:return '<1'
    if g<3:return '1-3'
    if g<5:return '3-5'
    return '>=5'

def max_drawdown(nets):
    eq=peak=mdd=0
    for x in nets:
        eq+=x; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    return mdd

def score_entries(entries):
    if not entries:return {'races':0,'tickets':0}
    tickets=sum(e['ticket_count'] for e in entries)
    stake=100*tickets
    ret=sum(e['return_yen'] for e in entries)
    hit_races=sum(e['return_yen']>0 for e in entries)
    wins=sorted((e['return_yen'] for e in entries if e['return_yen']>0),reverse=True)
    largest=wins[0] if wins else 0
    return {
      'races':len(entries),'tickets':tickets,
      'hit_races':hit_races,'hit_race_rate':hit_races/len(entries),
      'stake_yen':stake,'return_yen':ret,'net_yen':ret-stake,'roi':ret/stake-1,
      'maximum_drawdown_yen':max_drawdown([e['return_yen']-100*e['ticket_count'] for e in entries]),
      'largest_race_return_yen':largest,
      'largest_race_return_share':largest/ret if ret else None
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prediction',required=True)
    ap.add_argument('--payout',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    pred=load_prediction(a.prediction); pay=load_payout(a.payout)

    regimes={
      'ALL':lambda r:True,
      'GIRLS':lambda r:bool(r['girls']),
      'NON_GIRLS':lambda r:not bool(r['girls']),
      'AGREE_CONF40':lambda r:bool(r['top1_agree']) and float(r['conservative_top1_probability'])>=.40,
      'NON_GIRLS_AGREE_CONF40':lambda r:(not bool(r['girls'])) and bool(r['top1_agree']) and float(r['conservative_top1_probability'])>=.40,
      'GAP_LT1':lambda r:float(r['top_score_gap'])<1,
      'GAP_1_3':lambda r:1<=float(r['top_score_gap'])<3,
      'GAP_3_5':lambda r:3<=float(r['top_score_gap'])<5,
      'GAP_GE5':lambda r:float(r['top_score_gap'])>=5,
      'NON_GIRLS_GAP_LT3_AGREE_CONF40':lambda r:(not bool(r['girls'])) and float(r['top_score_gap'])<3 and bool(r['top1_agree']) and float(r['conservative_top1_probability'])>=.40,
    }

    entries={s:[] for s in STRATEGIES}
    missing={}
    for rid,r in sorted(pred.items(),key=lambda kv:(kv[1]['race_date'],kv[0])):
        if rid not in pay:
            missing[rid]='no_payout_record'; continue
        tmap=ticket_map(r)
        for s,tickets in tmap.items():
            ret=0; valid=True
            for market,ticket in tickets:
                market_map=pay[rid].get(market)
                if market_map is None:
                    valid=False; break
                ret += market_map.get(ticket,0)
            if not valid: continue
            entries[s].append({
              'race_id':rid,'race_date':r['race_date'],'girls':bool(r['girls']),
              'top1_agree':bool(r['top1_agree']),'top1_p':float(r['conservative_top1_probability']),
              'gap':float(r['top_score_gap']),'gap_bin':gap_bin(r['top_score_gap']),
              'ticket_count':len(tickets),'return_yen':ret,
              'tickets':[{'market':m,'ticket':t} for m,t in tickets]
            })

    result={}
    for s,es in entries.items():
        by_regime={}
        for name,fn in regimes.items():
            subset=[e for e in es if fn({
              'girls':e['girls'],'top1_agree':e['top1_agree'],
              'conservative_top1_probability':e['top1_p'],'top_score_gap':e['gap']
            })]
            by_regime[name]=score_entries(subset)
        # chronological 250-race blocks on all available entries
        blocks=[]
        for i in range(0,len(es),250):
            b=score_entries(es[i:i+250]); b['block_index']=i//250+1; blocks.append(b)
        result[s]={'regimes':by_regime,'chronological_250race_blocks':blocks}

    payload={
      'record':'KEIRIN_NEXTGEN5000_ALL_MARKET_NATURAL_STRATEGY_DIAGNOSTIC_v1',
      'status':'POST_OUTCOME_BURNED_DIAGNOSTIC_ONLY_NO_PROMOTION',
      'prediction_races':len(pred),'payout_races':len(pay),'missing_prediction_payout_races':len(missing),
      'strategies':result,
      'interpretation_boundary':[
        'All results are post-outcome burned diagnostics on NEXTGEN5000 positions 2001..5000.',
        'No strategy may be promoted from this sample.',
        'Any promising strategy must be frozen before outcomes on a successor untouched historical universe.',
        'No odds values are used; this compares natural market mappings and settlement only.'
      ],
      'hard_boundaries':{
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'model_refit':False,'runtime':False,'profitability_claim_authorized':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    for s in STRATEGIES:
        print(s,'ALL',json.dumps(result[s]['regimes']['ALL'],sort_keys=True))
        print(s,'CONF40',json.dumps(result[s]['regimes']['NON_GIRLS_AGREE_CONF40'],sort_keys=True))
        print(s,'FROZEN3F',json.dumps(result[s]['regimes']['NON_GIRLS_GAP_LT3_AGREE_CONF40'],sort_keys=True))

if __name__=='__main__':
    main()
