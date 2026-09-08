#!/usr/bin/env python3
from copy import deepcopy

import keirin_rider_circumference_development_evaluator_v1 as e


def races():
    out=[]
    for i in range(20):
        rid=f"202609{16+i%10:02d}_V{i%2}_R{i+1}"
        base=10000+i*10
        out.append({
            "race_id":rid,
            "race_date":f"2026-09-{16+i%10:02d}",
            "venue":"VENUE_A" if i%2==0 else "VENUE_B",
            "circumference_bucket":"333_OR_333_33" if i%2==0 else "400",
            "winner_registration":f"{base+1:06d}",
            "riders":[
                {"car_no":1,"official_registration_number":f"{base+1:06d}","s0_probability":0.40,"challenger_probability":0.50,"challenger_active":True},
                {"car_no":2,"official_registration_number":f"{base+2:06d}","s0_probability":0.30,"challenger_probability":0.25,"challenger_active":True},
                {"car_no":3,"official_registration_number":f"{base+3:06d}","s0_probability":0.20,"challenger_probability":0.15,"challenger_active":False},
                {"car_no":4,"official_registration_number":f"{base+4:06d}","s0_probability":0.10,"challenger_probability":0.10,"challenger_active":False},
            ],
        })
    return out


def auth(xs):
    return {
        "formal_support_gate_pass":True,
        "calendar_definition_adopted":True,
        "formula_frozen":True,
        "development_membership_frozen_preoutcome":True,
        "result_join_authorized":True,
        "source_gates_pass":True,
        "final_untouched_holdout_excluded":True,
        "s0_beta":e.S0_BETA,
        "calendar_definition_id":"TEST_ADOPTED_CALENDAR_DEF",
        "formula_hash":"a"*64,
        "membership_hash":"b"*64,
        "frozen_race_ids":[x["race_id"] for x in xs],
    }


def must_fail(fn,contains=None):
    try:
        fn()
    except e.DevelopmentEvaluationError as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return
    raise AssertionError("expected DevelopmentEvaluationError")


def main():
    xs=races()
    a=auth(xs)
    out=e.evaluate(a,xs,bootstrap_replicates=500)

    assert out["races"]==20
    assert out["primary"]["challenger"]<out["primary"]["s0"]
    assert out["primary"]["improvement_s0_minus_challenger"]>0.0
    assert out["primary"]["bootstrap_95_percentile_interval"]["lower_2_5"]>0.0
    assert out["primary"]["primary_evidence_positive"] is True

    assert out["secondary"]["winner_brier"]["challenger"]<out["secondary"]["winner_brier"]["s0"]
    assert out["secondary"]["winner_brier"]["formula"]=="mean over races of sum_over_cars((p-y)^2)"
    assert out["secondary"]["winner_brier"]["cannot_rescue_failed_primary"] is True

    expected_bins=[
        [0.0,0.1],[0.1,0.15],[0.15,0.2],[0.2,0.25],
        [0.25,0.3],[0.3,0.4],[0.4,1.0000000001],
    ]
    assert out["secondary"]["calibration"]["s0"]["fixed_probability_bins"]==expected_bins
    assert out["secondary"]["calibration"]["challenger"]["fixed_probability_bins"]==expected_bins
    assert out["secondary"]["calibration"]["s0"]["empty_or_small_bins"]=="REPORT_BUT_DO_NOT_MERGE_POSTHOC"

    assert abs(out["coverage"]["fallback_fraction_overall"]-0.5)<1e-12
    assert set(out["coverage"]["fallback_fraction_by_circumference"])=={"333_OR_333_33","400"}
    assert set(out["slices"]["by_venue"])=={"VENUE_A","VENUE_B"}
    assert out["full_advancement_decision_authorized"] is False
    assert out["result_used_as_target_only"] is True
    assert out["result_used_as_feature"] is False
    assert out["network_access"] is False

    # Bootstrap result is deterministic for fixed seed and inputs.
    out2=e.evaluate(a,xs,bootstrap_replicates=500)
    assert out["primary"]["bootstrap_95_percentile_interval"]==out2["primary"]["bootstrap_95_percentile_interval"]

    bad=deepcopy(a)
    bad["result_join_authorized"]=False
    must_fail(lambda:e.evaluate(bad,xs,bootstrap_replicates=10),"authorization_gate_not_true:result_join_authorized")

    bad=deepcopy(a)
    bad["s0_beta"]=e.S0_BETA+0.001
    must_fail(lambda:e.evaluate(bad,xs,bootstrap_replicates=10),"s0_beta_mutation_detected")

    bad=deepcopy(a)
    bad["frozen_race_ids"]=bad["frozen_race_ids"][:-1]
    must_fail(lambda:e.evaluate(bad,xs,bootstrap_replicates=10),"input_race_membership_mismatch")

    outside=deepcopy(xs)
    outside[0]["race_date"]="2026-09-27"
    must_fail(lambda:e.evaluate(a,outside,bootstrap_replicates=10),"race_outside_frozen_development_window")

    dup=deepcopy(xs)
    dup[0]["riders"][1]["car_no"]=1
    must_fail(lambda:e.evaluate(a,dup,bootstrap_replicates=10),"duplicate_car_no")

    mass=deepcopy(xs)
    mass[0]["riders"][0]["s0_probability"]=0.41
    must_fail(lambda:e.evaluate(a,mass,bootstrap_replicates=10),"s0_probability_mass_mismatch")

    winner=deepcopy(xs)
    winner[0]["winner_registration"]="999999"
    must_fail(lambda:e.evaluate(a,winner,bootstrap_replicates=10),"winner_not_in_race")

    print("PASS 22/22")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
