from __future__ import annotations

"""Coefficient-injection adapter for C1/N1 PRE-only line architecture.

This module does not fit coefficients. It deterministically connects admitted
line relation features to the existing ordered-top3 probability generators.
Zero line coefficients must reduce exactly to the corresponding PL control.
"""

import math
from typing import Any, Mapping

from line_relation_features_v1 import (
    RunnerLineState,
    own_line_features,
    pair_line_features,
    rank3_context_features,
)
from top3_architecture_core_v1 import (
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)


class LineLogitAdapterError(ValueError):
    pass


def _numeric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        x = float(value)
        if math.isfinite(x):
            return x
    raise LineLogitAdapterError(f"nonnumeric_feature:{value!r}")


def linear_term(features: Mapping[str, Any], coefficients: Mapping[str, float]) -> float:
    total = 0.0
    for name, coef in coefficients.items():
        if name not in features:
            raise LineLogitAdapterError(f"missing_feature:{name}")
        c = float(coef)
        if not math.isfinite(c):
            raise LineLogitAdapterError(f"nonfinite_coefficient:{name}")
        total += c * _numeric(features[name])
    if not math.isfinite(total):
        raise LineLogitAdapterError("nonfinite_linear_term")
    return total


def c1_line_augmented_utilities(
    base_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    own_coefficients: Mapping[str, float],
) -> dict[int, float]:
    if set(base_utilities) != set(states):
        raise LineLogitAdapterError("base_utility_and_line_state_car_set_mismatch")
    out = {}
    for car, base in base_utilities.items():
        b = float(base)
        if not math.isfinite(b):
            raise LineLogitAdapterError(f"nonfinite_base_utility:{car}")
        out[car] = b + linear_term(
            own_line_features(states, car),
            own_coefficients,
        )
    return out


def n1_conditional_logits(
    c1_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    rank2_coefficients: Mapping[str, float],
    rank3_coefficients: Mapping[str, float],
) -> tuple[
    dict[int, float],
    dict[tuple[int, int], float],
    dict[tuple[int, int, int], float],
]:
    if set(c1_utilities) != set(states):
        raise LineLogitAdapterError("c1_utility_and_line_state_car_set_mismatch")
    cars = tuple(sorted(states))

    p1_logits = {car: float(c1_utilities[car]) for car in cars}
    p2_logits: dict[tuple[int, int], float] = {}
    p3_logits: dict[tuple[int, int, int], float] = {}

    for first in cars:
        for candidate in cars:
            if candidate == first:
                continue
            p2_logits[(first, candidate)] = (
                float(c1_utilities[candidate])
                + linear_term(
                    pair_line_features(states, candidate, first),
                    rank2_coefficients,
                )
            )

    for first in cars:
        for second in cars:
            if second == first:
                continue
            for candidate in cars:
                if candidate in (first, second):
                    continue
                p3_logits[(first, second, candidate)] = (
                    float(c1_utilities[candidate])
                    + linear_term(
                        rank3_context_features(
                            states,
                            candidate,
                            first,
                            second,
                        ),
                        rank3_coefficients,
                    )
                )

    return p1_logits, p2_logits, p3_logits


def build_c1_n1_distributions(
    base_utilities: Mapping[int, float],
    states: Mapping[int, RunnerLineState],
    own_coefficients: Mapping[str, float],
    rank2_coefficients: Mapping[str, float],
    rank3_coefficients: Mapping[str, float],
) -> dict[str, dict[tuple[int, int, int], float]]:
    c1_utilities = c1_line_augmented_utilities(
        base_utilities,
        states,
        own_coefficients,
    )
    c1 = pl_top3_from_runner_utilities(c1_utilities)
    p1, p2, p3 = n1_conditional_logits(
        c1_utilities,
        states,
        rank2_coefficients,
        rank3_coefficients,
    )
    n1 = conditional_top3_from_context_logits(p1, p2, p3)
    return {"C1": c1, "N1": n1}
