from reality_tactical_transport_v0 import (
    LineMember,
    LineObservationType,
    LineSnapshot,
    RealityTransportError,
    TacticalState,
    WeatherObservation,
    validate_tactical_transition,
)


def expect_fail(fn):
    try:
        fn()
    except RealityTransportError:
        return
    raise AssertionError("expected RealityTransportError")


def main() -> None:
    validate_tactical_transition(TacticalState.PRE_START_LINE_INTENT, TacticalState.INITIAL_POSITION_ACQUISITION)
    validate_tactical_transition(TacticalState.LINE_FRAGMENTATION, TacticalState.SWITCHING)
    validate_tactical_transition(TacticalState.SWITCHING, TacticalState.REATTACHMENT)
    validate_tactical_transition(TacticalState.FINAL_SPRINT_OR_OVERTAKE, TacticalState.TERMINAL_FINISH)
    expect_fail(lambda: validate_tactical_transition(TacticalState.PRE_START_LINE_INTENT, TacticalState.TERMINAL_FINISH))
    expect_fail(lambda: validate_tactical_transition(TacticalState.TERMINAL_FINISH, TacticalState.LINE_MAINTENANCE))

    members = (
        LineMember("r1", "L1", 1, 2),
        LineMember("r2", "L1", 2, 2),
        LineMember("r3", "L2", 1, 1),
    )
    expected = LineSnapshot(
        race_id="demo",
        observation_type=LineObservationType.PRE_EVENT_EXPECTED_LINE,
        snapshot_timestamp="2026-09-01T15:30:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        source_url="https://example.invalid/expected",
        source_class="PRE_PUBLIC_PROVIDER_EXPECTED_LINE",
        provenance_sha="expected-sha",
        active_rider_ids=("r1", "r2", "r3"),
        members=members,
    )
    assert not expected.is_observed_legshow

    observed = LineSnapshot(
        race_id="demo",
        observation_type=LineObservationType.LEGSHOW_OBSERVED_LINE,
        snapshot_timestamp="2026-09-01T15:50:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        source_url="https://example.invalid/legshow",
        source_class="OFFICIAL_OR_AUTHORIZED_LEGSHOW_OBSERVATION",
        provenance_sha="legshow-sha",
        active_rider_ids=("r1", "r2", "r3"),
        members=members,
    )
    assert observed.is_observed_legshow
    assert expected.observation_type != observed.observation_type

    expect_fail(lambda: LineSnapshot(
        race_id="demo",
        observation_type=LineObservationType.POST_RACE_RECONSTRUCTED_LINE,
        snapshot_timestamp="2026-09-01T16:30:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        source_url="x",
        source_class="POST_RACE",
        provenance_sha="x",
        active_rider_ids=("r1",),
        members=(LineMember("r1", "L1", 1, 1),),
    ))

    expect_fail(lambda: LineSnapshot(
        race_id="demo",
        observation_type=LineObservationType.LEGSHOW_OBSERVED_LINE,
        snapshot_timestamp="2026-09-01T16:01:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        source_url="x",
        source_class="LEGSHOW",
        provenance_sha="x",
        active_rider_ids=("r1",),
        members=(LineMember("r1", "L1", 1, 1),),
    ))

    WeatherObservation(
        venue_id="MATSUDO",
        station_id="JMA_EXPLICIT_MAPPING_REQUIRED",
        observation_timestamp="2026-09-01T15:00:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        capture_timestamp="2026-09-01T15:10:00+09:00",
        wind_speed_mps=3.2,
        wind_direction="S",
        temperature_c=31.0,
        precipitation_mm=0.0,
        source_url="https://www.data.jma.go.jp/",
        source_class="OFFICIAL_JMA_OBSERVATION",
        provenance_sha="weather-sha",
        venue_station_mapping_source="EXPLICIT_MAPPING_PLACEHOLDER_FOR_SELFTEST_ONLY",
    )

    expect_fail(lambda: WeatherObservation(
        venue_id="MATSUDO",
        station_id="JMA",
        observation_timestamp="2026-09-01T16:01:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        capture_timestamp="2026-09-01T16:02:00+09:00",
        wind_speed_mps=3.2,
        wind_direction="S",
        temperature_c=31.0,
        precipitation_mm=0.0,
        source_url="https://www.data.jma.go.jp/",
        source_class="OFFICIAL_JMA_OBSERVATION",
        provenance_sha="weather-sha",
        venue_station_mapping_source="mapping",
    ))

    expect_fail(lambda: WeatherObservation(
        venue_id="MATSUDO",
        station_id="JMA",
        observation_timestamp="2026-09-01T15:00:00+09:00",
        decision_timestamp="2026-09-01T16:00:00+09:00",
        capture_timestamp="2026-09-01T15:10:00+09:00",
        wind_speed_mps=3.2,
        wind_direction=None,
        temperature_c=31.0,
        precipitation_mm=0.0,
        source_url="https://www.data.jma.go.jp/",
        source_class="OFFICIAL_JMA_OBSERVATION",
        provenance_sha="weather-sha",
        venue_station_mapping_source="mapping",
    ))

    print("PASS_REALITY_TACTICAL_TRANSPORT_V0_MECHANICAL_SELFTEST")


if __name__ == "__main__":
    main()
