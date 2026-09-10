#!/usr/bin/env python3
"""Fail-closed final ECON_HOLDOUT1000 validator for frozen B1a_MKT50_v1 lineage.

This validator does not discover or fetch holdout data. It only evaluates a supplied, pre-bound
holdout input after separate authorization. It imports the already-frozen candidate transform and
final economic selector, and contains no tuning parameters.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from b1a_mkt50_v1 import FailClosed, market_shape_from_decimal_odds, transform_race_market
from b1a_mkt50_final_economic_selector_v1 import (
    select_single, START_BANKROLL, COMPETITION_THRESHOLD, SUPPORTED_MARKETS
)

EPS=1e-15
MIN_HITS_FOR_ECON=20
MIN_BET_RACES=50
MAX_DRAWDOWN=0.35
MAX_SINGLE_RETURN_SHARE=0.50
TAIL_ODDS_FLOOR=300.0

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def load_rows(p:Path):
    rows=[]
    with p.open('r',encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            if not line.strip(): continue
            try:r=json.loads(line)
            except Exception as e: raise FailClosed(f'line {i}: invalid JSON') from e
            if not isinstance(r,dict): raise FailClosed(f'line {i}: non-object')
            rows.append(r)
    if len(rows)!=1000: raise FailClosed(f'holdout rows={len(rows)} expected=1000')
    return rows

def norm(d):
    if not isinstance(d,dict) or not d: raise FailClosed('empty probability distribution')
    out={str(k):float(v) for k,v in d.items()}
    if any((not math.isfinite(v) or v<0) for v in out.values()): raise FailClosed('invalid probability')
    z=sum(out.values())
    if z<=0 or not math.isfinite(z): raise FailClosed('invalid probability total')
    return {k:v/z for k,v in out.items()}

def winner_mass(d,winners):
    x=sum(d.get(str(t),0.0) for t in winners)
    if x<=0: raise FailClosed('winner mass <=0')
    return x

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True)
    a=ap.parse_args(); ip=Path(a.input); rows=load_rows(ip)
    seen=set(); raw_ll=[]; new_ll=[]; tail_raw=tail_new=0.0; tail_obs=0
    bankroll=START_BANKROLL; peak=bankroll; min_bank=bankroll; max_dd=0.0
    total_stake=total_return=bet_races=hit_tickets=0; max_positive_return=0
    for i,r in enumerate(rows,1):
        rid=str(r.get('race_id','')).strip()
        if not rid or rid in seen: raise FailClosed(f'row {i}: blank/duplicate race_id')
        seen.add(rid)
        score=float(r.get('competition_score'))
        if not math.isfinite(score): raise FailClosed(f'{rid}: invalid competition_score')
        markets=r.get('markets')
        if not isinstance(markets,dict): raise FailClosed(f'{rid}: markets missing')
        winning=r.get('winning_tickets_by_market')
        payout=r.get('settlements_yen_per_100')
        if not isinstance(winning,dict) or not isinstance(payout,dict): raise FailClosed(f'{rid}: outcome fields missing')
        selector_input={}
        for market in SUPPORTED_MARKETS:
            mr=markets.get(market)
            if mr is None: continue
            model=norm(mr.get('b1a_ticket_probability') or {})
            odds={str(k):float(v) for k,v in (mr.get('decimal_odds') or {}).items()}
            mshape=market_shape_from_decimal_odds(odds)
            if set(model)!=set(mshape): raise FailClosed(f'{rid}/{market}: universe mismatch')
            q=transform_race_market(market,model,mshape)
            winners=[str(x) for x in (winning.get(market) or [])]
            if not winners or not set(winners).issubset(model): raise FailClosed(f'{rid}/{market}: invalid winning tickets')
            raw_ll.append(-math.log(max(winner_mass(model,winners),EPS)))
            new_ll.append(-math.log(max(winner_mass(q,winners),EPS)))
            for t,o in odds.items():
                if o>=TAIL_ODDS_FLOOR:
                    tail_raw += model[t]; tail_new += q[t]
                    if t in winners: tail_obs += 1
            selector_input[market]={'b1a_ticket_probability':model,'decimal_odds':odds}
        chosen=select_single(selector_input,score,bankroll)
        if chosen is None: continue
        bet_races += 1
        stake=int(chosen['stake_yen']); market=chosen['market']; ticket=chosen['ticket']
        if stake>bankroll: raise FailClosed(f'{rid}: stake exceeds bankroll')
        pay=int((payout.get(market) or {}).get(ticket,0))
        ret=pay*(stake//100) if pay>0 else 0
        if ret>0: hit_tickets += 1; max_positive_return=max(max_positive_return,ret)
        total_stake += stake; total_return += ret
        bankroll = bankroll-stake+ret
        if bankroll<0: raise FailClosed(f'{rid}: negative bankroll')
        peak=max(peak,bankroll); min_bank=min(min_bank,bankroll)
        if peak>0: max_dd=max(max_dd,(peak-bankroll)/peak)
    if len(raw_ll)==0 or len(new_ll)==0: raise FailClosed('no supported market rows')
    raw_mean=sum(raw_ll)/len(raw_ll); new_mean=sum(new_ll)/len(new_ll)
    primary='PASS' if new_mean<raw_mean else 'FAIL'
    if tail_obs==0:
        tail='INCONCLUSIVE'; raw_err=new_err=None
    else:
        raw_err=abs(math.log((tail_obs+EPS)/(tail_raw+EPS))); new_err=abs(math.log((tail_obs+EPS)/(tail_new+EPS)))
        tail='PASS' if new_err<raw_err else 'FAIL'
    roi=(total_return-total_stake)/total_stake if total_stake>0 else None
    concentration=max_positive_return/total_return if total_return>0 else None
    if hit_tickets<MIN_HITS_FOR_ECON:
        econ='INCONCLUSIVE'
    else:
        econ='PASS' if (roi is not None and roi>=0 and bet_races>=MIN_BET_RACES and max_dd<=MAX_DRAWDOWN and (concentration is None or concentration<=MAX_SINGLE_RETURN_SHARE)) else 'FAIL'
    promotion=(primary=='PASS' and tail=='PASS' and econ=='PASS')
    out={
      'record':'KEIRIN_B1A_MKT50_ECON_HOLDOUT1000_VALIDATION_v1',
      'input_sha256':sha256_file(ip), 'races':len(rows), 'candidate':'B1a_MKT50_v1',
      'rules':{'competition_score_threshold':COMPETITION_THRESHOLD,'markets':list(SUPPORTED_MARKETS),'tail_odds_floor':TAIL_ODDS_FLOOR,'minimum_hits_for_economic_gate':MIN_HITS_FOR_ECON,'minimum_bet_races':MIN_BET_RACES,'maximum_drawdown':MAX_DRAWDOWN,'maximum_single_return_share':MAX_SINGLE_RETURN_SHARE},
      'calibration':{'raw_b1a_log_loss':raw_mean,'b1a_mkt50_log_loss':new_mean,'primary_gate':primary,'tail_observed_hits':tail_obs,'tail_expected_raw':tail_raw,'tail_expected_candidate':tail_new,'tail_log_error_raw':raw_err,'tail_log_error_candidate':new_err,'tail_gate':tail},
      'economic':{'bet_races':bet_races,'hit_tickets':hit_tickets,'total_stake_yen':total_stake,'total_return_yen':total_return,'roi':roi,'ending_bankroll_yen':bankroll,'minimum_bankroll_yen':min_bank,'maximum_drawdown':max_dd,'largest_positive_return_share':concentration,'economic_gate':econ},
      'promotion_pass':promotion,
      'retuned_after_holdout_open':False
    }
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS_EVALUATOR_EXECUTED','promotion_pass':promotion,'output':a.output},ensure_ascii=False))
if __name__=='__main__': main()
