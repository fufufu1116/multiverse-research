#!/usr/bin/env python3
from copy import deepcopy
import hashlib
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("n", HERE / "keirin_multisite_final_racecard_normalizer_v2.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def order():
    return {
        "ordered_candidates": [{
            "priority": 1,
            "rider_name": "西村 光太",
            "registration": "014537",
            "future": {
                "date": "2026-09-14",
                "venue": "伊東",
                "circumference_bucket": "333_OR_333_33",
            },
        }]
    }

def obs(family="CTC", **kw):
    d = {
        "source_family": family,
        "source_role": "FINAL_DAY1_RACECARD",
        "source_namespace": "racecard/schedule",
        "source_title": "初日出走表",
        "page_kind": "final_day1_racecard",
        "source_url": f"https://example.invalid/{family.lower()}/racecard",
        "source_sha256": sha(family),
        "captured_at_jst": "2026-09-13T20:00:00+09:00",
        "official_registration_number": "014537",
        "rider_name": "西村　光太",
        "race_date": "2026-09-14",
        "venue": "伊東競輪場",
        "day": "初日",
        "circumference_m": 333.33,
        "race_no": 7,
        "car_no": 3,
        "class": "S級1班",
        "style": "追込",
        "status": "ACTIVE",
    }
    d.update(kw)
    return d

def status(xs):
    return n.normalize(order(), xs)

def test_single():
    o=status([obs()])
    assert o["normalized_rows"][0]["fill_status"] == "SINGLE_SOURCE_READY"
    assert o["normalized_rows"][0]["class"] == "S1"
    assert o["normalized_rows"][0]["style"] == "追"
    assert o["formal_multi_source_minimum_added"] is False

def test_all_six():
    families=["CTC","KDREAMS","WINTICKET","KEIRIN.JP","CHARILOTO","ODDSPARK"]
    o=status([obs(f) for f in families])
    assert o["normalized_rows"][0]["fill_status"] == "CONSENSUS_PASS"
    assert o["normalized_rows"][0]["corroboration_count"] == 6

def test_alias_keirin_jp():
    o=status([obs("KEIRIN_JP")])
    assert o["normalized_rows"][0]["corroborating_source_families"] == ["KEIRIN.JP"]

def test_race_conflict():
    o=status([obs("CTC"),obs("KDREAMS",race_no=8)])
    assert o["status"]=="FAIL_CLOSED" and not o["normalized_rows"]

def test_car_conflict():
    assert status([obs("CTC"),obs("KDREAMS",car_no=4)])["status"]=="FAIL_CLOSED"

def test_class_conflict():
    assert status([obs("CTC"),obs("KDREAMS",**{"class":"A1"})])["status"]=="FAIL_CLOSED"

def test_style_conflict():
    assert status([obs("CTC"),obs("KDREAMS",style="逃")])["status"]=="FAIL_CLOSED"

def test_result_rejected_but_valid_source_can_survive():
    bad=obs("KDREAMS",source_namespace="race result")
    o=status([obs("CTC"),bad])
    assert o["normalized_rows"][0]["fill_status"]=="SINGLE_SOURCE_READY"
    assert any("forbidden_source_namespace" in r["reason"] for r in o["rejected_observations"])

def test_untrusted_rejected():
    o=status([obs("UNKNOWN")])
    assert not o["normalized_rows"]
    assert any("untrusted_source_family" in r["reason"] for r in o["rejected_observations"])

def test_withdrawal_blocks_candidate():
    o=status([obs("CTC"),obs("KDREAMS",status="WITHDRAWN")])
    assert o["status"]=="FAIL_CLOSED" and not o["normalized_rows"]

def test_duplicate_family_ignored_not_double_counted():
    x=obs("CTC")
    y=deepcopy(x); y["source_url"]="https://example.invalid/ctc/other"
    o=status([x,y])
    assert o["normalized_rows"][0]["corroboration_count"]==1
    assert any("duplicate_source_family" in r["reason"] for r in o["rejected_observations"])

def test_manifest_bridge():
    shell={"rows":[{
        "priority":1,"rider_name":"西村 光太","official_registration_number":"014537",
        "race_date":"2026-09-14","venue":"伊東","circumference_m":333,"day":"Day1",
        "race_no":None,"car_no":None,"class":None,"style":None
    }],"baseline_supported_rows":[]}
    out=n.build_finalizer_manifest(shell,order(),[obs("CTC"),obs("KDREAMS")])
    row=out["rows"][0]
    assert row["race_no"]==7 and row["source_role"]=="FINAL_DAY1_RACECARD"
    assert out["result_access_authorized"] is False

def main():
    tests=[v for k,v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests: t()
    print(f"PASS {len(tests)}/{len(tests)}")

if __name__=="__main__":
    main()
