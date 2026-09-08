#!/usr/bin/env python3
import hashlib
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("normalizer", HERE / "keirin_final_racecard_consensus_normalizer_v1.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

H = hashlib.sha256(b"x").hexdigest()

EXPECTED = {
    "priority": 1,
    "rider_name": "西村 光太",
    "official_registration_number": "014537",
    "race_date": "2026-09-14",
    "venue": "伊東",
    "circumference_m": 333,
    "day": "Day1",
    "race_no": None,
    "car_no": None,
    "class": None,
    "style": None,
    "source_url": None,
    "captured_at_jst": None,
    "source_sha256": None,
}

def obs(source="ctc", **kw):
    d = {
        "source_name": source,
        "page_kind": "final_day1_racecard",
        "official_registration_number": "014537",
        "rider_name": "西村　光太",
        "race_date": "2026-09-14",
        "venue": "伊東競輪場",
        "day": "初日",
        "circumference_m": 333.33,
        "race_no": 8,
        "car_no": 2,
        "class": "S級1班",
        "style": "追込",
        "source_url": f"https://example.test/{source}/racecard",
        "captured_at_jst": "2026-09-13T18:00:00+09:00",
        "source_sha256": H,
        "source_title": "初日出走表",
    }
    d.update(kw)
    return d

def test_four_source_consensus():
    r = m.decide_candidate(EXPECTED, [obs(s) for s in ("ctc","kdreams","winticket","keirin_jp")])
    assert r["status"] == "CONSENSUS_PASS"
    assert r["finalizer_row"]["race_no"] == 8
    assert r["finalizer_row"]["class"] == "S1"
    assert r["finalizer_row"]["style"] == "追"
    assert r["finalizer_row"]["source_role"] == "FINAL_DAY1_RACECARD"

def test_two_source_consensus():
    assert m.decide_candidate(EXPECTED, [obs("ctc"), obs("winticket")])["status"] == "CONSENSUS_PASS"

def test_single_source_ready_not_new_blocker():
    r = m.decide_candidate(EXPECTED, [obs("ctc")])
    assert r["status"] == "SINGLE_SOURCE_READY"
    assert r["formal_blocker_added"] is False
    assert r["finalizer_row"] is not None

def test_race_conflict():
    r = m.decide_candidate(EXPECTED, [obs("ctc"), obs("kdreams", race_no=9)])
    assert r["status"] == "CONFLICT_FAIL_CLOSED"
    assert r["finalizer_row"] is None

def test_car_conflict():
    assert m.decide_candidate(EXPECTED, [obs("ctc"), obs("kdreams", car_no=7)])["status"] == "CONFLICT_FAIL_CLOSED"

def test_identity_mismatch_rejected():
    r = m.decide_candidate(EXPECTED, [obs("ctc", official_registration_number="999999")])
    assert r["status"] == "NOT_READY"
    assert "locked_candidate_mismatch" in r["rejected_sources"][0]["reason"]

def test_forbidden_result_page_rejected():
    r = m.decide_candidate(EXPECTED, [obs("ctc", page_kind="result")])
    assert r["status"] == "NOT_READY"
    assert "forbidden_page_kind" in r["rejected_sources"][0]["reason"]

def test_missing_provenance_rejected():
    r = m.decide_candidate(EXPECTED, [obs("ctc", source_sha256="")])
    assert r["status"] == "NOT_READY"
    assert "invalid_source_sha256" in r["rejected_sources"][0]["reason"]

def test_duplicate_source_not_counted_twice():
    r = m.decide_candidate(EXPECTED, [obs("ctc"), obs("ctc")])
    assert r["status"] == "SINGLE_SOURCE_READY"
    assert r["accepted_sources"] == ["ctc"]
    assert any(x["reason"] == "duplicate_source_observation" for x in r["rejected_sources"])

def main():
    tests = [v for k,v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"PASS {len(tests)}/{len(tests)}")

if __name__ == "__main__":
    main()
