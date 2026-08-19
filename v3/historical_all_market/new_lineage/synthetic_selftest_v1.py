from __future__ import annotations

from itertools import permutations

from top3_architecture_core_v1 import (
    assert_unit_mass,
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)
from probability_object_contract_v1 import validate_ordered_top3_probability_object
from digital_twin_v1 import generate_race, pre_view, world_joint_distribution


def _records(obj):
    return [
        {"first": i, "second": j, "third": k, "p": p}
        for (i, j, k), p in obj.items()
    ]


def _assert_digital_twin_invariants() -> None:
    # Ordinary FI/FII-style generation must default to seven riders.
    race7 = generate_race(seed=20260820, race_index=0)
    if race7.event_format != "STANDARD_FI_FII_7" or len(race7.riders) != 7:
        raise AssertionError("digital_twin_default_format_failed")

    pre = pre_view(race7)
    if pre.get("event_format") != "STANDARD_FI_FII_7" or pre.get("field_size") != 7:
        raise AssertionError("digital_twin_pre_format_failed")

    # Hidden simulator truth must not leak into PRE rider records.
    for rider in pre["riders"]:
        if "latent_skill" in rider:
            raise AssertionError("digital_twin_latent_leak_failed")

    # Nine-rider worlds are explicit special-event fixtures, never silent defaults.
    race9 = generate_race(
        seed=20260820,
        race_index=1,
        event_format="SPECIAL_9",
    )
    if race9.event_format != "SPECIAL_9" or len(race9.riders) != 9:
        raise AssertionError("digital_twin_special9_failed")

    try:
        generate_race(
            seed=20260820,
            race_index=2,
            n_riders=9,
            event_format="STANDARD_FI_FII_7",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("digital_twin_format_fail_closed_failed")

    # Every currently implemented world must be a coherent ordered-top3 distribution.
    expected_support = len(list(permutations(range(1, 8), 3)))
    for world in ("W0", "W1", "W2", "W3", "W4"):
        joint = world_joint_distribution(race7, world)
        if len(joint) != expected_support:
            raise AssertionError(f"{world}_support_size_failed")
        if abs(sum(joint.values()) - 1.0) > 1e-10:
            raise AssertionError(f"{world}_mass_failed")
        if any(i == j or i == k or j == k for i, j, k in joint):
            raise AssertionError(f"{world}_duplicate_finisher_failed")
        if any(p < 0.0 for p in joint.values()):
            raise AssertionError(f"{world}_negative_probability_failed")


def run() -> None:
    cars = [1, 2, 3, 4, 5]

    # C0/C1 structural PL core smoke test.
    utilities = {car: -0.13 * car for car in cars}
    pl = pl_top3_from_runner_utilities(utilities)
    assert_unit_mass(pl)

    # N1 chain-rule core smoke test. Context terms are synthetic and carry no race meaning.
    p1_logits = dict(utilities)
    p2_logits = {
        (first, candidate): utilities[candidate] + 0.01 * (first - candidate)
        for first in cars
        for candidate in cars
        if candidate != first
    }
    p3_logits = {
        (first, second, candidate): utilities[candidate]
        + 0.01 * (first - candidate)
        - 0.005 * (second - candidate)
        for first in cars
        for second in cars
        for candidate in cars
        if second != first and candidate not in (first, second)
    }
    n1 = conditional_top3_from_context_logits(p1_logits, p2_logits, p3_logits)
    assert_unit_mass(n1)

    car_to_frame = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4}

    for name, obj in (("PL", pl), ("N1", n1)):
        errors = validate_ordered_top3_probability_object(
            active_car_nos=cars,
            records=_records(obj),
            car_to_frame=car_to_frame,
        )
        if errors:
            raise AssertionError(f"{name}_contract_failed: {errors}")

    expected_support = len(list(permutations(cars, 3)))
    if len(pl) != expected_support or len(n1) != expected_support:
        raise AssertionError("top3_support_size_failed")

    _assert_digital_twin_invariants()
    print("SYNTHETIC_SELFTEST_PASS")


if __name__ == "__main__":
    run()
