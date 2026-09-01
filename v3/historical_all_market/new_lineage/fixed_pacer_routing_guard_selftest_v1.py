from __future__ import annotations

from copy import deepcopy

from fixed_pacer_routing_guard_v1 import assert_line_dependent_route_allowed


SHA = "a" * 64


def _standard_record() -> dict:
    return {
        "race_id": "fixture-standard-1",
        "prediction_timestamp": "2026-08-20T15:38:00+09:00",
        "decision_timestamp": "2026-08-20T16:00:00+09:00",
        "decision_cutoff_rule_id": "fixture-cutoff",
        "race_regime": "STANDARD_ORIGINAL_LINE_KEIRIN",
        "race_regime_source": "fixture",
        "race_regime_source_timestamp": "2026-08-20T15:30:00+09:00",
        "race_regime_raw_provenance_sha": SHA,
        "line_source": "fixture-pre-line",
        "line_snapshot_timestamp": "2026-08-20T15:31:00+09:00",
        "line_observation_type": "PRE_EVENT_EXPECTED_LINE",
        "line_raw_provenance_sha": SHA,
        "num_lines": 3,
        "riders": [
            {"car_no": 1, "rider_id": "r1", "active": True, "line_group_id": "L1", "line_position": 0, "line_size": 3, "is_singleton": False},
            {"car_no": 2, "rider_id": "r2", "active": True, "line_group_id": "L1", "line_position": 1, "line_size": 3, "is_singleton": False},
            {"car_no": 3, "rider_id": "r3", "active": True, "line_group_id": "L1", "line_position": 2, "line_size": 3, "is_singleton": False},
            {"car_no": 4, "rider_id": "r4", "active": True, "line_group_id": "L2", "line_position": 0, "line_size": 2, "is_singleton": False},
            {"car_no": 5, "rider_id": "r5", "active": True, "line_group_id": "L2", "line_position": 1, "line_size": 2, "is_singleton": False},
            {"car_no": 6, "rider_id": "r6", "active": True, "line_group_id": "L3", "line_position": 0, "line_size": 2, "is_singleton": False},
            {"car_no": 7, "rider_id": "r7", "active": True, "line_group_id": "L3", "line_position": 1, "line_size": 2, "is_singleton": False}
        ]
    }


def _nonstandard_record(regime: str) -> dict:
    record = _standard_record()
    record["race_regime"] = regime
    for key in (
        "line_source",
        "line_snapshot_timestamp",
        "line_observation_type",
        "line_raw_provenance_sha",
        "num_lines",
    ):
        record.pop(key, None)
    for rider in record["riders"]:
        for key in ("line_group_id", "line_position", "line_size", "is_singleton"):
            rider.pop(key, None)
    return record


def _expect_block(record: dict, model_family: str, expected_fragment: str) -> None:
    try:
        assert_line_dependent_route_allowed(record, model_family)
    except ValueError as exc:
        if expected_fragment not in str(exc):
            raise AssertionError(f"wrong block reason: {exc}") from exc
    else:
        raise AssertionError(f"route unexpectedly allowed: {model_family}:{record.get('race_regime')}")


def run() -> None:
    standard = _standard_record()
    for family in ("C1", "N1"):
        assert_line_dependent_route_allowed(standard, family)

    for regime in ("INTERNATIONAL_FIXED_PACER", "UNKNOWN_OR_OTHER"):
        record = _nonstandard_record(regime)
        for family in ("C1", "N1"):
            _expect_block(record, family, "LINE_DEPENDENT_MODEL_ROUTE_BLOCKED")

    _expect_block(standard, "C0", "UNSUPPORTED_GUARD_MODEL_FAMILY")

    malformed = deepcopy(standard)
    malformed["riders"][0].pop("line_position")
    _expect_block(malformed, "C1", "PRE_STRUCTURE_FAIL_CLOSED")

    print("FIXED_PACER_ROUTING_GUARD_SELFTEST_PASS")


if __name__ == "__main__":
    run()
