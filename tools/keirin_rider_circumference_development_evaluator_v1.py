#!/usr/bin/env python3
"""Frozen development evaluator for Rider x Circumference challenger v1.

Engineering-only prebuild. This tool has no network access and is not authorized
for use while CURRENT blocks RESULT. A future caller must supply an explicit
post-gate authorization manifest and exact frozen race membership.

Primary metric: winner log loss.
Secondary: multiclass Brier using the existing S0 convention, fixed-bin car-level
winner ECE using the existing S0 calibration prespec, and coverage diagnostics.
Primary uncertainty: race-resampling percentile bootstrap, 10,000 replicates,
seed 20260907, linear empirical percentile interpolation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json
import math
import random
import re
from pathlib import Path
from typing import Mapping

S0_BETA=0.22260435254784533
WINDOW_START=date(2026,9,16)
WINDOW_END=date(2026,9,26)
BOOTSTRAP_REPLICATES=10000
BOOTSTRAP_SEED=20260907
CALIBRATION_BINS=(
    (0.0,0.1),
    (0.1,0.15),
    (0.15,0.2),
    (0.2,0.25),
    (0.25,0.3),
    (0.3,0.4),
    (0.4,1.0000000001),
)


class DevelopmentEvaluationError(ValueError):
    pass


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise DevelopmentEvaluationError(f"{label}_must_be_numeric")
    x=float(value)
    if not math.isfinite(x):
        raise DevelopmentEvaluationError(f"{label}_must_be_finite")
    return x


def _authorization(auth,race_ids):
    if not isinstance(auth,Mapping):
        raise DevelopmentEvaluationError("authorization_must_be_mapping")
    required_true=(
        "formal_support_gate_pass",
        "calendar_definition_adopted",
        "formula_frozen",
        "development_membership_frozen_preoutcome",
        "result_join_authorized",
        "source_gates_pass",
        "final_untouched_holdout_excluded",
    )
    for key in required_true:
        if auth.get(key) is not True:
            raise DevelopmentEvaluationError(f"authorization_gate_not_true:{key}")

    beta=_finite(auth.get("s0_beta"),"authorization_s0_beta")
    if abs(beta-S0_BETA)>1e-15:
        raise DevelopmentEvaluationError("s0_beta_mutation_detected")

    if not isinstance(auth.get("calendar_definition_id"),str) or not auth["calendar_definition_id"].strip():
        raise DevelopmentEvaluationError("missing_calendar_definition_id")
    for key in ("formula_hash","membership_hash"):
        value=auth.get(key)
        if not isinstance(value,str) or not re.fullmatch(r"[0-9a-f]{64}",value):
            raise DevelopmentEvaluationError(f"invalid_{key}")

    frozen=auth.get("frozen_race_ids")
    if not isinstance(frozen,list) or any(not isinstance(x,str) or not x for x in frozen):
        raise DevelopmentEvaluationError("invalid_frozen_race_ids")
    if len(frozen)!=len(set(frozen)):
        raise DevelopmentEvaluationError("duplicate_frozen_race_id")
    if set(frozen)!=set(race_ids):
        raise DevelopmentEvaluationError("input_race_membership_mismatch")
    return True


def _normalize_races(races):
    if not isinstance(races,list) or not races:
        raise DevelopmentEvaluationError("races_must_be_nonempty_list")
    out=[]
    seen_race_ids=set()

    for ri,raw in enumerate(races):
        if not isinstance(raw,Mapping):
            raise DevelopmentEvaluationError(f"race_must_be_mapping:{ri}")
        race_id=raw.get("race_id")
        if not isinstance(race_id,str) or not race_id:
            raise DevelopmentEvaluationError(f"invalid_race_id:{ri}")
        if race_id in seen_race_ids:
            raise DevelopmentEvaluationError(f"duplicate_race_id:{race_id}")
        seen_race_ids.add(race_id)

        raw_date=raw.get("race_date")
        if not isinstance(raw_date,str):
            raise DevelopmentEvaluationError(f"race_date_must_be_string:{race_id}")
        try:
            d=date.fromisoformat(raw_date)
        except ValueError as exc:
            raise DevelopmentEvaluationError(f"invalid_race_date:{race_id}") from exc
        if not (WINDOW_START<=d<=WINDOW_END):
            raise DevelopmentEvaluationError(f"race_outside_frozen_development_window:{race_id}")

        venue=raw.get("venue")
        if not isinstance(venue,str) or not venue.strip():
            raise DevelopmentEvaluationError(f"invalid_venue:{race_id}")
        circumference=raw.get("circumference_bucket")
        if circumference not in ("333_OR_333_33","400"):
            raise DevelopmentEvaluationError(f"invalid_circumference_bucket:{race_id}")

        riders=raw.get("riders")
        if not isinstance(riders,list) or not (3<=len(riders)<=9):
            raise DevelopmentEvaluationError(f"invalid_rider_count:{race_id}")

        seen_cars=set()
        seen_regs=set()
        rows=[]
        for i,r in enumerate(riders):
            if not isinstance(r,Mapping):
                raise DevelopmentEvaluationError(f"rider_must_be_mapping:{race_id}:{i}")
            car=r.get("car_no")
            if isinstance(car,bool) or not isinstance(car,int) or not (1<=car<=9):
                raise DevelopmentEvaluationError(f"invalid_car_no:{race_id}:{i}")
            if car in seen_cars:
                raise DevelopmentEvaluationError(f"duplicate_car_no:{race_id}:{car}")
            seen_cars.add(car)

            reg=r.get("official_registration_number")
            if not isinstance(reg,str) or not re.fullmatch(r"\d{6}",reg):
                raise DevelopmentEvaluationError(f"invalid_registration:{race_id}:{i}")
            if reg in seen_regs:
                raise DevelopmentEvaluationError(f"duplicate_registration:{race_id}:{reg}")
            seen_regs.add(reg)

            s0=_finite(r.get("s0_probability"),f"s0_probability:{race_id}:{car}")
            challenger=_finite(r.get("challenger_probability"),f"challenger_probability:{race_id}:{car}")
            if not (0.0<s0<=1.0) or not (0.0<challenger<=1.0):
                raise DevelopmentEvaluationError(f"probability_must_be_in_(0,1]:{race_id}:{car}")
            active=r.get("challenger_active")
            if not isinstance(active,bool):
                raise DevelopmentEvaluationError(f"challenger_active_must_be_boolean:{race_id}:{car}")
            rows.append({
                "car_no":car,
                "official_registration_number":reg,
                "s0_probability":s0,
                "challenger_probability":challenger,
                "challenger_active":active,
            })

        s0_mass=sum(x["s0_probability"] for x in rows)
        ch_mass=sum(x["challenger_probability"] for x in rows)
        if abs(s0_mass-1.0)>1e-9:
            raise DevelopmentEvaluationError(f"s0_probability_mass_mismatch:{race_id}:{s0_mass}")
        if abs(ch_mass-1.0)>1e-9:
            raise DevelopmentEvaluationError(f"challenger_probability_mass_mismatch:{race_id}:{ch_mass}")

        winner=raw.get("winner_registration")
        if winner not in seen_regs:
            raise DevelopmentEvaluationError(f"winner_not_in_race:{race_id}")

        out.append({
            "race_id":race_id,
            "race_date":d,
            "venue":venue,
            "circumference_bucket":circumference,
            "winner_registration":winner,
            "riders":rows,
        })
    return out


def _brier(rows,winner,key):
    return sum(
        (r[key]-(1.0 if r["official_registration_number"]==winner else 0.0))**2
        for r in rows
    )


def _percentile_linear(values,q):
    if not values:
        raise DevelopmentEvaluationError("empty_percentile_values")
    xs=sorted(float(x) for x in values)
    if not (0.0<=q<=1.0):
        raise DevelopmentEvaluationError("percentile_q_out_of_range")
    pos=(len(xs)-1)*q
    lo=int(math.floor(pos))
    hi=int(math.ceil(pos))
    if lo==hi:
        return xs[lo]
    weight=pos-lo
    return xs[lo]*(1.0-weight)+xs[hi]*weight


def _bootstrap_ci(improvements,replicates=BOOTSTRAP_REPLICATES,seed=BOOTSTRAP_SEED):
    if not isinstance(replicates,int) or isinstance(replicates,bool) or replicates<1:
        raise DevelopmentEvaluationError("bootstrap_replicates_must_be_positive_integer")
    if len(improvements)<2:
        raise DevelopmentEvaluationError("need_at_least_two_races_for_bootstrap")
    rng=random.Random(seed)
    n=len(improvements)
    means=[]
    for _ in range(replicates):
        total=0.0
        for _ in range(n):
            total+=improvements[rng.randrange(n)]
        means.append(total/n)
    return {
        "replicates":replicates,
        "seed":seed,
        "percentile_method":"LINEAR_INTERPOLATION_POSITION_(N-1)*Q",
        "lower_2_5":_percentile_linear(means,0.025),
        "upper_97_5":_percentile_linear(means,0.975),
    }


def _ece(races,key):
    bins=[[] for _ in CALIBRATION_BINS]
    for race in races:
        winner=race["winner_registration"]
        for r in race["riders"]:
            p=r[key]
            y=1.0 if r["official_registration_number"]==winner else 0.0
            placed=False
            for i,(lo,hi) in enumerate(CALIBRATION_BINS):
                if lo<=p<hi:
                    bins[i].append((p,y))
                    placed=True
                    break
            if not placed:
                raise DevelopmentEvaluationError(f"probability_outside_calibration_bins:{p}")

    total=sum(len(x) for x in bins)
    details=[]
    weighted=0.0
    eligible_gaps=[]
    for (lo,hi),items in zip(CALIBRATION_BINS,bins):
        n=len(items)
        mean_p=(sum(x[0] for x in items)/n) if n else None
        win_rate=(sum(x[1] for x in items)/n) if n else None
        gap=(abs(mean_p-win_rate) if n else None)
        if n:
            weighted+=(n/total)*gap
            if n>=20:
                eligible_gaps.append(gap)
        details.append({
            "range":[lo,hi],
            "n":n,
            "mean_predicted_probability":mean_p,
            "empirical_win_rate":win_rate,
            "absolute_gap":gap,
            "interpretive_flag_eligible":n>=20,
        })
    return {
        "unit":"car_level_binary_winner_event",
        "fixed_probability_bins":[list(x) for x in CALIBRATION_BINS],
        "interval_rule":"left_closed_right_open_except_last_effectively_inclusive",
        "weighted_ECE_absolute_gap":weighted,
        "max_eligible_bin_absolute_gap":max(eligible_gaps) if eligible_gaps else None,
        "minimum_bin_n_for_interpretive_flag":20,
        "empty_or_small_bins":"REPORT_BUT_DO_NOT_MERGE_POSTHOC",
        "bins":details,
    }


def _slice_improvement(per_race,key):
    groups=defaultdict(list)
    for row in per_race:
        groups[row[key]].append(row["winner_log_loss_improvement"])
    return {
        str(group):{
            "races":len(values),
            "mean_winner_log_loss_improvement":sum(values)/len(values),
            "negative":(sum(values)/len(values))<0.0,
        }
        for group,values in sorted(groups.items(),key=lambda x:str(x[0]))
    }


def _evaluate_metrics(normalized,bootstrap_replicates=BOOTSTRAP_REPLICATES):
    per_race=[]
    active_venue=Counter()
    active_rider=Counter()
    active_by_circ=Counter()
    total_by_circ=Counter()
    active_rows=0
    total_rows=0

    for race in normalized:
        winner=race["winner_registration"]
        by_reg={r["official_registration_number"]:r for r in race["riders"]}
        wp=by_reg[winner]
        s0_ll=-math.log(wp["s0_probability"])
        ch_ll=-math.log(wp["challenger_probability"])
        improvement=s0_ll-ch_ll
        s0_brier=_brier(race["riders"],winner,"s0_probability")
        ch_brier=_brier(race["riders"],winner,"challenger_probability")

        per_race.append({
            "race_id":race["race_id"],
            "race_date":race["race_date"].isoformat(),
            "venue":race["venue"],
            "circumference_bucket":race["circumference_bucket"],
            "winner_log_loss_s0":s0_ll,
            "winner_log_loss_challenger":ch_ll,
            "winner_log_loss_improvement":improvement,
            "winner_brier_s0":s0_brier,
            "winner_brier_challenger":ch_brier,
            "winner_brier_improvement":s0_brier-ch_brier,
        })

        for r in race["riders"]:
            total_rows+=1
            total_by_circ[race["circumference_bucket"]]+=1
            if r["challenger_active"]:
                active_rows+=1
                active_venue[race["venue"]]+=1
                active_rider[r["official_registration_number"]]+=1
                active_by_circ[race["circumference_bucket"]]+=1

    n=len(per_race)
    improvements=[x["winner_log_loss_improvement"] for x in per_race]
    bootstrap=_bootstrap_ci(improvements,replicates=bootstrap_replicates)

    def mean(field):
        return sum(x[field] for x in per_race)/n

    max_venue_share=(max(active_venue.values())/active_rows) if active_rows else None
    max_rider_share=(max(active_rider.values())/active_rows) if active_rows else None
    fallback_by_circ={}
    for circ,total in total_by_circ.items():
        active=active_by_circ[circ]
        fallback_by_circ[circ]=1.0-active/total

    return {
        "races":n,
        "primary":{
            "metric":"WINNER_LOG_LOSS",
            "s0":mean("winner_log_loss_s0"),
            "challenger":mean("winner_log_loss_challenger"),
            "improvement_s0_minus_challenger":mean("winner_log_loss_improvement"),
            "bootstrap_95_percentile_interval":bootstrap,
            "primary_evidence_positive":(
                mean("winner_log_loss_improvement")>0.0
                and bootstrap["lower_2_5"]>0.0
            ),
        },
        "secondary":{
            "winner_brier":{
                "formula":"mean over races of sum_over_cars((p-y)^2)",
                "s0":mean("winner_brier_s0"),
                "challenger":mean("winner_brier_challenger"),
                "improvement_s0_minus_challenger":mean("winner_brier_improvement"),
                "cannot_rescue_failed_primary":True,
            },
            "calibration":{
                "s0":_ece(normalized,"s0_probability"),
                "challenger":_ece(normalized,"challenger_probability"),
                "cannot_rescue_failed_primary":True,
            },
        },
        "coverage":{
            "active_rows":active_rows,
            "total_rows":total_rows,
            "fallback_fraction_overall":1.0-active_rows/total_rows,
            "fallback_fraction_by_circumference":fallback_by_circ,
            "max_single_venue_share_of_active_rows":max_venue_share,
            "max_single_rider_share_of_active_rows":max_rider_share,
            "venue_share_threshold":0.60,
            "rider_share_threshold":0.10,
        },
        "slices":{
            "by_venue":_slice_improvement(per_race,"venue"),
            "by_date":_slice_improvement(per_race,"race_date"),
            "by_circumference":_slice_improvement(per_race,"circumference_bucket"),
        },
        "per_race":per_race,
        "full_advancement_decision_authorized":False,
        "note":"Primary evidence is only one required component; full advancement also requires all frozen source/concentration/diagnostic gates.",
    }


def evaluate(authorization,races,bootstrap_replicates=BOOTSTRAP_REPLICATES):
    normalized=_normalize_races(races)
    _authorization(authorization,[x["race_id"] for x in normalized])
    out=_evaluate_metrics(normalized,bootstrap_replicates=bootstrap_replicates)
    out.update({
        "record":"KEIRIN_RIDER_CIRCUMFERENCE_DEVELOPMENT_EVALUATION_v1",
        "window":"2026-09-16..2026-09-26 ALL DAY1 STARTS",
        "s0_beta":S0_BETA,
        "result_used_as_target_only":True,
        "result_used_as_feature":False,
        "payout_used":False,
        "odds_used":False,
        "human_forecast_used":False,
        "network_access":False,
        "runtime":False,
    })
    return out


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",required=True)
    ap.add_argument("--races",required=True)
    ap.add_argument("--out")
    args=ap.parse_args()
    auth=json.loads(Path(args.authorization).read_text(encoding="utf-8"))
    races=json.loads(Path(args.races).read_text(encoding="utf-8"))
    out=evaluate(auth,races)
    rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(rendered,encoding="utf-8")
    else:
        print(rendered,end="")


if __name__=="__main__":
    main()
