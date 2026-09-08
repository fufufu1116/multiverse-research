#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

e=importlib.import_module("keirin_support_gate_local_day1_calendar_shadow_v1")


def receipt(reg, d333, d400):
    return {
        "rider":{"name":"T","official_registration_number":reg},
        "supported_rows":{
            "333m":{
                "race_date":d333,"venue":"防府","circumference_m":333,
                "day":"Day1","race_no":1,"car_no":1,
                "registration_number":reg,"valid_pre_row_for_support":True,
            },
            "400m":{
                "race_date":d400,"venue":"川崎","circumference_m":400,
                "day":"Day1","race_no":2,"car_no":2,
                "registration_number":reg,"valid_pre_row_for_support":True,
            },
        },
        "support_decision":{
            "cross_circumference_supported_rider":True,
            "result_needed_for_support_decision":False,
        },
        "result_accessed":False,
        "target_result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "human_forecast_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
    }


def main():
    one=e.evaluate([receipt("012345","2026-09-04","2026-08-30")])
    assert one["checks"]["333_OR_333_33"]["value"]==1
    assert one["checks"]["400"]["value"]==1
    assert one["checks"]["333_OR_333_33"]["shadow_status"]=="FAIL"
    assert one["checks"]["400"]["shadow_status"]=="FAIL"
    assert one["definition_adopted"] is False
    assert one["full_gate_pass_authorized"] is False

    two=e.evaluate([
        receipt("012345","2026-09-04","2026-08-30"),
        receipt("012346","2026-09-14","2026-09-07"),
    ])
    assert two["checks"]["333_OR_333_33"]["value"]==2
    assert two["checks"]["400"]["value"]==2
    assert two["checks"]["333_OR_333_33"]["shadow_status"]=="PASS"
    assert two["checks"]["400"]["shadow_status"]=="PASS"
    assert two["both_calendar_dimensions_shadow_pass"] is True
    assert two["definition_adopted"] is False
    assert two["full_gate_pass_authorized"] is False
    assert two["result_accessed"] is False
    assert two["odds_accessed"] is False
    assert two["runtime"] is False

    three=e.evaluate([
        receipt("012345","2026-09-04","2026-08-30"),
        receipt("012346","2026-09-14","2026-09-07"),
        receipt("012347","2026-09-15","2026-09-14"),
    ])
    assert three["checks"]["333_OR_333_33"]["distinct_local_day1_race_dates"]==[
        "2026-09-04","2026-09-14","2026-09-15"
    ]
    assert three["checks"]["400"]["distinct_local_day1_race_dates"]==[
        "2026-08-30","2026-09-07","2026-09-14"
    ]
    assert three["full_gate_pass_authorized"] is False

    bad=receipt("012345","2026-09-04","2026-08-30")
    bad["odds_accessed"]=True
    try:
        e.evaluate([bad])
    except ValueError as exc:
        assert "FORBIDDEN_odds_accessed" in str(exc)
    else:
        raise AssertionError("forbidden odds flag must fail closed")

    print("PASS 20/20")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
