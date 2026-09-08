#!/usr/bin/env python3
"""Deterministic low-DOF Rider x Circumference fitter v1.

Implements the frozen research proposal:
  z_i = beta * competition_score_i + q_c * delta_r
with beta fixed at S0, q=+1 for 333/333.33m and q=-1 for 400m,
winner negative log likelihood + lambda * sum(delta_r^2),
lambda grid {1,4,16,64}, and leave-one-LOCAL_DAY1_RACE_DATE-out CV.

CRITICAL FIREWALL:
Authorization is validated before the outcome-bearing race payload is touched.
This implementation may exist before RESULT access is allowed, but real fitting
must fail closed until support/calendar/formula/membership/result gates are true.

No venue terms, no beta refit, no odds/payout/prediction/comment features.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

S0_BETA=0.22260435254784533
LAMBDA_GRID=(1.0,4.0,16.0,64.0)
FORMULA_ID="S0_PLUS_SHRUNK_RIDER_X_CIRCUMFERENCE_OFFSET_v1"
CALENDAR_DEF="LOCAL_DAY1_RACE_DATE"
FORBIDDEN_ASCII={
    "result","results","outcome","outcomes","payout","payouts","odds",
    "prediction","predictions","forecast","forecasts","comment","comments",
    "finish","finishing","rank","ranking"
}
FORBIDDEN_JP=("結果","払戻","オッズ","予想","コメント","着順")
ALLOWED_TARGET_FIELDS={"winner_registration"}


class LowDofFitError(ValueError):
    pass


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise LowDofFitError(f"{label}_must_be_numeric")
    x=float(value)
    if not math.isfinite(x):
        raise LowDofFitError(f"{label}_must_be_finite")
    return x


def authorization_preflight(auth:Mapping[str,Any])->dict:
    if not isinstance(auth,Mapping):
        raise LowDofFitError("authorization_must_be_mapping")
    required_true=(
        "support_gate_pass",
        "calendar_definition_adopted",
        "formula_frozen",
        "fit_membership_frozen",
        "result_join_authorized",
        "final_untouched_holdout_excluded",
    )
    for key in required_true:
        if auth.get(key) is not True:
            raise LowDofFitError(f"authorization_gate_not_true:{key}")

    if auth.get("formula_id")!=FORMULA_ID:
        raise LowDofFitError("unexpected_formula_id")
    if auth.get("calendar_block_definition")!=CALENDAR_DEF:
        raise LowDofFitError("unexpected_calendar_block_definition")

    beta=_finite(auth.get("s0_beta"),"authorization_s0_beta")
    if abs(beta-S0_BETA)>1e-15:
        raise LowDofFitError("s0_beta_mutation_detected")

    grid=auth.get("lambda_grid")
    if not isinstance(grid,list) or tuple(float(x) for x in grid)!=LAMBDA_GRID:
        raise LowDofFitError("lambda_grid_mutation_detected")

    regs=auth.get("supported_registrations")
    if not isinstance(regs,list) or not regs:
        raise LowDofFitError("supported_registrations_must_be_nonempty_list")
    if any(not isinstance(x,str) or not re.fullmatch(r"\d{6}",x) for x in regs):
        raise LowDofFitError("invalid_supported_registration")
    if len(regs)!=len(set(regs)):
        raise LowDofFitError("duplicate_supported_registration")

    for key in ("formula_hash","fit_membership_hash"):
        value=auth.get(key)
        if not isinstance(value,str) or not re.fullmatch(r"[0-9a-f]{64}",value):
            raise LowDofFitError(f"invalid_{key}")

    return {
        "supported_registrations":tuple(regs),
        "s0_beta":beta,
        "formula_hash":auth["formula_hash"],
        "fit_membership_hash":auth["fit_membership_hash"],
    }


def _assert_clean_keys(obj:Mapping[str,Any],label:str,allow_target=False):
    for key in obj:
        if allow_target and key in ALLOWED_TARGET_FIELDS:
            continue
        raw=str(key)
        tokens={x for x in re.split(r"[^a-z0-9]+",raw.lower()) if x}
        if tokens & FORBIDDEN_ASCII or any(x in raw for x in FORBIDDEN_JP):
            raise LowDofFitError(f"forbidden_post_decision_field:{label}:{raw}")


def _bucket(raw)->tuple[str,float]:
    text=str(raw)
    if text in {"333_OR_333_33","333","333.33"}:
        return "333_OR_333_33",1.0
    if text=="400":
        return "400",-1.0
    try:
        x=float(raw)
    except Exception as exc:
        raise LowDofFitError("unsupported_circumference") from exc
    if abs(x-400)<1e-6:
        return "400",-1.0
    if abs(x-333)<1.0 or abs(x-333.33)<1.0:
        return "333_OR_333_33",1.0
    raise LowDofFitError("unsupported_circumference")


def _normalize_races(races, supported_regs:set[str])->list[dict]:
    if not isinstance(races,list) or len(races)<2:
        raise LowDofFitError("races_must_be_list_with_at_least_two")
    out=[]
    seen_ids=set()
    for ri,raw in enumerate(races):
        if not isinstance(raw,Mapping):
            raise LowDofFitError(f"race_must_be_mapping:{ri}")
        _assert_clean_keys(raw,f"race:{ri}",allow_target=True)

        race_id=raw.get("race_id")
        if not isinstance(race_id,str) or not race_id or race_id in seen_ids:
            raise LowDofFitError(f"invalid_or_duplicate_race_id:{ri}")
        seen_ids.add(race_id)

        race_date=str(raw.get("race_date") or "")
        block=str(raw.get("calendar_block") or "")
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",race_date):
            raise LowDofFitError(f"invalid_race_date:{race_id}")
        if block!=race_date:
            raise LowDofFitError(f"calendar_block_must_equal_local_day1_race_date:{race_id}")

        bucket,q=_bucket(raw.get("circumference_bucket",raw.get("circumference_m")))
        riders=raw.get("riders")
        if not isinstance(riders,list) or not (3<=len(riders)<=9):
            raise LowDofFitError(f"invalid_rider_count:{race_id}")

        seen_cars=set()
        seen_regs=set()
        normalized=[]
        for i,r in enumerate(riders):
            if not isinstance(r,Mapping):
                raise LowDofFitError(f"rider_must_be_mapping:{race_id}:{i}")
            _assert_clean_keys(r,f"rider:{race_id}:{i}")
            car=r.get("car_no")
            if isinstance(car,bool) or not isinstance(car,int) or not (1<=car<=9) or car in seen_cars:
                raise LowDofFitError(f"invalid_or_duplicate_car_no:{race_id}:{i}")
            seen_cars.add(car)
            reg=str(r.get("official_registration_number") or "")
            if not re.fullmatch(r"\d{6}",reg) or reg in seen_regs:
                raise LowDofFitError(f"invalid_or_duplicate_registration:{race_id}:{reg}")
            seen_regs.add(reg)
            score=_finite(r.get("competition_score"),f"competition_score:{race_id}:{reg}")
            if score<=0:
                raise LowDofFitError(f"competition_score_must_be_positive:{race_id}:{reg}")
            normalized.append({
                "car_no":car,
                "official_registration_number":reg,
                "competition_score":score,
                "parameter_active":reg in supported_regs,
            })

        winner=str(raw.get("winner_registration") or "")
        if winner not in seen_regs:
            raise LowDofFitError(f"winner_not_in_race:{race_id}")

        out.append({
            "race_id":race_id,
            "race_date":race_date,
            "calendar_block":block,
            "circumference_bucket":bucket,
            "q":q,
            "winner_registration":winner,
            "riders":normalized,
        })
    if len({x["calendar_block"] for x in out})<2:
        raise LowDofFitError("need_at_least_two_calendar_blocks_for_cv")
    return out


def _logsumexp(values:list[float])->float:
    m=max(values)
    return m+math.log(sum(math.exp(x-m) for x in values))


def _race_loss(race, delta:dict[str,float])->float:
    logits=[]
    winner_logit=None
    for r in race["riders"]:
        d=delta.get(r["official_registration_number"],0.0) if r["parameter_active"] else 0.0
        z=S0_BETA*r["competition_score"]+race["q"]*d
        logits.append(z)
        if r["official_registration_number"]==race["winner_registration"]:
            winner_logit=z
    return _logsumexp(logits)-winner_logit


def _objective(races, params:list[str], values:list[float], lam:float)->float:
    delta=dict(zip(params,values))
    return sum(_race_loss(r,delta) for r in races)+lam*sum(x*x for x in values)


def _grad_hess(races,params,values,lam):
    idx={reg:i for i,reg in enumerate(params)}
    n=len(params)
    g=[2.0*lam*x for x in values]
    h=[[0.0]*n for _ in range(n)]
    for i in range(n):
        h[i][i]=2.0*lam
    delta=dict(zip(params,values))

    for race in races:
        logits=[]
        meta=[]
        for r in race["riders"]:
            reg=r["official_registration_number"]
            d=delta.get(reg,0.0) if r["parameter_active"] else 0.0
            z=S0_BETA*r["competition_score"]+race["q"]*d
            logits.append(z)
            meta.append(reg if r["parameter_active"] and reg in idx else None)
        m=max(logits)
        exps=[math.exp(z-m) for z in logits]
        denom=sum(exps)
        probs=[x/denom for x in exps]

        mass=[0.0]*n
        for prob,reg in zip(probs,meta):
            if reg is not None:
                mass[idx[reg]]+=prob

        winner=race["winner_registration"]
        q=race["q"]
        for k in range(n):
            g[k]+=q*mass[k]
        if winner in idx:
            g[idx[winner]]-=q

        for k in range(n):
            h[k][k]+=mass[k]-mass[k]*mass[k]
            for l in range(k+1,n):
                v=-mass[k]*mass[l]
                h[k][l]+=v
                h[l][k]+=v
    return g,h


def _solve_linear(a,b):
    n=len(b)
    if n==0:
        return []
    m=[list(row)+[float(rhs)] for row,rhs in zip(a,b)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(m[r][col]))
        if abs(m[pivot][col])<1e-14:
            raise LowDofFitError("singular_newton_hessian")
        if pivot!=col:
            m[col],m[pivot]=m[pivot],m[col]
        piv=m[col][col]
        for j in range(col,n+1):
            m[col][j]/=piv
        for r in range(n):
            if r==col:
                continue
            f=m[r][col]
            if f==0:
                continue
            for j in range(col,n+1):
                m[r][j]-=f*m[col][j]
    return [m[i][n] for i in range(n)]


def fit_delta(races:list[dict], supported_registrations:list[str], lam:float)->dict:
    present={r["official_registration_number"] for race in races for r in race["riders"] if r["parameter_active"]}
    params=sorted(set(supported_registrations)&present)
    values=[0.0]*len(params)
    if not params:
        return {
            "delta":{},
            "iterations":0,
            "converged":True,
            "gradient_inf_norm":0.0,
            "objective":sum(_race_loss(r,{}) for r in races),
        }

    converged=False
    grad_inf=None
    iteration=0
    for iteration in range(1,101):
        g,h=_grad_hess(races,params,values,lam)
        grad_inf=max(abs(x) for x in g)
        if grad_inf<=1e-10:
            converged=True
            break
        step=_solve_linear(h,[-x for x in g])
        dot=sum(gi*si for gi,si in zip(g,step))
        current=_objective(races,params,values,lam)
        t=1.0
        accepted=False
        for _ in range(60):
            candidate=[x+t*s for x,s in zip(values,step)]
            cand_obj=_objective(races,params,candidate,lam)
            if cand_obj<=current+1e-4*t*dot:
                values=candidate
                accepted=True
                break
            t*=0.5
        if not accepted:
            raise LowDofFitError("newton_line_search_failed")
    if not converged:
        g,_=_grad_hess(races,params,values,lam)
        grad_inf=max(abs(x) for x in g)
        converged=grad_inf<=1e-10
    if not converged:
        raise LowDofFitError(f"optimizer_not_converged_grad_inf={grad_inf}")

    return {
        "delta":dict(zip(params,values)),
        "iterations":iteration,
        "converged":True,
        "gradient_inf_norm":grad_inf,
        "objective":_objective(races,params,values,lam),
    }


def _mean_loss(races,delta):
    if not races:
        raise LowDofFitError("cannot_score_empty_race_set")
    return sum(_race_loss(r,delta) for r in races)/len(races)


def cross_validate(races,supported_regs):
    blocks=sorted({r["calendar_block"] for r in races})
    results=[]
    for lam in LAMBDA_GRID:
        heldout_losses=[]
        fold_rows=[]
        for block in blocks:
            train=[r for r in races if r["calendar_block"]!=block]
            hold=[r for r in races if r["calendar_block"]==block]
            if not train or not hold:
                raise LowDofFitError(f"invalid_cv_fold:{block}")
            fit=fit_delta(train,supported_regs,lam)
            loss=_mean_loss(hold,fit["delta"])
            heldout_losses.extend(_race_loss(r,fit["delta"]) for r in hold)
            fold_rows.append({
                "heldout_calendar_block":block,
                "train_races":len(train),
                "holdout_races":len(hold),
                "holdout_mean_winner_log_loss":loss,
                "fit_iterations":fit["iterations"],
            })
        mean=sum(heldout_losses)/len(heldout_losses)
        results.append({
            "lambda":lam,
            "mean_winner_log_loss":mean,
            "folds":fold_rows,
        })

    best_loss=min(x["mean_winner_log_loss"] for x in results)
    tied=[x for x in results if abs(x["mean_winner_log_loss"]-best_loss)<=1e-12]
    chosen=max(tied,key=lambda x:x["lambda"])
    return results,chosen["lambda"]


def fit(authorization:Mapping[str,Any], races)->dict:
    # SECURITY ORDER: all static authorization first; only then touch races.
    pre=authorization_preflight(authorization)
    supported=list(pre["supported_registrations"])
    normalized=_normalize_races(races,set(supported))

    cv,chosen_lambda=cross_validate(normalized,supported)
    final=fit_delta(normalized,supported,chosen_lambda)
    s0_loss=_mean_loss(normalized,{})
    challenger_loss=_mean_loss(normalized,final["delta"])

    seen={r["official_registration_number"] for race in normalized for r in race["riders"] if r["parameter_active"]}
    not_seen=sorted(set(supported)-seen)

    return {
        "record":"KEIRIN_RIDER_CIRCUMFERENCE_LOW_DOF_FIT_v1",
        "formula_id":FORMULA_ID,
        "baseline":{"name":"S0_SCORE_ONLY_SOFTMAX","beta":S0_BETA,"beta_frozen":True},
        "calendar_block_definition":CALENDAR_DEF,
        "lambda_grid":list(LAMBDA_GRID),
        "lambda_selection":"LEAVE_ONE_LOCAL_DAY1_RACE_DATE_OUT_MIN_MEAN_WINNER_LOG_LOSS; TIE_WITHIN_1E-12_CHOOSE_LARGEST_LAMBDA",
        "chosen_lambda":chosen_lambda,
        "cross_validation":cv,
        "final_fit":{
            "races":len(normalized),
            "calendar_blocks":sorted({r["calendar_block"] for r in normalized}),
            "delta_lookup":final["delta"],
            "iterations":final["iterations"],
            "gradient_inf_norm":final["gradient_inf_norm"],
            "objective_with_penalty":final["objective"],
            "supported_registrations_authorized":len(supported),
            "supported_registrations_seen_in_fit":len(seen),
            "supported_registrations_not_seen_in_fit":not_seen,
        },
        "fit_sample_probability_quality":{
            "s0_mean_winner_log_loss":s0_loss,
            "challenger_mean_winner_log_loss":challenger_loss,
            "improvement_s0_minus_challenger":s0_loss-challenger_loss,
            "development_advancement_decision_from_fit_sample":False,
        },
        "result_used_as_target_only":True,
        "result_used_as_feature":False,
        "payout_used":False,
        "odds_used":False,
        "human_forecast_used":False,
        "s0_refit":False,
        "network_access":False,
        "runtime":False,
        "note":"Fit-sample loss is diagnostic only. Advancement must be decided on the separately frozen later development-evaluation window with the frozen evaluator and bootstrap.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",required=True)
    ap.add_argument("--races",required=True)
    ap.add_argument("--out")
    a=ap.parse_args()

    auth=json.loads(Path(a.authorization).read_text(encoding="utf-8"))
    # Do not open outcome-bearing races until static authorization passes.
    authorization_preflight(auth)
    races=json.loads(Path(a.races).read_text(encoding="utf-8"))
    if isinstance(races,dict):
        races=races.get("races")

    try:
        out=fit(auth,races)
        rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            Path(a.out).write_text(rendered,encoding="utf-8")
        print(rendered,end="")
        return 0
    except Exception as exc:
        fail={
            "record":"KEIRIN_RIDER_CIRCUMFERENCE_LOW_DOF_FIT_v1",
            "status":"FAIL_CLOSED",
            "fatal_error":f"{type(exc).__name__}: {str(exc)[:800]}",
            "result_join_authorized":False,
            "runtime":False,
        }
        print(json.dumps(fail,ensure_ascii=False))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
