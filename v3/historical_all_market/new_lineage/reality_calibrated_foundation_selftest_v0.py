from __future__ import annotations

import inspect

import reality_calibrated_foundation_v0 as foundation


DECISION = "2026-09-01T10:00:00+09:00"
EVENT = "2026-09-01T11:00:00+09:00"
EARLIER = "2026-09-01T09:00:00+09:00"
FUTURE = "2026-09-01T10:01:00+09:00"


def _program(regime: str = "STANDARD_ORIGINAL_LINE_KEIRIN") -> foundation.ProgramRegimeSnapshot:
    return foundation.ProgramRegimeSnapshot(
        race_id="FOUNDATION_TEST_R1",
        event_datetime=EVENT,
        prediction_timestamp=EARLIER,
        decision_timestamp=DECISION,
        decision_cutoff_rule_id="TEST_DECISION_RULE",
        venue_id="TEST_VENUE",
        race_grade="FI",
        race_class_band="A1_A2",
        race_stage="PRELIMINARY",
        race_regime=regime,
        field_size=7,
        sex_scope="MEN",
        program_source="OFFICIAL_TEST_FIXTURE_METADATA",
        program_source_class="OFFICIAL_PROGRAM",
        program_source_timestamp=EARLIER,
        program_provenance_sha="program-fixture-sha",
    )


def _venue() -> foundation.VenueEnvironmentSnapshot:
    return foundation.VenueEnvironmentSnapshot(
        venue_id="TEST_VENUE",
        bank_length_m=400.0,
        venue_source="OFFICIAL_TEST_MASTER",
        venue_source_class="OFFICIAL_MASTER",
        venue_provenance_sha="venue-fixture-sha",
        home_straight_m=50.0,
        bank_cant_deg=30.0,
        weather="CLEAR",
        temperature_c=25.0,
        wind_speed_mps=2.0,
        wind_direction="N",
        environment_source="AUTHORIZED_PRE_TEST_FIXTURE",
        environment_source_class="PRE_EMPIRICAL_AUTHORIZED",
        environment_observation_timestamp=EARLIER,
        environment_provenance_sha="environment-fixture-sha",
    )


def _riders() -> tuple[foundation.RiderIdentitySnapshot, ...]:
    return tuple(
        foundation.RiderIdentitySnapshot(
            rider_id=f"RIDER_{car}",
            car_no=car,
            class_at_cutoff="A1",
            active_status_at_cutoff=True,
            identity_source="OFFICIAL_TEST_PROGRAM",
            identity_source_class="OFFICIAL_PROGRAM",
            identity_snapshot_timestamp=EARLIER,
            identity_provenance_sha=f"identity-{car}-sha",
            registration_region_or_official_affiliation="TEST_REGION",
        )
        for car in range(1, 8)
    )


def _history(timestamp: str = EARLIER) -> tuple[foundation.RiderPreHistorySnapshot, ...]:
    return tuple(
        foundation.RiderPreHistorySnapshot(
            rider_id=f"RIDER_{car}",
            snapshot_timestamp=timestamp,
            source="AUTHORIZED_POINT_IN_TIME_TEST_FIXTURE",
            source_class="PRE_EMPIRICAL_AUTHORIZED",
            provenance_sha=f"history-{car}-sha",
            competition_score=90.0 + car,
            win_rate=0.10,
            quinella_rate=0.20,
            trio_rate=0.30,
            S=1.0,
            H=2.0,
            B=3.0,
            nige=1.0,
            makuri=1.0,
            sashi=1.0,
            mark=1.0,
        )
        for car in range(1, 8)
    )


