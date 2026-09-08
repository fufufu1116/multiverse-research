#!/usr/bin/env python3
from copy import deepcopy
import math

import keirin_pre_only_rider_or_style_predictor_v3 as p


def model():
    return {
        "record":"TEST_MODEL",
        "baseline":{
            "name":"S0_SCORE_ONLY_SOFTMAX",
            "beta":p.S0_BETA,
            "beta_frozen":True,
        },
        "rider_level":{
            "lookup":[
                {"official_registration_number":"010001","delta_logit":0.10},
                {"official_registration_number":"010002","delta_logit":-0.05},
            ]
        },
        "style_fallback":{
            "lookup":{
                "逃":{"delta_logit":0.02},
                "追":{"delta_logit":-0.01},
                "両":{"delta_logit":0.0},
            }
        },
        "safeguards":{
            "outcomes_used":False,
            "payout_used":False,
            "odds_used":False,
            "human_forecast_used":False,
            "s0_refit":False,
            "runtime":False,
        }
    }


def race():
    return {
        "circumference_bucket":"333_OR_333_33",
        "circumference_m":333.33,
        "riders":[
            {"car_no":1,"official_registration_number":"010001","rider_name":"A","style":"逃","competition_score":100.0},
            {"car_no":2,"official_registration_number":"010002","rider_name":"B","style":"追","competition_score":99.0},
            {"car_no":3,"official_registration_number":"010003","rider_name":"C","style":"逃","competition_score":98.0},
            {"car_no":4,"official_registration_number":"010004","rider_name":"D","style":"追","competition_score":97.0},
            {"car_no":5,"official_registration_number":"010005","rider_name":"E","style":"両","competition_score":96.0},
            {"car_no":6,"official_registration_number":"010006","rider_name":"F","style":"未知","competition_score":95.0},
            {"car_no":7,"official_registration_number":"010007","rider_name":"G","style":None,"competition_score":94.0},
        ]
    }


def must_fail(fn, contains=None):
    try:
        fn()
    except p.CircumferencePredictorError as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return
    raise AssertionError("expected CircumferencePredictorError")


def main():
    out=p.predict(model(),race())
    assert len(out["riders"])==7
    assert abs(out["s0_probability_sum"]-1.0)<1e-12
    assert abs(out["challenger_probability_sum"]-1.0)<1e-12
    assert out["target_result_accessed"] is False
    assert out["odds_accessed"] is False

    by_car={r["car_no"]:r for r in out["riders"]}
    assert by_car[1]["correction_source"]=="RIDER"
    assert by_car[3]["correction_source"]=="STYLE"
    assert by_car[6]["correction_source"]=="S0"
    assert by_car[7]["correction_source"]=="S0"

    # 400m reverses the circumference correction sign.
    r400=race()
    r400["circumference_bucket"]="400"
    r400["circumference_m"]=400.0
    out400=p.predict(model(),r400)
    by400={r["car_no"]:r for r in out400["riders"]}
    assert abs(by_car[1]["delta_logit"]-0.10)<1e-12
    assert abs(by400[1]["delta_logit"]-0.10)<1e-12
    assert by_car[1]["challenger_logit"]>by_car[1]["s0_logit"]
    assert by400[1]["challenger_logit"]<by400[1]["s0_logit"]

    bad_model=model()
    bad_model["baseline"]["beta"]=p.S0_BETA+0.001
    must_fail(lambda:p.predict(bad_model,race()),"s0_beta_mutation_detected")

    dup_lookup=model()
    dup_lookup["rider_level"]["lookup"].append(
        {"official_registration_number":"010001","delta_logit":0.2}
    )
    must_fail(lambda:p.predict(dup_lookup,race()),"duplicate_rider_registration")

    nonfinite_delta=model()
    nonfinite_delta["rider_level"]["lookup"][0]["delta_logit"]=float("inf")
    must_fail(lambda:p.predict(nonfinite_delta,race()),"rider_delta_logit:010001_must_be_finite")

    dup_car=race()
    dup_car["riders"][1]["car_no"]=1
    must_fail(lambda:p.predict(model(),dup_car),"duplicate_car_no")

    dup_reg=race()
    dup_reg["riders"][1]["official_registration_number"]="010001"
    must_fail(lambda:p.predict(model(),dup_reg),"duplicate_registration")

    leaked_result=race()
    leaked_result["riders"][0]["result_rank"]=1
    must_fail(lambda:p.predict(model(),leaked_result),"forbidden_post_decision_field")

    leaked_odds=race()
    leaked_odds["odds_snapshot"]={"1":2.0}
    must_fail(lambda:p.predict(model(),leaked_odds),"forbidden_post_decision_field")

    conflict=race()
    conflict["circumference_bucket"]="400"
    must_fail(lambda:p.predict(model(),conflict),"circumference_bucket_meter_conflict")

    nonfinite_score=race()
    nonfinite_score["riders"][0]["competition_score"]=float("nan")
    must_fail(lambda:p.predict(model(),nonfinite_score),"competition_score:0_must_be_finite")

    bad_car=race()
    bad_car["riders"][6]["car_no"]=10
    must_fail(lambda:p.predict(model(),bad_car),"invalid_car_no")

    short=race()
    short["riders"]=short["riders"][:2]
    must_fail(lambda:p.predict(model(),short),"race_rider_count_must_be_3_to_9")

    unsafe=model()
    unsafe["safeguards"]["odds_used"]=True
    must_fail(lambda:p.predict(unsafe,race()),"unsafe_or_missing_model_safeguard:odds_used")

    print("PASS 18/18")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
