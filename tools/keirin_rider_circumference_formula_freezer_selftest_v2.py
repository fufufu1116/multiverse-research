#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

f=importlib.import_module("keirin_rider_circumference_formula_freezer_v2")


def auth():
    return {
        "support_gate_pass":True,
        "calendar_definition_adopted":True,
        "fit_membership_frozen":True,
        "evaluation_membership_frozen":True,
        "result_still_closed":True,
        "calendar_block_definition":"LOCAL_DAY1_RACE_DATE",
        "s0_beta":f.S0_BETA,
        "lambda_grid":[1,4,16,64],
        "support_gate_artifact_sha256":"a"*64,
        "calendar_adoption_artifact_sha256":"b"*64,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "model_promotion_authorized":False,
    }


def fit_membership():
    return {
        "record":"TEST_FIT_MEMBERSHIP",
        "role":"DEVELOPMENT_FIT_PRE_ONLY",
        "membership_frozen":True,
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "races":[
            {
                "race_id":"FIT_20260914_ITO_03",
                "race_date":"2026-09-14",
                "venue":"伊東",
                "circumference_bucket":"333_OR_333_33",
                "riders":[
                    {
                        "car_no":1,
                        "official_registration_number":"010001",
                        "competition_score":100.1,
                        "class":"S1",
                        "style":"追",
                    },
                    {
                        "car_no":2,
                        "official_registration_number":"010002",
                        "competition_score":99.2,
                        "class":"S1",
                        "style":"逃",
                    },
                    {
                        "car_no":3,
                        "official_registration_number":"010003",
                        "competition_score":98.3,
                        "class":"S2",
                        "style":"両",
                    },
                ],
            }
        ],
    }


def eval_membership():
    return {
        "record":"TEST_EVAL_MEMBERSHIP",
        "role":"DEVELOPMENT_EVALUATION_PRE_ONLY",
        "membership_frozen":True,
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "prediction_accessed":False,
        "human_comments_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "races":[
            {
                "race_id":"EVAL_20260916_X_01",
                "race_date":"2026-09-16",
                "venue":"X",
                "circumference_bucket":"400",
                "riders":[
                    {
                        "car_no":1,
                        "official_registration_number":"020001",
                        "competition_score":90.0,
                        "class":"A1",
                        "style":"追",
                    },
                    {
                        "car_no":2,
                        "official_registration_number":"020002",
                        "competition_score":89.0,
                        "class":"A1",
                        "style":"逃",
                    },
                    {
                        "car_no":3,
                        "official_registration_number":"020003",
                        "competition_score":88.0,
                        "class":"A2",
                        "style":"両",
                    },
                ],
            }
        ],
    }


def must_fail(fn,contains=None):
    try:
        fn()
    except f.FormulaFreezeError as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return str(exc)
    raise AssertionError("expected FormulaFreezeError")


def main():
    a=auth()
    fit=fit_membership()
    ev=eval_membership()

    out=f.freeze(a,fit,ev)
    assert out["record"]=="KEIRIN_RIDER_CIRCUMFERENCE_EXACT_FORMULA_FREEZE_v2"
    assert out["formula_frozen"] is True
    assert out["formula_id"]=="S0_PLUS_SHRUNK_RIDER_X_CIRCUMFERENCE_OFFSET_v1"
    assert out["calendar_block_definition"]=="LOCAL_DAY1_RACE_DATE"
    assert out["baseline"]["beta"]==f.S0_BETA
    assert out["lambda_grid"]==[1,4,16,64]
    assert out["development_fit_membership"]["race_count"]==1
    assert out["development_evaluation_membership"]["race_count"]==1
    assert out["result_accessed"] is False
    assert out["result_join_authorized"] is False
    assert out["formula_fit_authorized"] is False
    assert out["runtime"] is False
    assert out["pre_only_membership_firewall"]=="RECURSIVE_SCHEMA_KEY_FAIL_CLOSED"

    # Deterministic freeze hash for identical inputs.
    out2=f.freeze(a,fit,ev)
    assert out["freeze_sha256"]==out2["freeze_sha256"]

    # Explicit safe governance flags are accepted only in their safe state.
    bad=deepcopy(a)
    bad["result_still_closed"]=False
    must_fail(lambda:f.freeze(bad,fit,ev),"authorization_gate_not_true:result_still_closed")

    for key in ("result_join_authorized","formula_fit_authorized","model_promotion_authorized"):
        bad=deepcopy(a)
        bad[key]=True
        must_fail(
            lambda bad=bad,key=key:f.freeze(bad,fit,ev),
            f"authority_must_not_precede_formula_freeze:{key}",
        )

    # Nested post-decision data is forbidden anywhere in PRE membership.
    cases=[
        ("winner_registration","020001","winner"),
        ("odds_snapshot",{"1":2.0},"odds"),
        ("result_order",[1,2,3],"result"),
        ("payout_yen",10000,"payout"),
        ("prediction_score",0.8,"prediction"),
        ("human_comments","x","comments"),
        ("finish_rank",1,"finish"),
        ("着順",1,"着順"),
    ]
    for key,value,_marker in cases:
        bad=eval_membership()
        bad["races"][0][key]=value
        must_fail(
            lambda bad=bad:f.freeze(a,fit,bad),
            "forbidden_post_decision_field_in_membership",
        )

    # Nested rider-level leakage is also rejected.
    bad=fit_membership()
    bad["races"][0]["riders"][0]["odds"]=3.2
    must_fail(
        lambda:f.freeze(a,bad,ev),
        "forbidden_post_decision_field_in_membership",
    )

    # True access flags in membership are forbidden.
    bad=fit_membership()
    bad["result_accessed"]=True
    must_fail(
        lambda:f.freeze(a,bad,ev),
        "pre_freeze_governance_flag_must_be_false",
    )

    # v1 frozen formula gates remain unchanged.
    bad=deepcopy(a)
    bad["calendar_block_definition"]="WEEK"
    must_fail(lambda:f.freeze(bad,fit,ev),"unexpected_calendar_block_definition")

    bad=deepcopy(a)
    bad["s0_beta"]=f.S0_BETA+0.001
    must_fail(lambda:f.freeze(bad,fit,ev),"s0_beta_mutation_detected")

    bad=deepcopy(a)
    bad["lambda_grid"]=[1,2,4,8]
    must_fail(lambda:f.freeze(bad,fit,ev),"lambda_grid_mutation_detected")

    bad=eval_membership()
    bad["races"][0]["race_date"]="2026-09-27"
    must_fail(
        lambda:f.freeze(a,fit,bad),
        "evaluation_race_outside_frozen_window",
    )

    bad=eval_membership()
    bad["races"].append(deepcopy(bad["races"][0]))
    must_fail(
        lambda:f.freeze(a,fit,bad),
        "DEVELOPMENT_EVALUATION_PRE_ONLY_duplicate_race_id",
    )

    bad=fit_membership()
    bad["role"]="WRONG"
    must_fail(
        lambda:f.freeze(a,bad,ev),
        "DEVELOPMENT_FIT_PRE_ONLY_role_mismatch",
    )

    print("PASS 27/27")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
