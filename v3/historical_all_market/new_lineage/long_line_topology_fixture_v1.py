from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Sequence, Tuple

from digital_twin_v1 import Race


LineShape = Tuple[int, ...]


def _validate_line_shape(field_size: int, line_shape: Sequence[int]) -> LineShape:
    if not line_shape:
        raise ValueError("line_shape must contain at least one line")
    if any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in line_shape):
        raise ValueError("line_shape sizes must be positive integers")
    shape = tuple(line_shape)
    if sum(shape) != field_size:
        raise ValueError("line_shape must sum exactly to field size")
    return shape


def _resolve_car_order(race: Race, car_order: Iterable[int] | None) -> Tuple[int, ...]:
    active = tuple(sorted(r.car_no for r in race.riders))
    if car_order is None:
        return active

    order = tuple(car_order)
    if len(order) != len(active):
        raise ValueError("car_order length must equal field size")
    if len(set(order)) != len(order):
        raise ValueError("car_order must not contain duplicates")
    if set(order) != set(active):
        raise ValueError("car_order must contain exactly the active car numbers")
    return order


def apply_line_shape_fixture(
    race: Race,
    line_shape: Sequence[int],
    car_order: Iterable[int] | None = None,
) -> Race:
    """Return a synthetic engineering fixture with an explicit line topology.

    This adapter changes only line membership/position/size. It does not change
    latent ability, observed PRE descriptors, bank/wind context, event format,
    model coefficients, or real-world frequency assumptions.

    A supplied line shape is support/test input only. It is not a statement that
    the shape is common, advantageous, or even empirically observed at a stated
    frequency in real keirin.
    """
    shape = _validate_line_shape(len(race.riders), line_shape)
    order = _resolve_car_order(race, car_order)

    membership: dict[int, tuple[int, int, int]] = {}
    cursor = 0
    for line_id, size in enumerate(shape, start=1):
        members = order[cursor:cursor + size]
        for pos, car_no in enumerate(members):
            membership[car_no] = (line_id, pos, size)
        cursor += size

    if set(membership) != set(order):
        raise AssertionError("internal line membership coverage failure")

    riders = tuple(
        replace(
            rider,
            line_id=membership[rider.car_no][0],
            line_position=membership[rider.car_no][1],
            line_size=membership[rider.car_no][2],
        )
        for rider in race.riders
    )
    return replace(race, riders=riders)


def assert_line_topology_invariants(race: Race, expected_shape: Sequence[int] | None = None) -> None:
    groups: dict[int, list[object]] = {}
    for rider in race.riders:
        groups.setdefault(rider.line_id, []).append(rider)

    ordered_sizes = []
    seen_cars: set[int] = set()
    for line_id in sorted(groups):
        members = groups[line_id]
        size = len(members)
        ordered_sizes.append(size)

        positions = sorted(r.line_position for r in members)
        if positions != list(range(size)):
            raise AssertionError(f"line {line_id} positions are not contiguous 0..size-1")
        if any(r.line_size != size for r in members):
            raise AssertionError(f"line {line_id} has inconsistent line_size values")
        if any((r.line_size == 1) != (size == 1) for r in members):
            raise AssertionError(f"line {line_id} singleton semantics mismatch")

        for rider in members:
            if rider.car_no in seen_cars:
                raise AssertionError("car appears in more than one line")
            seen_cars.add(rider.car_no)

    active_cars = {r.car_no for r in race.riders}
    if seen_cars != active_cars:
        raise AssertionError("not every active car belongs to exactly one line")

    if expected_shape is not None:
        shape = _validate_line_shape(len(race.riders), expected_shape)
        if tuple(ordered_sizes) != shape:
            raise AssertionError(f"topology shape mismatch: {tuple(ordered_sizes)} != {shape}")
