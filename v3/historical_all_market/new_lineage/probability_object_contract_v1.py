from __future__ import annotations

from itertools import combinations
import math
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

Top3Key = Tuple[int, int, int]
PairKey = Tuple[int, int]
TripleKey = Tuple[int, int, int]


def derive_market_probabilities(
    ordered_top3: Mapping[Top3Key, float],
) -> Dict[str, Dict[tuple, float]]:
    """Derive coherent elementary-ticket event probabilities from one top-3 joint source.

    The ordered top-3 distribution is the source of truth. Wide is an overlapping-event
    vector, so its total event-probability mass is 3, not 1.
    """

    three_rentan: Dict[Top3Key, float] = dict(ordered_top3)
    three_renhuku: Dict[TripleKey, float] = {}
    two_shatan: Dict[PairKey, float] = {}
    two_shahuku: Dict[PairKey, float] = {}
    wide: Dict[PairKey, float] = {}

    for (first, second, third), probability in ordered_top3.items():
        triple = tuple(sorted((first, second, third)))
        three_renhuku[triple] = three_renhuku.get(triple, 0.0) + probability

        ordered_pair = (first, second)
        two_shatan[ordered_pair] = two_shatan.get(ordered_pair, 0.0) + probability

        unordered_pair = tuple(sorted((first, second)))
        two_shahuku[unordered_pair] = two_shahuku.get(unordered_pair, 0.0) + probability

        for a, b in combinations((first, second, third), 2):
            pair = tuple(sorted((a, b)))
            wide[pair] = wide.get(pair, 0.0) + probability

    return {
        "3rentan": three_rentan,
        "3renhuku": three_renhuku,
        "2shatan": two_shatan,
        "2shahuku": two_shahuku,
        "wide": wide,
    }


def validate_ordered_top3_probability_object(
    active_car_nos: Sequence[int],
    records: Iterable[Mapping[str, float]],
    tolerance: float = 1e-10,
) -> List[str]:
    """Return contract violations for an ordered top-3 probability object."""

    errors: List[str] = []
    cars = list(active_car_nos)
    car_set = set(cars)

    if len(cars) < 3:
        return ["fewer_than_three_active_cars"]
    if len(cars) != len(car_set):
        return ["duplicate_active_car_no"]

    ordered_top3: Dict[Top3Key, float] = {}
    for record in records:
        try:
            key = (
                int(record["first"]),
                int(record["second"]),
                int(record["third"]),
            )
            probability = float(record["p"])
        except Exception as exc:
            errors.append(f"malformed_record:{type(exc).__name__}")
            continue

        if key in ordered_top3:
            errors.append(f"duplicate_top3_key:{key}")
        if len(set(key)) != 3:
            errors.append(f"repeated_car_within_top3:{key}")
        if not set(key).issubset(car_set):
            errors.append(f"unknown_car_in_top3:{key}")
        if not math.isfinite(probability) or probability < 0.0:
            errors.append(f"invalid_probability:{key}")

        ordered_top3[key] = probability

    expected_support_size = len(cars) * (len(cars) - 1) * (len(cars) - 2)
    if len(ordered_top3) != expected_support_size:
        errors.append(
            f"ordered_top3_support_size_mismatch:{len(ordered_top3)}!={expected_support_size}"
        )

    total_mass = sum(ordered_top3.values())
    if abs(total_mass - 1.0) > tolerance:
        errors.append(f"ordered_top3_mass_mismatch:{total_mass}")

    if errors:
        return errors

    markets = derive_market_probabilities(ordered_top3)
    expected_masses = {
        "3rentan": 1.0,
        "3renhuku": 1.0,
        "2shatan": 1.0,
        "2shahuku": 1.0,
        "wide": 3.0,
    }

    for market, target_mass in expected_masses.items():
        observed_mass = sum(markets[market].values())
        if abs(observed_mass - target_mass) > tolerance:
            errors.append(f"{market}_mass_mismatch:{observed_mass}!={target_mass}")

    # Marginal identity: for any ordered pair i->j, 2shatan(i,j) equals
    # the sum over all possible third-place cars in the source object.
    for (first, second), p_2shatan in markets["2shatan"].items():
        source_sum = sum(
            p
            for (i, j, _k), p in ordered_top3.items()
            if i == first and j == second
        )
        if abs(source_sum - p_2shatan) > tolerance:
            errors.append(f"2shatan_marginal_identity_failed:{first}-{second}")

    # Marginal identity: 2shahuku(i,j) = 2shatan(i,j) + 2shatan(j,i).
    for (a, b), p_2shahuku in markets["2shahuku"].items():
        expected = markets["2shatan"].get((a, b), 0.0) + markets["2shatan"].get((b, a), 0.0)
        if abs(expected - p_2shahuku) > tolerance:
            errors.append(f"2shahuku_marginal_identity_failed:{a}-{b}")

    return errors


def fail_closed_probability_object(
    active_car_nos: Sequence[int],
    records: Iterable[Mapping[str, float]],
    tolerance: float = 1e-10,
) -> None:
    errors = validate_ordered_top3_probability_object(
        active_car_nos=active_car_nos,
        records=records,
        tolerance=tolerance,
    )
    if errors:
        raise ValueError("PROBABILITY_OBJECT_FAIL_CLOSED: " + " | ".join(errors))
