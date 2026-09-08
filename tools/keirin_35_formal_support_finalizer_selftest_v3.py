#!/usr/bin/env python3
"""Isolated PRE-only compatibility selftest for finalizer v3."""

from copy import deepcopy
import hashlib
import importlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
v3 = importlib.import_module("keirin_35_formal_support_finalizer_v3")


def fixture(n=35):
    order=[]; matrix=[]; registry=[]; rows=[]; baseline=[
        {
            "rider_name":"BASE","official_registration_number":"000001",
            "race_date":"2098-12-01","venue":"BASE400",
            "circumference_m":400,"day":"Day1","race_no":1,"car_no":1,
            "class":"S1","style":"追","source_url":"https://example.invalid/racecard"
        },
        {
            "rider_name":"BASE","official_registration_number":"000001",
            "race_date":"2098-12-02","venue":"BASE333",
            "circumference_m":333,"day":"Day1","race_no":1,"car_no":1,
            "class":"S1","style":"追","source_url":"https://example.invalid/racecard"
        },
    ]
    for i in range(1,n+1):
        reg=f"{i+100000:06d}"
        venue="H333_A" if i%2 else "H333_B"
        date=f"2099-01-{1+(i%9):02d}"
        order.append({
            "priority":i,"rider_name":f"R{i}","registration":reg,
            "future":{"date":date,"venue":venue,"circumference_bucket":"333_OR_333_33"}
        })
        matrix.append({
            "priority":i,"rider_name":f"R{i}","official_registration_number":reg,
            "historical_support":{
                "race_date":"2098-12-15","venue":"H400_A" if i%2 else "H400_B",
                "circumference_m":400,"day":"Day1","race_no":1,"car_no":1,
                "class":"S1","style":"追","source_url":"https://example.invalid/racecard"
            }
        })
        registry.append({
            "event":f"{venue}_{date}","rider":f"R{i}",
            "official_registration_number":reg,
            "prospective_day1_pre_membership":"PENDING_EXACT_POSITIVE_DAY1_RACECARD",
            "closure_status":"OPEN_PRE_CUTOFF_READINESS"
        })
        rows.append({
            "priority":i,"rider_name":f"R{i}","official_registration_number":reg,
            "race_date":date,"venue":venue,"circumference_m":333,"day":"Day1",
            "race_no":1+(i%10),"car_no":1+(i%7),"class":"S1","style":"追",
            "source_role":"FINAL_DAY1_RACECARD",
            "source_namespace":"schedule/racecard only",
            "source_title":"初日出走表",
            "source_url":"https://example.invalid/racecard",
            "captured_at_jst":"2099-01-11T12:00:00+09:00",
            "source_sha256":hashlib.sha256(f"row{i}".encode()).hexdigest(),
        })
    return {"ordered_candidates":order},{"rows":matrix},{"entries":registry},{"rows":rows,"baseline_supported_rows":baseline}


def main():
    order,matrix,registry,manifest=fixture()

    out=v3.finalize(order,matrix,registry,manifest)
    assert out["new_pass_riders"]==29
    assert out["stopped_after_29_new_pass"] is True

    six=deepcopy(manifest)
    six["rows"]=six["rows"][6:]
    assert v3.finalize(order,matrix,registry,six)["new_pass_riders"]==29

    seven=deepcopy(manifest)
    seven["rows"]=seven["rows"][7:]
    assert v3.finalize(order,matrix,registry,seven)["new_pass_riders"]==28

    bad_result=deepcopy(manifest)
    bad_result["rows"][0]["source_role"]="RESULT_PAGE"
    bad_result["rows"][0]["source_namespace"]="race result"
    badout=v3.finalize(order,matrix,registry,bad_result)
    assert any(d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE" for d in badout["decisions"])

    safe_oddspark=deepcopy(manifest)
    safe_oddspark["rows"][0]["source_url"]="https://www.oddspark.com/keirin/RaceList.do?joCode=37"
    safe_oddspark["rows"][0]["source_namespace"]="schedule/racecard"
    safe_oddspark["rows"][0]["source_title"]="初日出走表"
    safeout=v3.finalize(order,matrix,registry,safe_oddspark)
    assert safeout["new_pass_riders"]==29
    assert not any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in safeout["decisions"]
    )

    true_odds=deepcopy(manifest)
    true_odds["rows"][0]["source_url"]="https://www.oddspark.com/keirin/odds/"
    true_odds["rows"][0]["source_namespace"]="racecard odds"
    true_odds["rows"][0]["source_title"]="オッズ"
    oddsout=v3.finalize(order,matrix,registry,true_odds)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in oddsout["decisions"]
    )

    true_payout=deepcopy(manifest)
    true_payout["rows"][0]["source_url"]="https://example.invalid/payout"
    true_payout["rows"][0]["source_namespace"]="payout"
    payoutout=v3.finalize(order,matrix,registry,true_payout)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in payoutout["decisions"]
    )

    assert "trusted_pit_cutoff_jst" not in manifest["rows"][0]

    print("PASS 8/8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
