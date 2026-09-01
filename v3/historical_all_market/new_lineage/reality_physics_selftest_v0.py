"""Source-independent mechanical selftest for reality_physics_core_v0.

No network, no real outcomes, no candidate models, no stochastic fitting.
"""

from __future__ import annotations

from math import isclose

from reality_physics_core_v0 import (
    DraftingContext,
    Environment,
    KinematicState,
    PhysicsInputError,
    RiderPhysics,
    TrackGeometry,
    aerodynamic_drag_force_n,
    centripetal_force_required_n,
    ideal_bank_angle_deg,
    power_breakdown,
)


def expect_raises(fn) -> None:
    try:
        fn()
    except PhysicsInputError:
        return
    raise AssertionError("expected PhysicsInputError")


def main() -> None:
    # Official active bank-length classes are accepted as structural support.
    for length in (333, 335, 400, 500):
        t = TrackGeometry(venue_id=f"TEST_{length}", track_length_m=length)
        assert t.official_length_class_supported

    assert not TrackGeometry(venue_id="OTHER", track_length_m=250).official_length_class_supported

    rider = RiderPhysics(
        total_mass_kg=82.0,
        cda_m2=0.30,
        crr=0.003,
        drivetrain_efficiency=0.97,
    )
    no_draft = DraftingContext(aero_drag_multiplier=1.0, provenance_class="SELFTEST")
    draft_80 = DraftingContext(aero_drag_multiplier=0.8, provenance_class="SELFTEST")

    env_10 = Environment(air_density_kg_m3=1.20, relative_air_speed_mps=10.0)
    env_20 = Environment(air_density_kg_m3=1.20, relative_air_speed_mps=20.0)
    f10 = aerodynamic_drag_force_n(env_10, rider, no_draft)
    f20 = aerodynamic_drag_force_n(env_20, rider, no_draft)
    assert isclose(f20 / f10, 4.0, rel_tol=1e-12)

    f_draft = aerodynamic_drag_force_n(env_20, rider, draft_80)
    assert isclose(f_draft / f20, 0.8, rel_tol=1e-12)

    # Aerodynamic wheel power scales with v^3 when all else is fixed and rolling is removed.
    zero_rr = RiderPhysics(
        total_mass_kg=82.0,
        cda_m2=0.30,
        crr=0.0,
        drivetrain_efficiency=1.0,
    )
    p10 = power_breakdown(
        env_10,
        zero_rr,
        KinematicState(ground_speed_mps=10.0),
        no_draft,
    ).wheel_mechanical_power_w
    p20 = power_breakdown(
        env_20,
        zero_rr,
        KinematicState(ground_speed_mps=20.0),
        no_draft,
    ).wheel_mechanical_power_w
    assert isclose(p20 / p10, 8.0, rel_tol=1e-12)

    # Curve requirements rise with speed and fall with radius.
    c10 = centripetal_force_required_n(82.0, 10.0, 25.0)
    c15 = centripetal_force_required_n(82.0, 15.0, 25.0)
    assert c15 > c10
    assert ideal_bank_angle_deg(15.0, 25.0) > ideal_bank_angle_deg(10.0, 25.0)
    assert ideal_bank_angle_deg(15.0, 50.0) < ideal_bank_angle_deg(15.0, 25.0)

    # Positive acceleration raises required rider input power.
    steady = power_breakdown(
        env_20,
        rider,
        KinematicState(ground_speed_mps=20.0, acceleration_mps2=0.0),
        no_draft,
    )
    accel = power_breakdown(
        env_20,
        rider,
        KinematicState(ground_speed_mps=20.0, acceleration_mps2=0.5),
        no_draft,
    )
    assert accel.rider_input_power_w > steady.rider_input_power_w

    # Fail closed on physically invalid inputs.
    expect_raises(lambda: Environment(air_density_kg_m3=0.0, relative_air_speed_mps=10.0))
    expect_raises(lambda: RiderPhysics(82.0, 0.3, 0.003, 0.0))
    expect_raises(lambda: DraftingContext(0.0, "SELFTEST"))
    expect_raises(lambda: ideal_bank_angle_deg(10.0, 0.0))

    print("PASS_REALITY_PHYSICS_V0_MECHANICAL_INVARIANTS_ONLY")


if __name__ == "__main__":
    main()
