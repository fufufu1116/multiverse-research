from reality_physics_ranges_v0 import (
    CDA_M2,
    DRIVETRAIN_EFFICIENCY,
    PEAK_MECHANICAL_POWER_W,
    RangeContractError,
    assert_no_probability_semantics,
    require_drafting_multiplier,
    require_official_track_length,
    require_rolling_resistance_runtime,
)


def must_fail(fn, *args):
    try:
        fn(*args)
    except RangeContractError:
        return
    raise AssertionError(f"expected RangeContractError: {fn.__name__}{args}")


def main():
    assert_no_probability_semantics()

    assert CDA_M2.require(0.19) == 0.19
    assert CDA_M2.require(0.31) == 0.31
    must_fail(CDA_M2.require, 0.18)
    must_fail(CDA_M2.require, 0.32)

    assert PEAK_MECHANICAL_POWER_W.require(775) == 775
    assert PEAK_MECHANICAL_POWER_W.require(2025) == 2025
    must_fail(PEAK_MECHANICAL_POWER_W.require, 2500)

    assert DRIVETRAIN_EFFICIENCY.require(0.98) == 0.98
    must_fail(DRIVETRAIN_EFFICIENCY.require, 1.01)

    assert require_drafting_multiplier("leader", 0.98) == 0.98
    assert require_drafting_multiplier("second", 0.60) == 0.60
    assert require_drafting_multiplier("later", 0.50) == 0.50
    must_fail(require_drafting_multiplier, "second", 0.90)
    must_fail(require_drafting_multiplier, "unknown", 0.60)

    for track in (333, 335, 400, 500):
        assert require_official_track_length(track) == track
    must_fail(require_official_track_length, 250)

    # Most important fail-closed check: reference-only Crr cannot become runtime truth.
    must_fail(require_rolling_resistance_runtime, 0.002)

    print("PASS_REALITY_PHYSICS_RANGE_CONTRACT_V0")


if __name__ == "__main__":
    main()
