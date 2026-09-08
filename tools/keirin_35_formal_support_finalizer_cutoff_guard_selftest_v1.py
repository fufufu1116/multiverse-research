#!/usr/bin/env python3
from copy import deepcopy
import hashlib

from keirin_35_formal_support_finalizer_v1 import selftest as base_selftest
from keirin_35_formal_support_finalizer_cutoff_guard_v1 import (
    CutoffBindingError,
    validate_cutoff_bindings,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _fixture():
    future_pre = {
        "rows": [
            {
                "official_registration_number": "100001",
                "rider_name": "R1",
                "race_date": "2099-01-10",
                "venue": "V333_A",
                "captured_at_jst": "2099-01-10T07:30:00+09:00",
                "trusted_pit_cutoff_jst": "2099-01-10T08:00:00+09:00",
            },
            {
                "official_registration_number": "100002",
                "rider_name": "R2",
                "race_date": "2099-01-11",
                "venue": "V400_A",
                "captured_at_jst": "2099-01-11T07:45:00+09:00",
                "trusted_pit_cutoff_jst": "2099-01-11T08:00:00+09:00",
            },
        ]
    }
    cutoff_manifest = {
        "record": "SYNTHETIC_CUTOFF_BINDINGS",
        "event_bindings": [
            {
                "venue": "V333_A",
                "race_date": "2099-01-10",
                "status": "LOCKED_TRUSTED_PRE_CUTOFF",
                "trusted_pit_cutoff_jst": "2099-01-10T08:00:00+09:00",
                "cutoff_source_url": "https://example.invalid/schedule-a",
                "cutoff_source_sha256": _sha("schedule-a"),
                "cutoff_source_captured_at_jst": "2099-01-09T12:00:00+09:00",
            },
            {
                "venue": "V400_A",
                "race_date": "2099-01-11",
                "status": "LOCKED_TRUSTED_PRE_CUTOFF",
                "trusted_pit_cutoff_jst": "2099-01-11T08:00:00+09:00",
                "cutoff_source_url": "https://example.invalid/schedule-b",
                "cutoff_source_sha256": _sha("schedule-b"),
                "cutoff_source_captured_at_jst": "2099-01-10T12:00:00+09:00",
            },
        ],
    }
    return future_pre, cutoff_manifest


def _must_fail(future_pre, manifest, expected_fragment: str):
    try:
        validate_cutoff_bindings(future_pre, manifest)
    except CutoffBindingError as exc:
        assert expected_fragment in str(exc), (expected_fragment, str(exc))
        return
    raise AssertionError(f"expected failure containing {expected_fragment}")


def selftest():
    assert base_selftest()["status"] == "PASS"

    future_pre, manifest = _fixture()
    passed = validate_cutoff_bindings(future_pre, manifest)
    assert passed["status"] == "PASS"
    assert passed["checked_rows"] == 2
    assert len(passed["checked_events"]) == 2

    tampered = deepcopy(future_pre)
    tampered["rows"][0]["trusted_pit_cutoff_jst"] = "2099-01-10T09:00:00+09:00"
    _must_fail(tampered, manifest, "row_cutoff_not_exact_binding")

    late = deepcopy(future_pre)
    late["rows"][0]["captured_at_jst"] = "2099-01-10T08:00:01+09:00"
    _must_fail(late, manifest, "row_captured_after_bound_cutoff")

    unlocked = deepcopy(manifest)
    unlocked["event_bindings"][0]["status"] = "PENDING"
    _must_fail(future_pre, unlocked, "cutoff_binding_not_locked")

    source_late = deepcopy(manifest)
    source_late["event_bindings"][0]["cutoff_source_captured_at_jst"] = (
        "2099-01-10T08:00:01+09:00"
    )
    _must_fail(future_pre, source_late, "cutoff_source_captured_after_cutoff")

    wrong_zone = deepcopy(future_pre)
    wrong_zone["rows"][0]["captured_at_jst"] = "2099-01-09T22:30:00+00:00"
    _must_fail(wrong_zone, manifest, "jst_offset_required_row_captured_at_jst")

    return {
        "status": "PASS",
        "base_finalizer_selftest": "PASS",
        "cutoff_guard_positive_case": "PASS",
        "tampered_cutoff_fail_closed": "PASS",
        "late_row_fail_closed": "PASS",
        "unlocked_binding_fail_closed": "PASS",
        "late_cutoff_source_fail_closed": "PASS",
        "non_jst_timestamp_fail_closed": "PASS",
    }


if __name__ == "__main__":
    print(selftest())
