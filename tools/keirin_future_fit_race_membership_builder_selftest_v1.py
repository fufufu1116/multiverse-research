#!/usr/bin/env python3
from copy import deepcopy
import hashlib
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

b=importlib.import_module("keirin_future_fit_race_membership_builder_v1")


def finalization():
    return {
        "receipts":[
            {
                "rider":{"official_registration_number":"014537"},
                "supported_rows":{"future":{
                    "race_date":"2026-09-14","venue":"伊東","circumference_m":333,
                    "race_no":3,"car_no":2
                }},
                "result_accessed":False,"payout_accessed":False,"odds_accessed":False,
            },
            {
                "rider":{"official_registration_number":"015362"},
                "supported_rows":{"future":{
                    "race_date":"2026-09-14","venue":"伊東","circumference_m":333,
                    "race_no":3,"car_no":5
                }},
                "result_accessed":False,"payout_accessed":False,"odds_accessed":False,
            },
            {
                "rider":{"official_registration_number":"015107"},
                "supported_rows":{"future":{
                    "race_date":"2026-09-14","venue":"青森","circumference_m":400,
                    "race_no":1,"car_no":4
                }},
                "result_accessed":False,"payout_accessed":False,"odds_accessed":False,
            },
        ]
    }


def card_ito():
    riders=[
        (1,"010001","A",99.0,"S1","追"),
        (2,"014537","西村 光太",101.2,"S1","追"),
        (3,"010003","C",98.3,"S2","逃"),
        (4,"010004","D",97.1,"S2","両"),
        (5,"015362","脇本 勇希",103.4,"S1","逃"),
        (6,"010006","F",96.2,"S2","追"),
        (7,"010007","G",95.8,"S2","両"),
    ]
    return {
        "race_date":"2026-09-14","venue":"伊東","circumference_m":333,
        "day":"Day1","race_no":3,
        "source_family":"CTC",
        "source_url":"https://ctc.gr.jp/schedule/racecard/ito/3",
        "source_sha256":hashlib.sha256(b"ito3").hexdigest(),
        "captured_at_jst":"2026-09-13T20:00:00+09:00",
        "riders":[
            {
                "car_no":car,"official_registration_number":reg,"rider_name":name,
                "competition_score":score,"class":cls,"style":style
            }
            for car,reg,name,score,cls,style in riders
        ],
    }


def card_aomori():
    riders=[
        (1,"020001","A",80.0,"A1","追"),
        (2,"020002","B",82.0,"A1","逃"),
        (3,"020003","C",83.0,"A2","両"),
        (4,"015107","田頭 寛之",84.0,"A1","両"),
        (5,"020005","E",81.5,"A2","追"),
        (6,"020006","F",79.5,"A2","逃"),
        (7,"020007","G",78.5,"A2","追"),
    ]
    return {
        "race_date":"2026-09-14","venue":"青森","circumference_m":400,
        "day":"Day1","race_no":1,
        "source_family":"KDREAMS",
        "source_url":"https://keirin.kdreams.jp/aomori/racecard/example",
        "source_sha256":hashlib.sha256(b"aomori1").hexdigest(),
        "captured_at_jst":"2026-09-14T08:00:00+09:00",
        "riders":[
            {
                "car_no":car,"official_registration_number":reg,"rider_name":name,
                "competition_score":score,"class":cls,"style":style
            }
            for car,reg,name,score,cls,style in riders
        ],
    }


def must_fail(fn,contains=None):
    try:
        fn()
    except b.FitMembershipError as exc:
        if contains is not None:
            assert contains in str(exc),(contains,str(exc))
        return
    raise AssertionError("expected FitMembershipError")


def main():
    f=finalization()
    ito=card_ito()
    ao=card_aomori()

    req=b.required_future_races(f)
    assert len(req)==2
    assert ("2026-09-14","伊東",3) in req
    assert len(req[("2026-09-14","伊東",3)])==2

    out=b.build(f,[ito,ao])
    assert out["membership_complete"] is True
    assert out["required_unique_future_races"]==2
    assert out["captured_required_races"]==2
    assert out["missing_required_races"]==[]
    assert out["formula_fit_authorized"] is False
    assert out["result_join_authorized"] is False
    assert out["result_accessed"] is False

    by_key={(x["race_date"],x["venue"],x["race_no"]):x for x in out["races"]}
    i=by_key[("2026-09-14","伊東",3)]
    assert i["full_pre_rider_count"]==7
    assert i["confirmed_support_riders_in_race"]==["014537","015362"]

    incomplete=b.build(f,[ito])
    assert incomplete["membership_complete"] is False
    assert incomplete["captured_required_races"]==1
    assert len(incomplete["missing_required_races"])==1
    assert incomplete["missing_required_races"][0]["venue"]=="青森"

    car_mismatch=deepcopy(ito)
    next(x for x in car_mismatch["riders"] if x["official_registration_number"]=="014537")["car_no"]=8
    must_fail(
        lambda:b.build(f,[car_mismatch,ao]),
        "support_racecard_binding_mismatch",
    )

    missing_supported=deepcopy(ito)
    missing_supported["riders"]=[
        x for x in missing_supported["riders"]
        if x["official_registration_number"]!="015362"
    ]
    must_fail(
        lambda:b.build(f,[missing_supported,ao]),
        "support_racecard_binding_mismatch",
    )

    bad_score=deepcopy(ito)
    bad_score["riders"][0]["competition_score"]=0
    must_fail(
        lambda:b.build(f,[bad_score,ao]),
        "competition_score_must_be_positive",
    )

    nan_score=deepcopy(ito)
    nan_score["riders"][0]["competition_score"]=float("nan")
    must_fail(
        lambda:b.build(f,[nan_score,ao]),
        "must_be_finite",
    )

    bad_host=deepcopy(ito)
    bad_host["source_url"]="https://evil.example/racecard"
    must_fail(
        lambda:b.build(f,[bad_host,ao]),
        "source_family_hostname_binding_mismatch",
    )

    leaked=deepcopy(ito)
    leaked["result_order"]=[2,5,1]
    must_fail(
        lambda:b.build(f,[leaked,ao]),
        "forbidden_post_decision_field",
    )

    rider_leak=deepcopy(ito)
    rider_leak["riders"][0]["odds"]=3.2
    must_fail(
        lambda:b.build(f,[rider_leak,ao]),
        "forbidden_post_decision_field",
    )

    late=deepcopy(ito)
    late["captured_at_jst"]="2026-09-15T00:00:00+09:00"
    must_fail(
        lambda:b.build(f,[late,ao]),
        "unambiguous_post_event_next_day_or_later_capture",
    )

    dup=deepcopy(ito)
    dup["riders"][1]["official_registration_number"]=dup["riders"][0]["official_registration_number"]
    must_fail(
        lambda:b.build(f,[dup,ao]),
        "invalid_or_duplicate_registration",
    )

    bad_family=deepcopy(ito)
    bad_family["source_family"]="UNKNOWN"
    must_fail(
        lambda:b.build(f,[bad_family,ao]),
        "untrusted_source_family",
    )

    print("PASS 24/24")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
