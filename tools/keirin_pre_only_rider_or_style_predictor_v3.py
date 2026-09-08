#!/usr/bin/env python3
"""Hardened PRE-only rider/style x circumference predictor v3.

This is an input/integrity hardening layer only. It does not fit coefficients,
join outcomes, fetch odds, or authorize predictions under a blocked CURRENT.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Mapping

S0_BETA=0.22260435254784533
ALLOWED_STYLES={"逃","追","両"}
FORBIDDEN_ASCII={
    "result","results","outcome","outcomes","payout","payouts","odds",
    "prediction","predictions","forecast","forecasts","comment","comments",
    "finish","finishing"
}
FORBIDDEN_JP=("結果","払戻","オッズ","予想","コメント","着順")


class CircumferencePredictorError(ValueError):
    pass


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _finite(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise CircumferencePredictorError(f"{label}_must_be_numeric")
    x=float(value)
    if not math.isfinite(x):
        raise CircumferencePredictorError(f"{label}_must_be_finite")
    return x


def _assert_pre_only_keys(obj,label):
    if not isinstance(obj,Mapping):
        raise CircumferencePredictorError(f"{label}_must_be_mapping")
    for key in obj:
        raw=str(key)
        lowered=raw.lower()
        tokens={x for x in re.split(r"[^a-z0-9]+",lowered) if x}
        bad=tokens & FORBIDDEN_ASCII
        if bad or any(fragment in raw for fragment in FORBIDDEN_JP):
            raise CircumferencePredictorError(f"forbidden_post_decision_field:{label}:{raw}")


def _bucket_from_m(value):
    m=_finite(value,"circumference_m")
    if abs(m-400.0)<1e-6:
        return "400"
    if abs(m-333.0)<1.0 or abs(m-333.33)<1.0:
        return "333_OR_333_33"
    raise CircumferencePredictorError("unsupported_circumference_m")


def bucket(race):
    _assert_pre_only_keys(race,"race")
    declared=race.get("circumference_bucket")
    inferred=None
    if "circumference_m" in race:
        inferred=_bucket_from_m(race["circumference_m"])
    if declared is not None:
        if declared not in ("333_OR_333_33","400"):
            raise CircumferencePredictorError("unsupported_circumference_bucket")
        if inferred is not None and inferred!=declared:
            raise CircumferencePredictorError("circumference_bucket_meter_conflict")
        return declared
    if inferred is None:
        raise CircumferencePredictorError("missing_circumference")
    return inferred


def validate_model(model):
    if not isinstance(model,Mapping):
        raise CircumferencePredictorError("model_must_be_mapping")
    try:
        baseline=model["baseline"]
        if baseline.get("name")!="S0_SCORE_ONLY_SOFTMAX":
            raise CircumferencePredictorError("unexpected_baseline_name")
        beta=_finite(baseline["beta"],"baseline_beta")
        if abs(beta-S0_BETA)>1e-15:
            raise CircumferencePredictorError("s0_beta_mutation_detected")
        if baseline.get("beta_frozen") is not True:
            raise CircumferencePredictorError("baseline_beta_must_be_frozen")

        lookup_rows=list(model["rider_level"]["lookup"])
        style_lookup_raw=model["style_fallback"]["lookup"]
    except KeyError as exc:
        raise CircumferencePredictorError(f"missing_model_field:{exc.args[0]}") from exc

    rider_lookup={}
    for i,row in enumerate(lookup_rows):
        if not isinstance(row,Mapping):
            raise CircumferencePredictorError(f"rider_lookup_row_must_be_mapping:{i}")
        reg=row.get("official_registration_number")
        if not isinstance(reg,str) or not re.fullmatch(r"\d{6}",reg):
            raise CircumferencePredictorError(f"invalid_rider_registration:{i}")
        if reg in rider_lookup:
            raise CircumferencePredictorError(f"duplicate_rider_registration:{reg}")
        rider_lookup[reg]=_finite(row.get("delta_logit"),f"rider_delta_logit:{reg}")

    if not isinstance(style_lookup_raw,Mapping):
        raise CircumferencePredictorError("style_lookup_must_be_mapping")
    unknown_styles=set(style_lookup_raw)-ALLOWED_STYLES
    if unknown_styles:
        raise CircumferencePredictorError(f"unsupported_style_lookup:{sorted(unknown_styles)[0]}")
    style_lookup={}
    for style,payload in style_lookup_raw.items():
        if not isinstance(payload,Mapping):
            raise CircumferencePredictorError(f"style_lookup_payload_must_be_mapping:{style}")
        style_lookup[style]=_finite(payload.get("delta_logit"),f"style_delta_logit:{style}")

    safeguards=model.get("safeguards",{})
    for key in ("outcomes_used","payout_used","odds_used","human_forecast_used","s0_refit","runtime"):
        if safeguards.get(key) is not False:
            raise CircumferencePredictorError(f"unsafe_or_missing_model_safeguard:{key}")

    return beta,rider_lookup,style_lookup


def _validate_race_riders(race):
    raw=race.get("riders")
    if not isinstance(raw,list):
        raise CircumferencePredictorError("riders_must_be_list")
    if not (3<=len(raw)<=9):
        raise CircumferencePredictorError("race_rider_count_must_be_3_to_9")

    seen_cars=set()
    seen_regs=set()
    rows=[]
    for i,r in enumerate(raw):
        _assert_pre_only_keys(r,f"rider:{i}")
        car=r.get("car_no")
        if isinstance(car,bool) or not isinstance(car,int) or not (1<=car<=9):
            raise CircumferencePredictorError(f"invalid_car_no:{i}")
        if car in seen_cars:
            raise CircumferencePredictorError(f"duplicate_car_no:{car}")
        seen_cars.add(car)

        reg=r.get("official_registration_number")
        if reg in (None,""):
            reg=None
        elif not isinstance(reg,str) or not re.fullmatch(r"\d{6}",reg):
            raise CircumferencePredictorError(f"invalid_registration:{i}")
        if reg is not None:
            if reg in seen_regs:
                raise CircumferencePredictorError(f"duplicate_registration:{reg}")
            seen_regs.add(reg)

        style=r.get("style")
        if style is not None and not isinstance(style,str):
            raise CircumferencePredictorError(f"invalid_style_type:{i}")
        score=_finite(r.get("competition_score"),f"competition_score:{i}")
        rows.append({
            "car_no":car,
            "rider_name":r.get("rider_name"),
            "official_registration_number":reg,
            "style":style,
            "competition_score":score,
        })
    return rows


def predict(model,race):
    beta,rider_lookup,style_lookup=validate_model(model)
    b=bucket(race)
    q=1.0 if b=="333_OR_333_33" else -1.0
    inputs=_validate_race_riders(race)

    rows=[]
    for r in inputs:
        reg=r["official_registration_number"]
        style=r["style"]
        if reg is not None and reg in rider_lookup:
            delta,source=rider_lookup[reg],"RIDER"
        elif style in style_lookup:
            delta,source=style_lookup[style],"STYLE"
        else:
            delta,source=0.0,"S0"
        score=r["competition_score"]
        s0_logit=beta*score
        challenger_logit=s0_logit+q*delta
        if not math.isfinite(challenger_logit):
            raise CircumferencePredictorError("nonfinite_challenger_logit")
        rows.append({
            **r,
            "correction_source":source,
            "delta_logit":delta,
            "s0_logit":s0_logit,
            "challenger_logit":challenger_logit,
        })

    def probabilities(key):
        maximum=max(x[key] for x in rows)
        exps=[math.exp(x[key]-maximum) for x in rows]
        denominator=sum(exps)
        if not math.isfinite(denominator) or denominator<=0.0:
            raise CircumferencePredictorError("invalid_softmax_denominator")
        probs=[x/denominator for x in exps]
        if any(not math.isfinite(x) or x<0.0 or x>1.0 for x in probs):
            raise CircumferencePredictorError("invalid_probability")
        if abs(sum(probs)-1.0)>1e-12:
            raise CircumferencePredictorError("probability_mass_mismatch")
        return probs

    s0=probabilities("s0_logit")
    challenger=probabilities("challenger_logit")
    for i,row in enumerate(rows):
        row["s0_probability"]=s0[i]
        row["challenger_probability"]=challenger[i]
        row["change_percentage_points"]=(challenger[i]-s0[i])*100.0

    s0_order=sorted(range(len(rows)),key=lambda i:(-s0[i],rows[i]["car_no"]))
    ch_order=sorted(range(len(rows)),key=lambda i:(-challenger[i],rows[i]["car_no"]))
    s0_rank={idx:rank+1 for rank,idx in enumerate(s0_order)}
    ch_rank={idx:rank+1 for rank,idx in enumerate(ch_order)}
    for i,row in enumerate(rows):
        row["s0_rank"]=s0_rank[i]
        row["challenger_rank"]=ch_rank[i]

    return {
        "model":model.get("record"),
        "baseline":"S0_SCORE_ONLY_SOFTMAX",
        "baseline_beta":beta,
        "circumference_bucket":b,
        "input_firewall":"PRE_ONLY_POST_DECISION_FIELD_NAMES_FAIL_CLOSED",
        "target_result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "human_forecast_accessed":False,
        "rank_changed":any(r["s0_rank"]!=r["challenger_rank"] for r in rows),
        "top1_changed":s0_order[0]!=ch_order[0],
        "s0_probability_sum":sum(s0),
        "challenger_probability_sum":sum(challenger),
        "riders":sorted(rows,key=lambda r:r["challenger_rank"]),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True)
    ap.add_argument("--race",required=True)
    ap.add_argument("--out")
    args=ap.parse_args()
    out=predict(load_json(args.model),load_json(args.race))
    rendered=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(rendered,encoding="utf-8")
    else:
        print(rendered,end="")


if __name__=="__main__":
    main()
