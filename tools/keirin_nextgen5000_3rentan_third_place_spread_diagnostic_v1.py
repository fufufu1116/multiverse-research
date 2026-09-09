#!/usr/bin/env python3
"""Burned diagnostic: 3rentan third-place-only spread + position dispersion.

Uses PRE-frozen conservative ranking and post-freeze winning 3rentan payout only.
No odds, no model refit, no promotion on this sample.
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path

QUARANTINE={'8320260327010001'}
SPREAD_DEPTHS=[1,2,3,4,5]  # number of predicted 3rd-place candidates, starting rank3

def max_drawdown(nets):
    eq=peak=mdd=0
    for x in nets:
        eq+=x; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    return mdd

def score(entries):
    if not entries:
        return {'races':0,'tickets':0}
    tickets=sum(e['ticket_count'] for e in entries)
    stake=100*tickets
    ret=sum(e['return_yen'] for e in entries)
    hits=sum(e['hit'] for e in entries)
    wins=sorted((e['return_yen'] for e in entries if e['return_yen']>0),reverse=True)
    largest=wins[0] if wins else 0
    return {
      'races':len(entries),'tickets':tickets,'avg_points_per_race':tickets/len(entries),
      'hit_races':hits,'hit_race_rate':hits/len(entries),
      'stake_yen':stake,'return_yen':ret,'net_yen':ret-stake,'roi':ret/stake-1,
      'recovery_rate':ret/stake,
      'maximum_drawdown_yen':max_drawdown([e['return_yen']-100*e['ticket_count'] for e in entries]),
      'largest_race_return_yen':largest,
      'largest_race_return_share':largest/ret if ret else None,
    }

def regime_ok(name,r):
    if name=='ALL': return True
    if name=='AGREE_CONF40': return r['top1_agree'] and r['top1_p']>=.40
    if name=='NON_GIRLS_AGREE_CONF40': return (not r['girls']) and r['top1_agree'] and r['top1_p']>=.40
    if name=='FROZEN3F': return (not r['girls']) and r['gap']<3 and r['top1_agree'] and r['top1_p']>=.40
    if name=='STRONG_HEAD_GAP_GE3': return r['gap']>=3 and r['top1_agree']
    if name=='VERY_STRONG_HEAD_GAP_GE5': return r['gap']>=5 and r['top1_agree']
    raise KeyError(name)

REGIMES=['ALL','AGREE_CONF40','NON_GIRLS_AGREE_CONF40','FROZEN3F','STRONG_HEAD_GAP_GE3','VERY_STRONG_HEAD_GAP_GE5']

def parse_win_ticket(t):
    a,b,c=map(int,t.split('-'))
    return a,b,c

def load_predictions(path):
    x=json.loads(Path(path).read_text(encoding='utf-8'))
    s=x.get('safeguards',{})
    if s.get('result_accessed') is not False or s.get('payout_accessed') is not False or s.get('odds_accessed') is not False:
        raise ValueError('FAIL-CLOSED:prediction_not_preoutcome')
    return {r['race_id']:r for r in x['races'] if r['race_id'] not in QUARANTINE}

def load_3rentan(paths):
    d={}
    for p in paths:
        with open(p,encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r['market']!='3rentan': continue
                rid=r['race_id']
                if rid in d: raise ValueError(f'duplicate 3rentan {rid}')
                d[rid]={'ticket':r['winning_ticket'],'payout':int(r['payout_yen_per_100']),'date':r['race_date']}
    return d

def rank_hist_to_json(c):
    return {str(k):c[k] for k in sorted(c)}

def cumulative_rank_coverage(c,max_rank=9):
    n=sum(c.values())
    out=[]
    for k in range(1,max_rank+1):
        covered=sum(v for r,v in c.items() if r<=k)
        out.append({'rank_le':k,'count':covered,'rate':covered/n if n else None})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prediction',required=True)
    ap.add_argument('--payout',action='append',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    pred=load_predictions(a.prediction); pay=load_3rentan(a.payout)
    common=sorted(set(pred)&set(pay), key=lambda rid:(pred[rid]['race_date'],rid))

    entries={d:[] for d in SPREAD_DEPTHS}
    h1=Counter(); h2=Counter(); h3=Counter()
    h2_winner_rank1=Counter(); h3_winner_rank1=Counter()
    h3_winner1_second2=Counter()
    conditional_n={'winner_rank1':0,'winner_rank1_second_rank2':0}

    for rid in common:
        r=pred[rid]; rank=list(map(int,r['conservative_rank']))
        inv={car:i+1 for i,car in enumerate(rank)}
        f1,f2,f3=parse_win_ticket(pay[rid]['ticket'])
        if f1 not in inv or f2 not in inv or f3 not in inv:
            continue
        rr1,rr2,rr3=inv[f1],inv[f2],inv[f3]
        h1[rr1]+=1; h2[rr2]+=1; h3[rr3]+=1
        if rr1==1:
            conditional_n['winner_rank1']+=1
            h2_winner_rank1[rr2]+=1; h3_winner_rank1[rr3]+=1
            if rr2==2:
                conditional_n['winner_rank1_second_rank2']+=1
                h3_winner1_second2[rr3]+=1

        meta={'girls':bool(r['girls']),'top1_agree':bool(r['top1_agree']),
              'top1_p':float(r['conservative_top1_probability']),'gap':float(r['top_score_gap'])}
        for d in SPREAD_DEPTHS:
            third_candidates=rank[2:2+d]
            tickets=[f"{rank[0]}-{rank[1]}-{c}" for c in third_candidates if c not in {rank[0],rank[1]}]
            hit=pay[rid]['ticket'] in tickets
            entries[d].append({
              'race_id':rid,'race_date':r['race_date'],**meta,
              'ticket_count':len(tickets),'hit':int(hit),
              'return_yen':pay[rid]['payout'] if hit else 0
            })

    strategies={}
    for d in SPREAD_DEPTHS:
        by={}
        for rg in REGIMES:
            sub=[e for e in entries[d] if regime_ok(rg,e)]
            by[rg]=score(sub)
        blocks=[]
        es=entries[d]
        for i in range(0,len(es),250):
            b=score(es[i:i+250]); b['block_index']=i//250+1; blocks.append(b)
        strategies[f'TOP1_TOP2_THIRD_RANK3_TO_{2+d}']={'third_candidates':d,'regimes':by,'chronological_250race_blocks':blocks}

    payload={
      'record':'KEIRIN_NEXTGEN5000_3RENTAN_THIRD_PLACE_SPREAD_DIAGNOSTIC_v1',
      'status':'POST_OUTCOME_BURNED_DIAGNOSTIC_ONLY_NO_PROMOTION',
      'races_scored':len(common),
      'position_dispersion':{
        'actual_finish1_predicted_rank_histogram':rank_hist_to_json(h1),
        'actual_finish2_predicted_rank_histogram':rank_hist_to_json(h2),
        'actual_finish3_predicted_rank_histogram':rank_hist_to_json(h3),
        'conditional_on_actual_winner_predicted_rank1':{
          'n':conditional_n['winner_rank1'],
          'actual_finish2_predicted_rank_histogram':rank_hist_to_json(h2_winner_rank1),
          'actual_finish3_predicted_rank_histogram':rank_hist_to_json(h3_winner_rank1),
          'finish2_cumulative_rank_coverage':cumulative_rank_coverage(h2_winner_rank1),
          'finish3_cumulative_rank_coverage':cumulative_rank_coverage(h3_winner_rank1),
        },
        'conditional_on_actual_winner_rank1_and_actual_second_rank2':{
          'n':conditional_n['winner_rank1_second_rank2'],
          'actual_finish3_predicted_rank_histogram':rank_hist_to_json(h3_winner1_second2),
          'finish3_cumulative_rank_coverage':cumulative_rank_coverage(h3_winner1_second2),
        }
      },
      'third_place_only_spread_strategies':strategies,
      'interpretation_boundary':[
        'This directly tests the owner hypothesis that third place is more dispersed.',
        'Only third-place breadth changes; predicted first and second remain fixed.',
        'No odds are used. A larger hit rate does not imply a profitable strategy.',
        'This sample is burned after outcome access. Any candidate must be frozen on a later untouched universe before promotion.'
      ],
      'hard_boundaries':{
        'DEV2000_C_scoring_count':0,'ECON_HOLDOUT1000_opened':False,
        'model_refit':False,'selection_promotion_authorized':False,'runtime':False
      }
    }
    Path(a.out).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('POSITION_COND_WINNER1_SECOND',json.dumps(payload['position_dispersion']['conditional_on_actual_winner_predicted_rank1'],sort_keys=True))
    print('POSITION_COND_WINNER1_SECOND2_THIRD',json.dumps(payload['position_dispersion']['conditional_on_actual_winner_rank1_and_actual_second_rank2'],sort_keys=True))
    for k,v in strategies.items():
        for rg in ['ALL','FROZEN3F','STRONG_HEAD_GAP_GE3','VERY_STRONG_HEAD_GAP_GE5']:
            print('SPREAD',k,rg,json.dumps(v['regimes'][rg],sort_keys=True))

if __name__=='__main__':
    main()
