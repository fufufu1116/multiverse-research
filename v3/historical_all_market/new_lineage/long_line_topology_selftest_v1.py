from __future__ import annotations

from itertools import permutations

from digital_twin_v1 import generate_race, pre_view, world_joint_distribution
from long_line_topology_fixture_v1 import apply_line_shape_fixture, assert_line_topology_invariants


SEVEN_RIDER_FIXTURES = (
    (4, 3),
    (4, 2, 1),
    (4, 1, 1, 1),
)

NINE_RIDER_FIXTURES = (
    (4, 3, 2),
    (5, 4),
    (4, 2, 1, 1, 1),
)


def _assert_pre_line_fields(race, shape) -> None:
    pre = pre_view(race)
    riders = pre["riders"]
    by_line = {}
    for rider in riders:
        by_line.setdefault(rider["line_group_id"], []).append(rider)

    actual_shape = []
    for line_id in sorted(by_line):
        members = by_line[line_id]
        size = len(members)
        actual_shape.append(size)
        positions = sorted(r["line_position"] for r in members)
        if positions != list(range(size)):
            raise AssertionError("PRE line positions are not contiguous")
        if any(r["line_size"] != size for r in members):
            raise AssertionError("PRE line_size mismatch")
        if any(r["is_singleton"] != (size == 1) for r in members):
            raise AssertionError("PRE singleton mismatch")

    if tuple(actual_shape) != tuple(shape):
        raise AssertionError(f"PRE shape mismatch: {tuple(actual_shape)} != {tuple(shape)}")


def _assert_world_mechanical_compatibility(race) -> None:
    cars = [r.car_no for r in race.riders]
    expected_support = len(list(permutations(cars, 3)))
    for world in ("W0", "W1", "W2", "W3", "W4"):
        joint = world_joint_distribution(race, world)
        if len(joint) != expected_support:
            raise AssertionError(f"{world} support size mismatch")
        if abs(sum(joint.values()) - 1.0) > 1e-10:
            raise AssertionError(f"{world} probability mass mismatch")
        if any(p < 0.0 for p in joint.values()):
            raise AssertionError(f"{world} negative probability")
        if any(i == j or i == k or j == k for i, j, k in joint):
            raise AssertionError(f"{world} duplicate finisher")


def _assert_invalid_requests_fail_closed(base7) -> None:
    invalid_shapes = (
        (),
        (4, 2),
        (4, 4),
        (0, 7),
        (-1, 8),
        (3, 2, 1, 0, 1),
        (3.0, 4),
        (True, 6),
    )
    for shape in invalid_shapes:
        try:
            apply_line_shape_fixture(base7, shape)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid shape did not fail closed: {shape}")

    bad_orders = (
        (1, 2, 3, 4, 5, 6),
        (1, 2, 3, 4, 5, 6, 6),
        (1, 2, 3, 4, 5, 6, 8),
    )
    for order in bad_orders:
        try:
            apply_line_shape_fixture(base7, (4, 3), car_order=order)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid car_order did not fail closed: {order}")


def run() -> None:
    base7 = generate_race(seed=20260820, race_index=700, event_format="STANDARD_FI_FII_7")
    base9 = generate_race(seed=20260820, race_index=900, event_format="SPECIAL_9")

    # Default generator path remains unchanged: it still uses its prereg-existing
    # max-3 motifs unless the explicit topology fixture adapter is invoked.
    if max(r.line_size for r in base7.riders) > 3:
        raise AssertionError("default 7-rider generator unexpectedly changed")
    if max(r.line_size for r in base9.riders) > 3:
        raise AssertionError("default 9-rider generator unexpectedly changed")

    for shape in SEVEN_RIDER_FIXTURES:
        fixture = apply_line_shape_fixture(base7, shape)
        assert_line_topology_invariants(fixture, shape)
        _assert_pre_line_fields(fixture, shape)
        if max(r.line_position for r in fixture.riders) < 3:
            raise AssertionError(f"fixture does not exercise position 3+: {shape}")
        _assert_world_mechanical_compatibility(fixture)

    for shape in NINE_RIDER_FIXTURES:
        fixture = apply_line_shape_fixture(base9, shape)
        assert_line_topology_invariants(fixture, shape)
        _assert_pre_line_fields(fixture, shape)
        if max(r.line_position for r in fixture.riders) < 3:
            raise AssertionError(f"fixture does not exercise position 3+: {shape}")
        if shape == (5, 4) and max(r.line_position for r in fixture.riders) != 4:
            raise AssertionError("5-rider fixture does not exercise position 4")
        _assert_world_mechanical_compatibility(fixture)

    # Deterministic explicit car ordering must be honored exactly.
    ordered = apply_line_shape_fixture(base7, (4, 3), car_order=(7, 6, 5, 4, 3, 2, 1))
    line1 = sorted(
        (r for r in ordered.riders if r.line_id == 1),
        key=lambda r: r.line_position,
    )
    if tuple(r.car_no for r in line1) != (7, 6, 5, 4):
        raise AssertionError("explicit car_order was not preserved")

    _assert_invalid_requests_fail_closed(base7)

    print("LONG_LINE_TOPOLOGY_SELFTEST_PASS")


if __name__ == "__main__":
    run()
