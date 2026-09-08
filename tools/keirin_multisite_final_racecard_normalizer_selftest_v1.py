#!/usr/bin/env python3
from copy import deepcopy
import hashlib

import keirin_multisite_final_racecard_normalizer_v1 as n


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def order():
    return {
        "ordered_candidates": [{
            "priority": 1,
            "rider_name": "R1",
            "registration": "100001",
            "future": {
                "date": "2099-01-10",
                "venue": "V333",
                "circumference_bucket": "333_OR_333_33",
            },
        }]
    }


def obs(source_family="CTC"):
    return {
        "source_family": source_family,
        "source_role": "FINAL_DAY1_RACECARD",
        "source_namespace": "racecard/schedule",
        "source_title": "Day1 racecard",
        "source_url": f"https://example.invalid/{source_family.lower()}/racecard",
        "source_sha256": sha(source_family),
        "captured_at_jst": "2099-01-09T20:00:00+09:00",
        "official_registration_number": "100001",
        "rider_name": "R1",
        "race_date": "2099-01-10",
        "venue": "V333",
        "day": "Day1",
        "circumference_m": 333.0,
        "race_no": 7,
        "car_no": 3,
        "class": "S1",
        "style": "追",
        "status": "ACTIVE",
    }


def must_fail(observations, reason_fragment):
    out = n.normalize(order(), observations)
    assert out["status"] == "FAIL_CLOSED", out
    blob = repr(out)
    assert reason_fragment in blob, (reason_fragment, blob)


def selftest():
    one = n.normalize(order(), [obs("CTC")])
    assert one["status"] == "PASS"
    assert one["normalized_row_count"] == 1
    assert one["normalized_rows"][0]["corroboration_count"] == 1
    assert "trusted_pit_cutoff_jst" not in one["normalized_rows"][0]

    two = n.normalize(order(), [obs("CTC"), obs("KDREAMS")])
    assert two["status"] == "PASS"
    assert two["normalized_rows"][0]["corroboration_count"] == 2

    three = n.normalize(
        order(), [obs("CTC"), obs("KDREAMS"), obs("WINTICKET")]
    )
    assert three["status"] == "PASS"
    assert three["normalized_rows"][0]["corroboration_count"] == 3

    for field, value in [
        ("race_no", 8), ("car_no", 4), ("class", "A1"), ("style", "逃")
    ]:
        x = obs("KDREAMS")
        x[field] = value
        must_fail([obs("CTC"), x], "cross_source_assignment_conflict")

    for field, value in [
        ("official_registration_number", "999999"),
        ("rider_name", "OTHER"),
        ("race_date", "2099-01-11"),
        ("venue", "OTHER"),
        ("day", "Day2"),
    ]:
        x = obs("CTC")
        x[field] = value
        must_fail([x], "FAIL_CLOSED")

    x = obs("CTC")
    x["source_namespace"] = "race result"
    must_fail([x], "forbidden_source_namespace")

    same = obs("CTC")
    must_fail([same, deepcopy(same)], "duplicate_source_observation")

    x = obs("CTC")
    x["status"] = "WITHDRAWN"
    must_fail([x], "withdrawal_or_substitution")

    return {
        "status": "PASS",
        "single_source_accept": True,
        "two_source_agreement_accept": True,
        "three_source_agreement_accept": True,
        "race_car_class_style_conflict_fail_closed": True,
        "identity_event_mismatch_fail_closed": True,
        "result_namespace_rejected": True,
        "duplicate_source_rejected": True,
        "withdrawal_rejected": True,
        "exact_cutoff_required": False,
    }


if __name__ == "__main__":
    print(selftest())
