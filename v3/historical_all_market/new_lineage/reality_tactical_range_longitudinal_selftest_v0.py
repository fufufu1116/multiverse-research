from __future__ import annotations

from reality_tactical_range_longitudinal_v0 import (
    ExpectedLineGroup,
    ExpectedLineSnapshot,
    OrdinalBand,
    RiderLongitudinalSeries,
    RiderTemporalObservation,
    TacticalScenario,
    RealityCoreFoundationError,
    assert_no_numeric_tactical_mapping,
    validate_scenario_family,
)


def must_fail(fn) -> None:
    try:
        fn()
    except RealityCoreFoundationError:
        return
    raise AssertionError("expected RealityCoreFoundationError")


def main() -> None:
    scenarios = (
        TacticalScenario("stable", {
            "line_cohesion": OrdinalBand.HIGH,
            "initiative_conflict": OrdinalBand.LOW,
            "position_competition": OrdinalBand.LOW,
            "block_or_position_defense": OrdinalBand.MEDIUM,
            "line_fragmentation": OrdinalBand.LOW,
            "switching": OrdinalBand.LOW,
            "reattachment": OrdinalBand.MEDIUM,
            "solo_transition": OrdinalBand.LOW,
        }),
        TacticalScenario("balanced", {
            "line_cohesion": OrdinalBand.MEDIUM,
            "initiative_conflict": OrdinalBand.MEDIUM,
            "position_competition": OrdinalBand.MEDIUM,
            "block_or_position_defense": OrdinalBand.MEDIUM,
            "line_fragmentation": OrdinalBand.MEDIUM,
            "switching": OrdinalBand.MEDIUM,
            "reattachment": OrdinalBand.MEDIUM,
            "solo_transition": OrdinalBand.MEDIUM,
        }),
        TacticalScenario("disruptive", {
            "line_cohesion": OrdinalBand.LOW,
            "initiative_conflict": OrdinalBand.HIGH,
            "position_competition": OrdinalBand.HIGH,
            "block_or_position_defense": OrdinalBand.HIGH,
            "line_fragmentation": OrdinalBand.HIGH,
            "switching": OrdinalBand.HIGH,
            "reattachment": OrdinalBand.LOW,
            "solo_transition": OrdinalBand.HIGH,
        }),
    )
    validate_scenario_family(scenarios)

    line = ExpectedLineSnapshot(
        race_id="r1",
        active_car_numbers=(1,2,3,4,5,6,7),
        groups=(ExpectedLineGroup((5,1,2,7)), ExpectedLineGroup((3,)), ExpectedLineGroup((4,6))),
        snapshot_timestamp="2026-09-01T16:16:47+09:00",
        decision_timestamp="2026-09-01T23:16:00+09:00",
        source_url="https://example.invalid/pre",
        provider_name="provider",
        provenance_sha="abc",
    )
    assert line.shape == (4,2,1)

    # Any structurally valid partition is allowed; no old template whitelist.
    line2 = ExpectedLineSnapshot(
        race_id="r2",
        active_car_numbers=(1,2,3,4,5,6,7),
        groups=(ExpectedLineGroup((1,2,3,4,5)), ExpectedLineGroup((6,)), ExpectedLineGroup((7,))),
        snapshot_timestamp="2026-09-01T16:00:00+09:00",
        decision_timestamp="2026-09-01T18:00:00+09:00",
        source_url="https://example.invalid/pre2",
        provider_name="provider",
        provenance_sha="def",
    )
    assert line2.shape == (5,1,1)

    must_fail(lambda: ExpectedLineSnapshot(
        race_id="bad",
        active_car_numbers=(1,2,3,4,5,6,7),
        groups=(ExpectedLineGroup((1,2,3)), ExpectedLineGroup((4,5))),
        snapshot_timestamp="2026-09-01T16:00:00+09:00",
        decision_timestamp="2026-09-01T18:00:00+09:00",
        source_url="x", provider_name="p", provenance_sha="z",
    ))
    must_fail(lambda: ExpectedLineSnapshot(
        race_id="bad2",
        active_car_numbers=(1,2,3),
        groups=(ExpectedLineGroup((1,2,3)),),
        snapshot_timestamp="2026-09-01T19:00:00+09:00",
        decision_timestamp="2026-09-01T18:00:00+09:00",
        source_url="x", provider_name="p", provenance_sha="z",
    ))

    o1 = RiderTemporalObservation(
        rider_id="rider-a",
        observation_timestamp="2026-08-01T07:00:00+09:00",
        capture_timestamp="2026-08-01T07:05:00+09:00",
        source_url="https://example.invalid/a1",
        provenance_sha="a1",
        class_at_observation="A2",
        competition_score=82.0,
    )
    o2 = RiderTemporalObservation(
        rider_id="rider-a",
        observation_timestamp="2026-09-01T07:00:00+09:00",
        capture_timestamp="2026-09-01T07:05:00+09:00",
        source_url="https://example.invalid/a2",
        provenance_sha="a2",
        class_at_observation="A2",
        competition_score=83.5,
    )
    series = RiderLongitudinalSeries("rider-a", (o1, o2))
    assert series.latest_available_by("2026-08-15T12:00:00+09:00") is o1
    assert series.latest_available_by("2026-09-01T08:00:00+09:00") is o2
    must_fail(lambda: series.latest_available_by("2026-07-01T00:00:00+09:00"))
    must_fail(lambda: RiderLongitudinalSeries("rider-a", (o2, o1)))
    must_fail(lambda: RiderTemporalObservation(
        rider_id="rider-a",
        observation_timestamp="2026-09-01T08:00:00+09:00",
        capture_timestamp="2026-09-01T07:59:00+09:00",
        source_url="x", provenance_sha="x", class_at_observation="A2",
    ))

    assert_no_numeric_tactical_mapping({"mode": "ordinal_only"})
    must_fail(lambda: assert_no_numeric_tactical_mapping({"fragmentation_probability": 0.2}))
    must_fail(lambda: assert_no_numeric_tactical_mapping({"something": 0.2}))

    print("PASS reality tactical range + longitudinal foundation selftest")


if __name__ == "__main__":
    main()
