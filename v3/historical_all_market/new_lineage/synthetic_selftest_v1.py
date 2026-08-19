from __future__ import annotations

from itertools import permutations

from top3_architecture_core_v1 import (
    assert_unit_mass,
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)
from probability_object_contract_v1 import validate_ordered_top3_probability_object


def _records(obj):
    return [
        {"first": i, "second": j, "third": k, "p": p}
        for (i, j, k), p in obj.items()
    ]


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

    print("SYNTHETIC_SELFTEST_PASS")


if __name__ == "__main__":
    run()
