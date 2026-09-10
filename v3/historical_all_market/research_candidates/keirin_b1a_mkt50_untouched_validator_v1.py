#!/usr/bin/env python3
"""Untouched-validation evaluator for frozen B1a_MKT50_v1."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from b1a_mkt50_v1 import MODEL_NAME, SUPPORTED_MARKETS, FailClosed, market_shape_from_decimal_odds, transform_race_market

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def load_jsonl(p: Path):
    rows=[]
    with p.open("r",encoding="utf-8") as f:
        for i,line in enumerate(f,1):
            if not line.strip(): continue
            try: r=json.loads(line)
            except Exception as e: raise FailClosed(f"line {i}: invalid JSON") from e
            if not isinstance(r,dict): raise FailClosed(f"line {i}: non-object")
            rows.append(r)
    if not rows: raise FailClosed("empty validation input")
    return rows

def _norm(d):
    z=sum(float(v) for v in d.values())
    if z<=0 or not math.isfinite(z): raise FailClosed("invalid probability total")
    return {str(k):float(v)/z for k,v in d.items()}

def winner_mass(dist, winners):
    s=sum(dist.get(str(w),0.0) for w in winners)
    if s<=0: raise FailClosed("winner probability mass <= 0")
    return s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output",required=True)
    a=ap.parse_args(); ip=Path(a.input); rows=load_jsonl(ip)
    log_raw=[]; log_new=[]; tail_pred_raw=0.0; tail_pred_new=0.0; tail_obs=0
    selected_count=0; gross=0.0; max_win=0.0; stake=0.0; realized_hits=0; seen=set()
    for i,r in enumerate(rows,1):
        rid=str(r.get("race_id","")); market=str(r.get("market",""))
        if not rid or market not in SUPPORTED_MARKETS: raise FailClosed(f"row {i}: invalid race_id/market")
        key=(rid,market)
        if key in seen: raise FailClosed(f"duplicate race+market {key}")
        seen.add(key)
        model=_norm(r.get("b1a_ticket_probability") or {}); odds=r.get("decimal_odds") or {}
        market_shape=market_shape_from_decimal_odds(odds)
        if set(model)!=set(market_shape): raise FailClosed(f"{key}: ticket universe mismatch")
        cand=transform_race_market(market,model,market_shape)
        winners=[str(x) for x in (r.get("winning_tickets") or [])]
        if not winners or not set(winners).issubset(model): raise FailClosed(f"{key}: invalid winners")
        log_raw.append(-math.log(winner_mass(model,winners))); log_new.append(-math.log(winner_mass(cand,winners)))
        for t,o in odds.items():
            if float(o)>=300.0:
                tail_pred_raw += model[str(t)]; tail_pred_new += cand[str(t)]
                if str(t) in winners: tail_obs += 1
        selected=[str(x) for x in (r.get("selected_tickets") or [])]
        returns={str(k):float(v) for k,v in (r.get("realized_return_yen_by_ticket") or {}).items()}
        stakes={str(k):float(v) for k,v in (r.get("stake_yen_by_ticket") or {}).items()}
        for t in selected:
            if t not in model: raise FailClosed(f"{key}: selected ticket absent {t}")
            selected_count += 1; rv=returns.get(t,0.0); sv=stakes.get(t,0.0)
            if rv>0: realized_hits+=1
            gross += rv; stake += sv; max_win=max(max_win,rv)
    raw_ll=sum(log_raw)/len(log_raw); new_ll=sum(log_new)/len(log_new); primary="PASS" if new_ll<raw_ll else "FAIL"
    if tail_obs==0:
        tail_gate="INCONCLUSIVE"; raw_tail_err=new_tail_err=None
    else:
        eps=1e-15; raw_tail_err=abs(math.log((tail_obs+eps)/(tail_pred_raw+eps))); new_tail_err=abs(math.log((tail_obs+eps)/(tail_pred_new+eps))); tail_gate="PASS" if new_tail_err<raw_tail_err else "FAIL"
    concentration=(max_win/gross) if gross>0 else None; roi=((gross-stake)/stake) if stake>0 else None; econ="INCONCLUSIVE"
    if realized_hits>=20 and roi is not None: econ="PASS" if roi>=0 else "FAIL"
    promotion=(primary=="PASS" and tail_gate=="PASS" and (concentration is None or concentration<=0.50) and econ=="PASS")
    out={"record":"KEIRIN_B1A_MKT50_UNTOUCHED_VALIDATION_v1","candidate":MODEL_NAME,"input_sha256":sha256_file(ip),"race_market_rows":len(rows),"calibration":{"raw_b1a_ticket_log_loss":raw_ll,"b1a_mkt50_ticket_log_loss":new_ll,"primary_gate":primary,"tail_odds_floor":300.0,"tail_observed_winning_tickets":tail_obs,"tail_expected_raw":tail_pred_raw,"tail_expected_candidate":tail_pred_new,"tail_log_calibration_error_raw":raw_tail_err,"tail_log_calibration_error_candidate":new_tail_err,"tail_gate":tail_gate},"economic_secondary":{"selected_ticket_count":selected_count,"realized_hits":realized_hits,"stake_yen":stake,"gross_return_yen":gross,"roi":roi,"largest_positive_return_share":concentration,"economic_gate":econ},"promotion_pass":promotion,"rules":{"pool_weight_model":0.5,"pool_weight_market":0.5,"competition_score_threshold":0.4,"roi_cannot_rescue_calibration":True,"single_win_over_50pct_blocks_promotion":True}}
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS_EVALUATOR_EXECUTED","promotion_pass":promotion,"output":a.output},ensure_ascii=False))
if __name__=="__main__": main()
