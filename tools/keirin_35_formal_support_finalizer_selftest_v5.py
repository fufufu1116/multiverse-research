#!/usr/bin/env python3
"""Isolated PRE-only compatibility selftest for finalizer v5."""

from copy import deepcopy
import hashlib
import importlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
v5 = importlib.import_module("keirin_35_formal_support_finalizer_v5")


def fixture(n=35):
    order=[]; matrix=[]; registry=[]; rows=[]; baseline=[
        {
            "rider_name":"BASE","registration_number":"000001",
            "race_date":"2098-12-01","venue":"BASE400",
            "circumference_m":400,"day":"Day1","race_no":1,"car_no":1,
            "class":"S1","style":"追","source_url":"https://example.invalid/racecard"
        },
        {
            "rider_name":"BASE","registration_number":"000001",
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
            "historical_row":{
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

    out=v5.finalize(order,matrix,registry,manifest)
    assert out["new_pass_riders"]==29
    assert out["stopped_after_29_new_pass"] is True

    six=deepcopy(manifest)
    six["rows"]=six["rows"][6:]
    assert v5.finalize(order,matrix,registry,six)["new_pass_riders"]==29

    seven=deepcopy(manifest)
    seven["rows"]=seven["rows"][7:]
    assert v5.finalize(order,matrix,registry,seven)["new_pass_riders"]==28

    bad_result=deepcopy(manifest)
    bad_result["rows"][0]["source_role"]="RESULT_PAGE"
    bad_result["rows"][0]["source_namespace"]="race result"
    badout=v5.finalize(order,matrix,registry,bad_result)
    assert any(d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE" for d in badout["decisions"])

    safe_oddspark=deepcopy(manifest)
    safe_oddspark["rows"][0]["source_url"]="https://www.oddspark.com/keirin/RaceList.do?joCode=37"
    safe_oddspark["rows"][0]["source_namespace"]="schedule/racecard"
    safe_oddspark["rows"][0]["source_title"]="初日出走表"
    safeout=v5.finalize(order,matrix,registry,safe_oddspark)
    assert safeout["new_pass_riders"]==29
    assert not any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in safeout["decisions"]
    )

    true_odds=deepcopy(manifest)
    true_odds["rows"][0]["source_url"]="https://www.oddspark.com/keirin/odds/"
    true_odds["rows"][0]["source_namespace"]="racecard odds"
    true_odds["rows"][0]["source_title"]="オッズ"
    oddsout=v5.finalize(order,matrix,registry,true_odds)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in oddsout["decisions"]
    )

    true_payout=deepcopy(manifest)
    true_payout["rows"][0]["source_url"]="https://example.invalid/payout"
    true_payout["rows"][0]["source_namespace"]="payout"
    payoutout=v5.finalize(order,matrix,registry,true_payout)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in payoutout["decisions"]
    )

    true_comment=deepcopy(manifest)
    true_comment["rows"][0]["source_url"]="https://example.invalid/comments"
    true_comment["rows"][0]["source_namespace"]="comments"
    commentout=v5.finalize(order,matrix,registry,true_comment)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in commentout["decisions"]
    )

    true_prediction=deepcopy(manifest)
    true_prediction["rows"][0]["source_url"]="https://example.invalid/prediction"
    true_prediction["rows"][0]["source_namespace"]="prediction"
    predictionout=v5.finalize(order,matrix,registry,true_prediction)
    assert any(
        d.get("priority")==1 and d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"
        for d in predictionout["decisions"]
    )

    assert "trusted_pit_cutoff_jst" not in manifest["rows"][0]

    assert out["counts_reached"] is True
    assert out["unambiguous_support_gate_pass"] is True
    assert out["complete_support_gate_pass"] is False
    assert out["status"] == "COUNTS_30R_60ROWS_UNAMBIGUOUS_GATES_PASS_CALENDAR_BLOCK_PENDING_PR177"

    # Pathological concentration must not be mislabeled as support-gate PASS.
    co,cm,cr,cp=fixture()
    for c in co["ordered_candidates"]:
        c["future"]["venue"]="MEGA"
    for row in cm["rows"]:
        row["historical_row"]["venue"]="MEGA"
    for e in cr["entries"]:
        _,date=e["event"].rsplit("_",1)
        e["event"]=f"MEGA_{date}"
    for row in cp["rows"]:
        row["venue"]="MEGA"
    concentrated=v5.finalize(co,cm,cr,cp)
    assert concentrated["counts_reached"] is True
    assert concentrated["unambiguous_support_gate_pass"] is False
    assert concentrated["status"] == "COUNTS_REACHED_UNAMBIGUOUS_SUPPORT_GATE_FAIL_CLOSED"

    # Actual normalizer-v2 -> finalizer-v5 bridge with one trusted PRE source/candidate.
    normalizer = importlib.import_module("keirin_multisite_final_racecard_normalizer_v2")
    bo,bm,br,bp=fixture()
    shell=deepcopy(bp)
    observations=[]
    for row in bp["rows"]:
        o=deepcopy(row)
        o["source_family"]="CTC"
        o["page_kind"]="final_day1_racecard"
        o["status"]="ACTIVE"
        observations.append(o)
        row["race_no"]=None
        row["car_no"]=None
        row["class"]=None
        row["style"]=None
        row["source_url"]=None
        row["captured_at_jst"]=None
        row["source_sha256"]=None
    bridged=normalizer.build_finalizer_manifest(shell,bo,observations)
    bridge_out=v5.finalize(bo,bm,br,bridged)
    assert bridge_out["new_pass_riders"] == 29
    assert bridge_out["unambiguous_support_gate_pass"] is True

    print("PASS 13/13")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
