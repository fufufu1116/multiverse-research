#!/usr/bin/env python3
from datetime import date, timedelta

import keirin_longshot_shadow_guard_v2 as guard
import keirin_longshot_shadow_selector_v2 as selector
import keirin_shadow_risk_aggregator_v2 as risk
import keirin_longshot_evidence_sufficiency_v2 as evidence
import keirin_longshot_shadow_validation_gate_v2 as validation
import keirin_longshot_shadow_pipeline_v2 as pipeline


def must_fail(fn, contains=None):
    try:
        fn()
    except ValueError as exc:
        if contains is not None:
            assert contains in str(exc), (contains,str(exc))
        return
    raise AssertionError("expected fail-closed ValueError")


def mid_rows(probability: float):
    rows=[]
    start=date(2026,1,5)
    for i in range(100):
        week=i//10
        d=start+timedelta(days=7*week+(i%7))
        ret=20.0 if i%10==0 else 0.0
        rows.append({
            "band":"MID_HOLE",
            "date":d.isoformat(),
            "iso_week":f"{d.isocalendar().year}-W{d.isocalendar().week:02d}",
            "stake_units":1.0,
            "return_units":ret,
            "conservative_probability":probability,
        })
    return rows


def main():
    # Frozen band boundaries and finite-input guard.
    assert guard.band_for_odds(20.0).name=="CORE"
    assert guard.band_for_odds(20.1).name=="MID_HOLE"
    assert guard.band_for_odds(80.0).name=="MID_HOLE"
    assert guard.band_for_odds(80.1).name=="LONGSHOT"
    assert guard.band_for_odds(300.0).name=="LONGSHOT"
    assert guard.band_for_odds(300.1).name=="EXTREME_LONGSHOT"
    must_fail(lambda:guard.evaluate_ticket(0.05,0.05,float("nan")),"decimal_odds_must_be_finite")
    must_fail(lambda:guard.evaluate_ticket(float("inf"),0.05,30.0),"s0_probability_must_be_finite")
    must_fail(lambda:guard.evaluate_ticket(True,0.05,30.0),"s0_probability_must_be_numeric")

    # At most one hole ticket, duplicates are invalid rather than double-counted.
    selected=selector.select_one([
        {"ticket":"MID","s0_probability":0.05,"challenger_probability":0.052,"decimal_odds":30.0},
        {"ticket":"EXTREME","s0_probability":0.006,"challenger_probability":0.007,"decimal_odds":500.0},
    ])
    assert selected["action"]=="SHADOW_SELECT_ONE"
    assert selected["qualified_count"]==2
    assert selected["race_longshot_ticket_cap"]==1
    must_fail(lambda:selector.select_one([
        {"ticket":"DUP","s0_probability":0.05,"challenger_probability":0.052,"decimal_odds":30.0},
        {"ticket":"DUP","s0_probability":0.06,"challenger_probability":0.061,"decimal_odds":30.0},
    ]),"duplicate_ticket")

    # Non-finite risk cannot leak through as a NaN allocation.
    must_fail(
        lambda:risk.aggregate([{"requested_risk_units":float("nan")}]),
        "requested_risk_units:0_must_be_finite",
    )
    must_fail(
        lambda:risk.aggregate([],race_risk_cap=float("inf")),
        "race_risk_cap_must_be_finite",
    )
    both=risk.aggregate([
        {"lane":"CORE","requested_risk_units":1.0},
        {"lane":"MID_HOLE","requested_risk_units":0.5},
    ])
    assert both["cap_respected"] is True
    assert abs(both["allocated_total_risk_units"]-1.0)<1e-12

    # Same observed profits/hits: insufficient expected-hit mass must fail.
    lucky=validation.evaluate(mid_rows(0.001))
    lucky_mid=lucky["bands"][0]
    assert lucky_mid["decisions"]==100
    assert lucky_mid["hits"]==10
    assert abs(lucky_mid["expected_hits_under_frozen_conservative_probability"]-0.1)<1e-9
    assert lucky_mid["roi"]>0
    assert lucky_mid["leave_largest_hit_out_roi"]>0
    assert lucky_mid["largest_hit_share_of_profit"]<=0.50
    assert lucky_mid["calendar_weeks"]>=8
    assert lucky_mid["evidence_sufficient"] is False
    assert lucky_mid["proposed_stable_pass"] is False

    enough=validation.evaluate(mid_rows(0.05))
    enough_mid=enough["bands"][0]
    assert abs(enough_mid["expected_hits_under_frozen_conservative_probability"]-5.0)<1e-9
    assert enough_mid["evidence_sufficient"] is True
    assert enough_mid["proposed_stable_pass"] is True
    assert enough_mid["maximum_drawdown_units"]>=0.0
    assert enough_mid["maximum_consecutive_losing_decisions"]>=0
    assert len(enough_mid["weekly_roi"])>=8
    assert len(enough_mid["monthly_roi"])>=2

    # Standalone evidence diagnostics enforce the same expected-hit rule.
    ev_lucky=evidence.evaluate(mid_rows(0.001))
    ev_enough=evidence.evaluate(mid_rows(0.05))
    assert ev_lucky["bands"][0]["evidence_sufficient"] is False
    assert ev_enough["bands"][0]["evidence_sufficient"] is True
    assert abs(evidence.required_decisions_for_expected_hits(0.05)-100.0)<1e-9
    assert abs(evidence.required_decisions_for_expected_hits(0.01)-500.0)<1e-9
    assert abs(evidence.required_decisions_for_expected_hits(0.002)-2500.0)<1e-9
    must_fail(
        lambda:evidence.required_decisions_for_expected_hits(float("nan")),
        "avg_probability_must_be_finite",
    )

    # End-to-end pipeline keeps one hole and caps CORE+hole at one race unit.
    out=pipeline.run_pipeline([
        {"ticket":"MID","s0_probability":0.05,"challenger_probability":0.052,"decimal_odds":30.0},
        {"ticket":"EXTREME","s0_probability":0.006,"challenger_probability":0.007,"decimal_odds":500.0},
    ],core_selection={"ticket":"CORE","requested_risk_units":1.0})
    holes=[
        x for x in out["risk_aggregation"]["selections"]
        if x.get("lane") in {"MID_HOLE","LONGSHOT","EXTREME_LONGSHOT"}
    ]
    assert len(holes)==1
    assert out["risk_aggregation"]["cap_respected"] is True
    assert abs(out["risk_aggregation"]["allocated_total_risk_units"]-1.0)<1e-12
    assert out["real_money_instruction"] is False

    # Unknown validation bands must not disappear silently.
    bad=mid_rows(0.05)
    bad[0]["band"]="UNKNOWN"
    must_fail(lambda:validation.evaluate(bad),"unsupported_band")

    print("PASS 25/25")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
