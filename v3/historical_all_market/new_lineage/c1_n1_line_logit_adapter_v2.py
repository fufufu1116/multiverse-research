from __future__ import annotations

"""Hardened C1/N1 PRE-only line-logit adapter.

v2 preserves the v1 mathematics while validating state-map integrity on every
public probability path and provides a raw-PRE-row entry point that must pass
the line_relation_features_v2 post-decision-field firewall.
"""

import math
from typing import Any, Iterable, Mapping

from line_relation_features_v2 import (
    LineRelationError,
    RunnerLineState,
    validate_line_states,
)
import c1_n1_line_logit_adapter_v1 as v1
from top3_architecture_core_v1 import (
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)


class LineLogitAdapterV2Error(ValueError):
    pass


def _validated_states(
    states: Mapping[int, RunnerLineState],
) -> dict[int, RunnerLineState]:
    if not isinstance(states, Mapping):
        raise LineLogitAdapterV2Error("states_must_be_mapping")
    try:
        rows = [
            {
                "car_no": state.car_no,
                "line_group_id": state.line_group_id,
                "line_position": state.line_position,
                "line_size": state.line_size,
                "is_singleton": state.is_singleton,
            }
            for state in states.values()
        ]
    except Exception as exc:
        raise LineLogitAdapterV2Error("invalid_state_object") from exc

    try:
        checked = validate_line_states(rows)
    except LineRelationError as exc:
        raise LineLogitAdapterV2Error(f"invalid_line_state_topology:{exc}") from exc

    if set(checked) != set(states):
        raise LineLogitAdapterV2Error("state_mapping_key_car_no_mismatch")
    for key, state in states.items():
        if int(key) != int(state.car_no):
            raise LineLogitAdapterV2Error("state_mapping_key_car_no_mismatch")
    return checked


def _finite_utilities(values: Mapping[int, float], label: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for car, value in values.items():
        x = float(value)
        if not math.isfinite(x):
            raise LineLogitAdapterV2Error(f"nonfinite_{label}:{car}")
        out[int(car)] = x
    return out


def c1_line_augmented_utilities(
    base_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    own_coefficients: Mapping[str, float],
) -> dict[int, float]:
    checked = _validated_states(states)
    base = _finite_utilities(base_utilities, "base_utility")
    if set(base) != set(checked):
        raise LineLogitAdapterV2Error("base_utility_and_line_state_car_set_mismatch")
    try:
        return v1.c1_line_augmented_utilities(base, checked, own_coefficients)
    except (ValueError, TypeError) as exc:
        raise LineLogitAdapterV2Error(str(exc)) from exc


def n1_conditional_logits(
    c1_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    rank2_coefficients: Mapping[str, float],
    rank3_coefficients: Mapping[str, float],
):
    checked = _validated_states(states)
    c1 = _finite_utilities(c1_utilities, "c1_utility")
    if set(c1) != set(checked):
        raise LineLogitAdapterV2Error("c1_utility_and_line_state_car_set_mismatch")
    try:
        return v1.n1_conditional_logits(
            c1, checked, rank2_coefficients, rank3_coefficients
        )
    except (ValueError, TypeError) as exc:
        raise LineLogitAdapterV2Error(str(exc)) from exc


def _assert_distribution_integrity(
    name: str,
    dist: Mapping[tuple[int, int, int], float],
    cars: set[int],
) -> None:
    n = len(cars)
    expected = n * (n - 1) * (n - 2)
    if len(dist) != expected:
        raise LineLogitAdapterV2Error(
            f"{name}_ordered_top3_count_mismatch:{len(dist)}:{expected}"
        )
    mass = 0.0
    for key, probability in dist.items():
        if len(key) != 3 or len(set(key)) != 3:
            raise LineLogitAdapterV2Error(f"{name}_duplicate_car_in_top3:{key}")
        if not set(key) <= cars:
            raise LineLogitAdapterV2Error(f"{name}_unknown_car_in_top3:{key}")
        p = float(probability)
        if not math.isfinite(p) or p < 0.0 or p > 1.0:
            raise LineLogitAdapterV2Error(f"{name}_invalid_probability:{key}:{p}")
        mass += p
    if abs(mass - 1.0) > 1e-10:
        raise LineLogitAdapterV2Error(f"{name}_probability_mass_mismatch:{mass}")


def build_c1_n1_distributions(
    base_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    own_coefficients: Mapping[str, float],
    rank2_coefficients: Mapping[str, float],
    rank3_coefficients: Mapping[str, float],
) -> dict[str, dict[tuple[int, int, int], float]]:
    checked = _validated_states(states)
    c1_utilities = c1_line_augmented_utilities(
        base_utilities, checked, own_coefficients
    )
    c1 = pl_top3_from_runner_utilities(c1_utilities)
    p1, p2, p3 = n1_conditional_logits(
        c1_utilities, checked, rank2_coefficients, rank3_coefficients
    )
    n1 = conditional_top3_from_context_logits(p1, p2, p3)
    cars = set(checked)
    _assert_distribution_integrity("C1", c1, cars)
    _assert_distribution_integrity("N1", n1, cars)
    return {"C1": c1, "N1": n1}


def build_c1_n1_distributions_from_pre_rows(
    base_utilities: Mapping[int, float],
    line_rows: Iterable[Mapping[str, Any]],
    own_coefficients: Mapping[str, float],
    rank2_coefficients: Mapping[str, float],
    rank3_coefficients: Mapping[str, float],
) -> dict[str, dict[tuple[int, int, int], float]]:
    """Preferred v2 entry point: raw line rows must pass the PRE-only firewall."""
    states = validate_line_states(line_rows)
    return build_c1_n1_distributions(
        base_utilities,
        states,
        own_coefficients,
        rank2_coefficients,
        rank3_coefficients,
    )
