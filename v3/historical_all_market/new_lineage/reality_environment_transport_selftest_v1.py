from reality_environment_transport_v1 import (
    EnvironmentEvidenceKind,
    EnvironmentObservation,
    EnvironmentUseRole,
    RealityEnvironmentError,
    validate_environment_use,
    weather_is_required_for_reality_baseline,
)


def expect_fail(fn, label: str) -> None:
    try:
        fn()
    except RealityEnvironmentError:
        return
    raise AssertionError(f"expected failure: {label}")


def obs(**overrides):
    data = dict(
        venue_id="TEST_OUTDOOR",
        evidence_kind=EnvironmentEvidenceKind.OBSERVED_OFFICIAL_STATION,
        observation_timestamp="2026-09-01T15:00:00+09:00",
        capture_timestamp="2026-09-01T15:05:00+09:00",
        decision_timestamp="2026-09-01T15:20:00+09:00",
        source_url="https://example.invalid/official-observation",
        source_class="OFFICIAL_OBSERVATION",
        provenance_sha="abc123",
        venue_station_mapping_source="venue-station-map-v1",
        wind_speed_mps=3.0,
        wind_direction="N",
        temperature_c=28.0,
        precipitation_mm=0.0,
    )
    data.update(overrides)
    return EnvironmentObservation(**data)


assert weather_is_required_for_reality_baseline() is False
validate_environment_use(EnvironmentUseRole.NO_ENVIRONMENT_BASELINE, None, venue_is_indoor_or_wind_shielded=False)

expect_fail(
    lambda: EnvironmentObservation(
        venue_id="X",
        evidence_kind=EnvironmentEvidenceKind.FORECAST,
        observation_timestamp="2026-09-01T15:00:00+09:00",
        capture_timestamp="2026-09-01T14:00:00+09:00",
        decision_timestamp="2026-09-01T15:20:00+09:00",
        source_url="https://example.invalid/forecast",
        source_class="FORECAST",
        provenance_sha="forecastsha",
        venue_station_mapping_source="map",
    ),
    "forecast rejected",
)
expect_fail(
    lambda: obs(capture_timestamp="2026-09-01T15:25:00+09:00"),
    "captured after decision rejected",
)
expect_fail(
    lambda: validate_environment_use(
        EnvironmentUseRole.NO_ENVIRONMENT_BASELINE,
        obs(),
        venue_is_indoor_or_wind_shielded=False,
    ),
    "baseline carrying weather rejected",
)
validate_environment_use(
    EnvironmentUseRole.OPTIONAL_PHYSICS_SENSITIVITY,
    obs(),
    venue_is_indoor_or_wind_shielded=False,
    max_observation_age_seconds=1800,
)
expect_fail(
    lambda: validate_environment_use(
        EnvironmentUseRole.OPTIONAL_PHYSICS_SENSITIVITY,
        obs(),
        venue_is_indoor_or_wind_shielded=False,
        max_observation_age_seconds=None,
    ),
    "missing prespecified staleness limit rejected",
)
expect_fail(
    lambda: validate_environment_use(
        EnvironmentUseRole.OPTIONAL_PHYSICS_SENSITIVITY,
        obs(),
        venue_is_indoor_or_wind_shielded=True,
        max_observation_age_seconds=1800,
    ),
    "outdoor wind injected to indoor venue rejected",
)
print("PASS reality_environment_transport_selftest_v1")
