from __future__ import annotations

import math
from typing import Dict, Hashable, Mapping, Tuple

Car = Hashable
Top3Key = Tuple[Car, Car, Car]


def _softmax(logits: Mapping[Car, float]) -> Dict[Car, float]:
    if not logits:
        raise ValueError("empty_logits")
    values = [float(v) for v in logits.values()]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite_logit")
    max_logit = max(values)
    exps = {k: math.exp(float(v) - max_logit) for k, v in logits.items()}
    denom = sum(exps.values())
    if not math.isfinite(denom) or denom <= 0.0:
        raise ValueError("invalid_softmax_denominator")
    return {k: v / denom for k, v in exps.items()}


def pl_top3_from_runner_utilities(
    runner_utilities: Mapping[Car, float],
) -> Dict[Top3Key, float]:
    """Exact ordered top-3 distribution under a Plackett-Luce generator.

    C0 and C1 deliberately share this generator. The scientific difference is upstream:
    - C0 uses the frozen/current runner utility/probability basis.
    - C1 may use admitted line/race-structure PRE in the runner utility.

    Keeping the downstream generator identical is essential for the feature-vs-architecture
    ablation. Do not add line-conditioned rank interactions inside this function.
    """

    cars = list(runner_utilities.keys())
    if len(cars) < 3:
        raise ValueError("fewer_than_three_runners")
    if len(cars) != len(set(cars)):
        raise ValueError("duplicate_runner_key")

    p_first = _softmax(runner_utilities)
    ordered_top3: Dict[Top3Key, float] = {}

    for first in cars:
        second_logits = {
            car: runner_utilities[car]
            for car in cars
            if car != first
        }
        p_second = _softmax(second_logits)

        for second in second_logits:
            third_logits = {
                car: runner_utilities[car]
                for car in cars
                if car not in (first, second)
            }
            p_third = _softmax(third_logits)

            for third in third_logits:
                ordered_top3[(first, second, third)] = (
                    p_first[first] * p_second[second] * p_third[third]
                )

    return ordered_top3


def conditional_top3_from_context_logits(
    p1_logits: Mapping[Car, float],
    p2_logits: Mapping[Tuple[Car, Car], float],
    p3_logits: Mapping[Tuple[Car, Car, Car], float],
) -> Dict[Top3Key, float]:
    """Exact N1 ordered top-3 distribution.

    Implements the low-freedom chain-rule object:

        P(i,j,k|X) = P1(i|X) * P2(j|i,X) * P3(k|i,j,X)

    This function is deliberately agnostic about how the logits are trained. The future
    training layer may use only preregistered/admitted PRE features. No RESULT/PAYOUT or
    post-decision feature belongs in this interface.
    """

    cars = list(p1_logits.keys())
    if len(cars) < 3:
        raise ValueError("fewer_than_three_runners")
    if len(cars) != len(set(cars)):
        raise ValueError("duplicate_runner_key")

    p_first = _softmax(p1_logits)
    ordered_top3: Dict[Top3Key, float] = {}

    for first in cars:
        second_context = {}
        for candidate in cars:
            if candidate == first:
                continue
            key = (first, candidate)
            if key not in p2_logits:
                raise KeyError(f"missing_p2_logit:{key}")
            second_context[candidate] = p2_logits[key]
        p_second = _softmax(second_context)

        for second in second_context:
            third_context = {}
            for candidate in cars:
                if candidate in (first, second):
                    continue
                key = (first, second, candidate)
                if key not in p3_logits:
                    raise KeyError(f"missing_p3_logit:{key}")
                third_context[candidate] = p3_logits[key]
            p_third = _softmax(third_context)

            for third in third_context:
                ordered_top3[(first, second, third)] = (
                    p_first[first] * p_second[second] * p_third[third]
                )

    return ordered_top3


def probability_mass(ordered_top3: Mapping[Top3Key, float]) -> float:
    return float(sum(float(p) for p in ordered_top3.values()))


def assert_unit_mass(
    ordered_top3: Mapping[Top3Key, float],
    tolerance: float = 1e-10,
) -> None:
    mass = probability_mass(ordered_top3)
    if abs(mass - 1.0) > tolerance:
        raise ValueError(f"top3_probability_mass_mismatch:{mass}")
