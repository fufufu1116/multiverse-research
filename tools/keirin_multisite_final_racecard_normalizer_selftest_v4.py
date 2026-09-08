#!/usr/bin/env python3
from copy import deepcopy
import importlib
import pathlib
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

v4=importlib.import_module("keirin_multisite_final_racecard_normalizer_v4")
v2test=importlib.import_module("keirin_multisite_final_racecard_normalizer_selftest_v2")


def normalize(rows):
    return v4.normalize(v2test.order(),rows)


def decision(out):
    return out["decisions"][0]


def main():
    # One source family is one corroboration unit even if observed twice.
    a=v2test.obs("CTC")
    b=deepcopy(a)
    b["source_url"]="https://example.invalid/ctc/second-snapshot"
    b["source_sha256"]=v2test.sha("CTC-second")
    same=normalize([a,b])
    assert same["status"]=="READY_PARTIAL"
    assert same["normalized_row_count"]==1
    assert same["normalized_rows"][0]["corroboration_count"]==1
    assert same["normalized_rows"][0]["fill_status"]=="SINGLE_SOURCE_READY"
    assert same["corroboration_unit"]=="DISTINCT_TRUSTED_SOURCE_FAMILY"
    assert any(
        x["reason"]=="duplicate_source_family_same_assignment_deduped"
        for x in same["rejected_observations"]
    )

    # A valid assignment conflict *inside the same source family* is a hard
    # candidate failure, not "keep the first and ignore the second".
    race_conflict=normalize([
        v2test.obs("CTC",race_no=7),
        v2test.obs("CTC",race_no=8),
    ])
    assert race_conflict["status"]=="FAIL_CLOSED"
    assert race_conflict["normalized_row_count"]==0
    assert decision(race_conflict)["status"]=="CONFLICT_FAIL_CLOSED"
    assert decision(race_conflict)["reason"]=="same_source_assignment_conflict"

    car_conflict=normalize([
        v2test.obs("KDREAMS",car_no=3),
        v2test.obs("KDREAMS",car_no=4),
    ])
    assert car_conflict["status"]=="FAIL_CLOSED"
    assert not car_conflict["normalized_rows"]

    class_conflict=normalize([
        v2test.obs("WINTICKET",**{"class":"S1"}),
        v2test.obs("WINTICKET",**{"class":"A1"}),
    ])
    assert class_conflict["status"]=="FAIL_CLOSED"

    style_conflict=normalize([
        v2test.obs("CHARILOTO",style="追"),
        v2test.obs("CHARILOTO",style="逃"),
    ])
    assert style_conflict["status"]=="FAIL_CLOSED"

    # Input order cannot decide which contradictory same-family assignment wins.
    forward=normalize([
        v2test.obs("CTC",race_no=7),
        v2test.obs("CTC",race_no=8),
    ])
    reverse=normalize([
        v2test.obs("CTC",race_no=8),
        v2test.obs("CTC",race_no=7),
    ])
    assert forward["status"]==reverse["status"]=="FAIL_CLOSED"
    assert decision(forward)["reason"]==decision(reverse)["reason"]

    # An invalid RESULT namespace snapshot from CTC cannot erase a valid CTC
    # final racecard merely because it was encountered first.
    invalid_first=v2test.obs("CTC",source_namespace="race result")
    valid=v2test.obs("CTC")
    survived=normalize([invalid_first,valid])
    assert survived["normalized_row_count"]==1
    assert survived["normalized_rows"][0]["corroboration_count"]==1
    assert any(
        "forbidden_source_namespace" in x["reason"]
        for x in survived["rejected_observations"]
    )

    survived_reverse=normalize([valid,invalid_first])
    assert survived_reverse["normalized_row_count"]==1
    assert survived_reverse["normalized_rows"][0]["corroboration_count"]==1

    # Two genuinely distinct families agreeing exactly create consensus=2.
    consensus=normalize([
        v2test.obs("CTC"),
        v2test.obs("KEIRIN.JP"),
    ])
    assert consensus["status"]=="READY_PARTIAL"
    assert consensus["normalized_row_count"]==1
    assert consensus["normalized_rows"][0]["fill_status"]=="CONSENSUS_PASS"
    assert consensus["normalized_rows"][0]["corroboration_count"]==2
    assert consensus["normalized_rows"][0]["corroborating_source_families"]==["CTC","KEIRIN.JP"]

    # Alias spellings are still one KEIRIN.JP family, not two votes.
    alias=normalize([
        v2test.obs("KEIRIN.JP"),
        v2test.obs("KEIRIN_JP"),
    ])
    assert alias["normalized_rows"][0]["corroboration_count"]==1
    assert alias["normalized_rows"][0]["fill_status"]=="SINGLE_SOURCE_READY"

    alias_conflict=normalize([
        v2test.obs("KEIRIN.JP",race_no=7),
        v2test.obs("KEIRIN_JP",race_no=8),
    ])
    assert alias_conflict["status"]=="FAIL_CLOSED"

    # Existing cross-family disagreement remains a hard failure.
    cross_conflict=normalize([
        v2test.obs("CTC",race_no=7),
        v2test.obs("KDREAMS",race_no=8),
    ])
    assert cross_conflict["status"]=="FAIL_CLOSED"
    assert not cross_conflict["normalized_rows"]

    # v3 exact-integer hardening is preserved.
    bad_float=normalize([v2test.obs("CTC",race_no=7.9)])
    assert bad_float["normalized_row_count"]==0
    assert any(
        x["reason"]=="invalid_race_or_car_number"
        for x in bad_float["rejected_observations"]
    )

    # Withdrawal remains candidate-level fail closed.
    withdrawn=normalize([
        v2test.obs("CTC"),
        v2test.obs("KDREAMS",status="WITHDRAWN"),
    ])
    assert withdrawn["status"]=="FAIL_CLOSED"
    assert not withdrawn["normalized_rows"]

    print("PASS 15/15")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
