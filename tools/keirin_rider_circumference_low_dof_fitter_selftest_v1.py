#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

f=importlib.import_module("keirin_rider_circumference_low_dof_fitter_v1")


class PoisonRaces:
    touched=False
    def __getattribute__(self,name):
        if name in {"touched","__class__"}:
            return object.__getattribute__(self,name)
        object.__setattr__(self,"touched",True)
        raise AssertionError(f"outcome payload touched before authorization: {name}")


def auth():
    return {
        "support_gate_pass":True,
        "calendar_definition_adopted":True,
        "formula_frozen":True,
        "fit_membership_frozen":True,
        "result_join_authorized":True,
        "final_untouched_holdout_excluded":True,
        "formula_id":f.FORMULA_ID,
        "calendar_block_definition":f.CALENDAR_DEF,
        "s0_beta":f.S0_BETA,
        "lambda_grid":[1,4,16,64],
        "supported_registrations":["010001","010002"],
        "formula_hash":"a"*64,
        "fit_membership_hash":"b"*64,
    }


def race(race_id,date,circ,winner):
    return {
        "race_id":race_id,
        "race_date":date,
        "calendar_block":date,
        "circumference_bucket":circ,
        "winner_registration":winner,
        "riders":[
            {"car_no":1,"official_registration_number":"010001","competition_score":100.0},
            {"car_no":2,"official_registration_number":"010002","competition_score":100.0},
            {"car_no":3,"official_registration_number":"010003","competition_score":100.0},
        ],
    }


def races():
    out=[]
    for i,d in enumerate(["2026-09-16","2026-09-17","2026-09-18","2026-09-19"],1):
        out.append(race(f"{d}-333",d,"333_OR_333_33","010001"))
        out.append(race(f"{d}-400",d,"400","010002"))
    return out


def must_fail(fn,contains=None):
    try:
        fn()
    except f.LowDofFitError as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return
    raise AssertionError("expected LowDofFitError")


def main():
    xs=races()
    a=auth()

    # Authorization denial must short-circuit before race payload access.
    blocked=deepcopy(a)
    blocked["result_join_authorized"]=False
    poison=PoisonRaces()
    must_fail(
        lambda:f.fit(blocked,poison),
        "authorization_gate_not_true:result_join_authorized",
    )
    assert poison.touched is False

    wrong_calendar=deepcopy(a)
    wrong_calendar["calendar_block_definition"]="WEEK"
    poison2=PoisonRaces()
    must_fail(
        lambda:f.fit(wrong_calendar,poison2),
        "unexpected_calendar_block_definition",
    )
    assert poison2.touched is False

    wrong_beta=deepcopy(a)
    wrong_beta["s0_beta"]=f.S0_BETA+0.01
    poison3=PoisonRaces()
    must_fail(lambda:f.fit(wrong_beta,poison3),"s0_beta_mutation_detected")
    assert poison3.touched is False

    wrong_grid=deepcopy(a)
    wrong_grid["lambda_grid"]=[1,2,4,8]
    poison4=PoisonRaces()
    must_fail(lambda:f.fit(wrong_grid,poison4),"lambda_grid_mutation_detected")
    assert poison4.touched is False

    out=f.fit(a,xs)
    assert out["baseline"]["beta"]==f.S0_BETA
    assert out["baseline"]["beta_frozen"] is True
    assert out["chosen_lambda"] in [1.0,4.0,16.0,64.0]
    assert len(out["cross_validation"])==4
    assert all(len(x["folds"])==4 for x in out["cross_validation"])

    delta=out["final_fit"]["delta_lookup"]
    assert set(delta)=={"010001","010002"}
    assert delta["010001"]>0.0,delta
    assert delta["010002"]<0.0,delta
    assert out["final_fit"]["gradient_inf_norm"]<=1e-10
    assert out["fit_sample_probability_quality"]["challenger_mean_winner_log_loss"] < out["fit_sample_probability_quality"]["s0_mean_winner_log_loss"]
    assert out["fit_sample_probability_quality"]["improvement_s0_minus_challenger"]>0.0
    assert out["fit_sample_probability_quality"]["development_advancement_decision_from_fit_sample"] is False
    assert out["result_used_as_target_only"] is True
    assert out["result_used_as_feature"] is False
    assert out["odds_used"] is False
    assert out["s0_refit"] is False

    # Calendar block must be exact LOCAL_DAY1_RACE_DATE.
    bad=deepcopy(xs)
    bad[0]["calendar_block"]="2026-W38"
    must_fail(lambda:f.fit(a,bad),"calendar_block_must_equal_local_day1_race_date")

    # Only winner_registration is allowed as the target field.
    bad=deepcopy(xs)
    bad[0]["finish_order"]=["010001","010002","010003"]
    must_fail(lambda:f.fit(a,bad),"forbidden_post_decision_field")

    bad=deepcopy(xs)
    bad[0]["riders"][0]["odds"]=2.0
    must_fail(lambda:f.fit(a,bad),"forbidden_post_decision_field")

    # Missing/zero/nonfinite competition score fails closed.
    bad=deepcopy(xs)
    bad[0]["riders"][0]["competition_score"]=0.0
    must_fail(lambda:f.fit(a,bad),"competition_score_must_be_positive")

    bad=deepcopy(xs)
    bad[0]["riders"][0]["competition_score"]=float("nan")
    must_fail(lambda:f.fit(a,bad),"must_be_finite")

    # Winner must be one of the exact race riders.
    bad=deepcopy(xs)
    bad[0]["winner_registration"]="999999"
    must_fail(lambda:f.fit(a,bad),"winner_not_in_race")

    # CV requires at least two distinct date blocks.
    bad=[deepcopy(xs[0]),deepcopy(xs[1])]
    bad[1]["race_id"]="other"
    bad[1]["race_date"]=bad[0]["race_date"]
    bad[1]["calendar_block"]=bad[0]["calendar_block"]
    must_fail(lambda:f.fit(a,bad),"need_at_least_two_calendar_blocks_for_cv")

    print("PASS 29/29")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