def _line(
    *,
    observation_type: str = "LEGSHOW_OBSERVED_LINE",
    timestamp: str = EARLIER,
    bad_position: bool = False,
) -> foundation.LineSnapshot:
    groups = {
        "L1": [1, 2, 3],
        "L2": [4, 5],
        "L3": [6, 7],
    }
    members = []
    for group_id, cars in groups.items():
        for pos, car in enumerate(cars):
            if bad_position and group_id == "L2" and car == 5:
                pos = 2
            members.append(
                foundation.LineMemberSnapshot(
                    rider_id=f"RIDER_{car}",
                    car_no=car,
                    line_group_id=group_id,
                    line_position=pos,
                    line_size=len(cars),
                    is_singleton=False,
                )
            )
    return foundation.LineSnapshot(
        race_id="FOUNDATION_TEST_R1",
        line_observation_type=observation_type,
        line_source="AUTHORIZED_LINE_TEST_FIXTURE",
        line_source_class="PRE_EMPIRICAL_AUTHORIZED",
        line_snapshot_timestamp=timestamp,
        line_raw_provenance_sha="line-fixture-sha",
        num_lines=3,
        members=tuple(members),
    )


def _snapshot(
    *,
    regime: str = "STANDARD_ORIGINAL_LINE_KEIRIN",
    history_timestamp: str = EARLIER,
    line: foundation.LineSnapshot | None = None,
) -> foundation.RaceRealityPreSnapshot:
    return foundation.RaceRealityPreSnapshot(
        program=_program(regime),
        venue_environment=_venue(),
        riders=_riders(),
        rider_history=_history(history_timestamp),
        line_snapshot=_line() if line is None else line,
    )


def _expect_fail(label: str, fn) -> None:
    try:
        fn()
    except foundation.RealityFoundationError:
        return
    raise AssertionError(f"expected_fail:{label}")


def main() -> None:
    foundation.validate_race_pre_snapshot(_snapshot(), require_actionable_line=True)

    _expect_fail(
        "future_history",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(history_timestamp=FUTURE), require_actionable_line=True
        ),
    )
    _expect_fail(
        "future_line",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(line=_line(timestamp=FUTURE)), require_actionable_line=True
        ),
    )
    _expect_fail(
        "post_race_line_label",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(line=_line(observation_type="POST_RACE_RECONSTRUCTED_LINE")),
            require_actionable_line=True,
        ),
    )
    _expect_fail(
        "unknown_regime_actionable_line",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(regime="UNKNOWN_OR_OTHER"), require_actionable_line=True
        ),
    )
    _expect_fail(
        "international_fixed_pacer_line_semantics",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(regime="INTERNATIONAL_FIXED_PACER"), require_actionable_line=True
        ),
    )
    _expect_fail(
        "noncontiguous_line_position",
        lambda: foundation.validate_race_pre_snapshot(
            _snapshot(line=_line(bad_position=True)), require_actionable_line=True
        ),
    )

    no_line = foundation.RaceRealityPreSnapshot(
        program=_program(),
        venue_environment=_venue(),
        riders=_riders(),
        rider_history=_history(),
        line_snapshot=None,
    )
    foundation.validate_race_pre_snapshot(no_line, require_actionable_line=False)
    _expect_fail(
        "missing_actionable_line",
        lambda: foundation.validate_race_pre_snapshot(no_line, require_actionable_line=True),
    )

    capabilities = foundation.foundation_capabilities()
    assert capabilities["foundation_only"] is True
    assert capabilities["truth_generator_implemented"] is False
    assert capabilities["outcome_generation_implemented"] is False
    assert capabilities["latent_state_generation_implemented"] is False
    assert capabilities["model_comparison_implemented"] is False
    assert capabilities["real_data_collection_implemented"] is False
    assert capabilities["engineering_defaults_inherited"] is False

    source = inspect.getsource(foundation)
    forbidden_import_or_call_tokens = (
        "import random",
        "world_joint_distribution(",
        "pl_top3_from_runner_utilities(",
        "conditional_top3_from_context_logits(",
        "RESULT/PAYOUT",
        "ECON_HOLDOUT1000",
    )
    for token in forbidden_import_or_call_tokens:
        assert token not in source, f"forbidden_foundation_token:{token}"

    print("KEIRIN_REALITY_CALIBRATED_FOUNDATION_V0_SELFTEST_PASS")


if __name__ == "__main__":
    main()
