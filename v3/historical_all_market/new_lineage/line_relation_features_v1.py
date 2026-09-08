from __future__ import annotations

"""Deterministic PRE-only line relation feature encoder for C1/N1 research.

This module converts already-admitted line topology fields into low-freedom
runner/pair/triple relations. It contains no fitted coefficients, RESULT,
PAYOUT, ODDS, market values, network access, or post-race reconstruction.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class LineRelationError(ValueError):
    pass


@dataclass(frozen=True)
class RunnerLineState:
    car_no: int
    line_group_id: str
    line_position: int
    line_size: int
    is_singleton: bool


def _as_state(row: Mapping[str, Any]) -> RunnerLineState:
    try:
        car_no = int(row["car_no"])
        group = str(row["line_group_id"]).strip()
        position = int(row["line_position"])
        size = int(row["line_size"])
        singleton = row["is_singleton"]
    except Exception as exc:
        raise LineRelationError("missing_or_invalid_line_fields") from exc

    if car_no < 1:
        raise LineRelationError("car_no_must_be_positive")
    if not group:
        raise LineRelationError("line_group_id_must_be_nonempty")
    if position < 0:
        raise LineRelationError("line_position_must_be_nonnegative")
    if size < 1:
        raise LineRelationError("line_size_must_be_positive")
    if not isinstance(singleton, bool):
        raise LineRelationError("is_singleton_must_be_boolean")
    if singleton != (size == 1):
        raise LineRelationError("singleton_semantics_mismatch")
    return RunnerLineState(car_no, group, position, size, singleton)


def validate_line_states(rows: Iterable[Mapping[str, Any]]) -> dict[int, RunnerLineState]:
    states = [_as_state(r) for r in rows]
    if len(states) < 3:
        raise LineRelationError("fewer_than_three_active_runners")
    if len({s.car_no for s in states}) != len(states):
        raise LineRelationError("duplicate_car_no")

    by_group: dict[str, list[RunnerLineState]] = {}
    for state in states:
        by_group.setdefault(state.line_group_id, []).append(state)

    for group, members in by_group.items():
        size = len(members)
        declared_sizes = {m.line_size for m in members}
        if declared_sizes != {size}:
            raise LineRelationError(f"line_size_group_mismatch:{group}")
        positions = sorted(m.line_position for m in members)
        if positions != list(range(size)):
            raise LineRelationError(f"line_positions_not_contiguous:{group}")
        if size == 1 and members[0].line_position != 0:
            raise LineRelationError(f"singleton_position_must_be_zero:{group}")

    return {s.car_no: s for s in states}


def own_line_features(
    states: Mapping[int, RunnerLineState],
    car_no: int,
) -> dict[str, int | bool]:
    if car_no not in states:
        raise LineRelationError(f"unknown_car:{car_no}")
    s = states[car_no]
    return {
        "line_position_index": s.line_position,
        "line_size": s.line_size,
        "is_singleton": s.is_singleton,
        "is_line_head": s.line_position == 0 and not s.is_singleton,
        "is_bante": s.line_position == 1,
        "is_third": s.line_position == 2,
        "is_rear_position_3plus": s.line_position >= 3,
        "num_lines": len({x.line_group_id for x in states.values()}),
    }


def pair_line_features(
    states: Mapping[int, RunnerLineState],
    candidate_car: int,
    context_car: int,
) -> dict[str, int | bool]:
    if candidate_car == context_car:
        raise LineRelationError("candidate_and_context_must_differ")
    if candidate_car not in states or context_car not in states:
        raise LineRelationError("unknown_pair_car")

    c = states[candidate_car]
    x = states[context_car]
    same = c.line_group_id == x.line_group_id

    # Cross-line position delta is deliberately neutralized rather than treating
    # arbitrary line-group presentation order as a numerical relationship.
    delta = c.line_position - x.line_position if same else 0

    return {
        "same_line": same,
        "within_line_position_relation_known": same,
        "position_delta_candidate_minus_context": delta,
        "candidate_directly_ahead_of_context": same and c.line_position + 1 == x.line_position,
        "candidate_directly_behind_context": same and c.line_position == x.line_position + 1,
        "candidate_is_line_head_of_context": same and c.line_position == 0 and x.line_position > 0,
        "context_is_line_head_of_candidate": same and x.line_position == 0 and c.line_position > 0,
        "candidate_is_singleton": c.is_singleton,
        "context_is_singleton": x.is_singleton,
        "candidate_line_size": c.line_size,
        "context_line_size": x.line_size,
    }


def rank3_context_features(
    states: Mapping[int, RunnerLineState],
    candidate_car: int,
    first_car: int,
    second_car: int,
) -> dict[str, int | bool]:
    if len({candidate_car, first_car, second_car}) != 3:
        raise LineRelationError("rank3_cars_must_be_distinct")

    c_first = pair_line_features(states, candidate_car, first_car)
    c_second = pair_line_features(states, candidate_car, second_car)
    first_second = pair_line_features(states, first_car, second_car)

    out: dict[str, int | bool] = {
        "first_second_same_line": bool(first_second["same_line"]),
    }
    for prefix, features in (("to_first", c_first), ("to_second", c_second)):
        for key, value in features.items():
            out[f"{prefix}_{key}"] = value
    return out


def encode_race_line_relations(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    states = validate_line_states(rows)
    cars = tuple(sorted(states))
    own = {car: own_line_features(states, car) for car in cars}
    pairs = {
        (candidate, context): pair_line_features(states, candidate, context)
        for candidate in cars
        for context in cars
        if candidate != context
    }
    return {
        "cars": cars,
        "own": own,
        "pairs": pairs,
        "result_fields_included": False,
        "payout_fields_included": False,
        "odds_fields_included": False,
        "post_race_reconstruction_used": False,
    }
