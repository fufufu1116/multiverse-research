#!/usr/bin/env python3
from copy import deepcopy

import keirin_rider_circumference_development_evaluator_v2 as e


class PoisonRaces:
    """Any payload access is a test failure."""
    touched=False
    def __getattribute__(self,name):
        if name in {"touched","__class__"}:
            return object.__getattribute__(self,name)
        object.__setattr__(self,"touched",True)
        raise AssertionError(f"RESULT payload touched before authorization: {name}")


def races():
    out=[]
    for i in range(20):
        day=16+i%10
        base=10000+i*10
        out.append({
            "race_id":f"202609{day:02d}_V{i%2}_R{i+1}",
            "race_date":f"2026-09-{day:02d}",
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
        return str(exc)
    raise AssertionError("expected DevelopmentEvaluationError")


def main():
    xs=races()
    a=auth(xs)

    # Core firewall regression: authorization denial must occur without any
    # attribute/type/iteration access to the outcome-bearing payload object.
    blocked=deepcopy(a)
    blocked["result_join_authorized"]=False
    poison=PoisonRaces()
    err=must_fail(
        lambda:e.evaluate(blocked,poison,bootstrap_replicates=10),
        "authorization_gate_not_true:result_join_authorized",
    )
    assert poison.touched is False

    # Earlier gates also short-circuit before payload access.
    blocked2=deepcopy(a)
    blocked2["formal_support_gate_pass"]=False
    poison2=PoisonRaces()
    must_fail(
        lambda:e.evaluate(blocked2,poison2,bootstrap_replicates=10),
        "authorization_gate_not_true:formal_support_gate_pass",
    )
    assert poison2.touched is False

    # Authorized synthetic fixture preserves v1 frozen math.
    out=e.evaluate(a,xs,bootstrap_replicates=500)
    assert out["record"]=="KEIRIN_RIDER_CIRCUMFERENCE_DEVELOPMENT_EVALUATION_v2"
    assert out["authorization_preflight_before_payload_access"] is True
    assert out["metric_math_source"]=="v1 FROZEN PREOUTCOME MATH UNCHANGED"
    assert out["primary"]["challenger"]<out["primary"]["s0"]
    assert out["primary"]["primary_evidence_positive"] is True
    assert out["result_used_as_target_only"] is True
    assert out["result_used_as_feature"] is False
    assert out["payout_used"] is False
    assert out["odds_used"] is False

    # Non-target post-decision payload families are forbidden even after
    # result-target authority exists.
    bad=deepcopy(xs)
    bad[0]["odds_snapshot"]={"1":2.0}
    must_fail(
        lambda:e.evaluate(a,bad,bootstrap_replicates=10),
        "forbidden_non_target_post_decision_field",
    )
    bad=deepcopy(xs)
    bad[0]["riders"][0]["human_comment"]="x"
    must_fail(
        lambda:e.evaluate(a,bad,bootstrap_replicates=10),
        "forbidden_non_target_post_decision_field",
    )
    bad=deepcopy(xs)
    bad[0]["finish_order"]=[1,2,3,4]
    must_fail(
        lambda:e.evaluate(a,bad,bootstrap_replicates=10),
        "forbidden_non_target_post_decision_field",
    )
    bad=deepcopy(xs)
    bad[0]["payout"]=10000
    must_fail(
        lambda:e.evaluate(a,bad,bootstrap_replicates=10),
        "forbidden_non_target_post_decision_field",
    )

    # Exact frozen membership remains mandatory.
    bad_auth=deepcopy(a)
    bad_auth["frozen_race_ids"]=bad_auth["frozen_race_ids"][:-1]
    must_fail(
        lambda:e.evaluate(bad_auth,xs,bootstrap_replicates=10),
        "input_race_membership_mismatch",
    )

    # S0 cannot drift at authorization time.
    bad_auth=deepcopy(a)
    bad_auth["s0_beta"]=e.S0_BETA+0.001
    poison3=PoisonRaces()
    must_fail(
        lambda:e.evaluate(bad_auth,poison3,bootstrap_replicates=10),
        "s0_beta_mutation_detected",
    )
    assert poison3.touched is False

    print("PASS 17/17")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
