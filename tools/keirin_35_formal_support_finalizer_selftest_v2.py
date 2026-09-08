#!/usr/bin/env python3
from copy import deepcopy
import hashlib

import keirin_35_formal_support_finalizer_v2 as v2


def fixture():
    order, matrix, registry, rows = [], [], [], []
    baseline = [
        {"registration_number":"900001","venue":"V400_BASE","circumference_m":400},
        {"registration_number":"900001","venue":"V333_BASE","circumference_m":333},
    ]
    for i in range(1,36):
        reg=f"{100000+i:06d}"
        venue="F333_A" if i<=18 else "F333_B"
        date="2099-01-10"
        order.append({
            "priority":i,"rider_name":f"R{i}","registration":reg,
            "future":{"date":date,"venue":venue,"circumference_bucket":"333_OR_333_33"},
        })
        matrix.append({
            "rider_name":f"R{i}","official_registration_number":reg,
            "historical_row":{
                "race_date":"2099-01-01","venue":"H400_A" if i%2 else "H400_B",
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
            "rider_name":f"R{i}","official_registration_number":reg,
            "race_date":date,"venue":venue,"circumference_m":333,
            "day":"Day1","race_no":1+(i%10),"car_no":1+(i%7),
            "class":"S1","style":"追","source_role":"FINAL_DAY1_RACECARD",
            "source_namespace":"schedule/racecard only",
            "source_url":"https://example.invalid/racecard",
            "captured_at_jst":"2099-01-11T12:00:00+09:00",
            "source_sha256":hashlib.sha256(f"row{i}".encode()).hexdigest(),
        })
    return {"ordered_candidates":order},{"rows":matrix},{"entries":registry},{"rows":rows,"baseline_supported_rows":baseline}


def selftest():
    order,matrix,registry,manifest=fixture()
    out=v2.finalize(order,matrix,registry,manifest)
    assert out["new_pass_riders"]==29
    assert out["stopped_after_29_new_pass"] is True

    six=deepcopy(manifest)
    six["rows"]=six["rows"][6:]
    assert v2.finalize(order,matrix,registry,six)["new_pass_riders"]==29

    seven=deepcopy(manifest)
    seven["rows"]=seven["rows"][7:]
    assert v2.finalize(order,matrix,registry,seven)["new_pass_riders"]==28

    bad=deepcopy(manifest)
    bad["rows"][0]["source_role"]="RESULT_PAGE"
    bad["rows"][0]["source_namespace"]="race result"
    badout=v2.finalize(order,matrix,registry,bad)
    assert any(d.get("reason")=="SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE" for d in badout["decisions"])

    no_cutoff=manifest["rows"][0]
    assert "trusted_pit_cutoff_jst" not in no_cutoff

    return {
        "status":"PASS",
        "exact_cutoff_not_required":True,
        "all_valid_stops_after_29":True,
        "six_failures_tolerated":True,
        "seven_failures_target_not_reached":True,
        "result_page_rejected":True,
    }


if __name__=="__main__":
    print(selftest())
