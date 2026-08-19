from __future__ import annotations

from itertools import combinations
import math
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

Top3Key = Tuple[int, int, int]
PairKey = Tuple[int, int]
TripleKey = Tuple[int, int, int]


def derive_market_probabilities(
    ordered_top3: Mapping[Top3Key, float],
) -> Dict[str, Dict[tuple, float]]:
    """Derive coherent car-based elementary-ticket event probabilities.

    The ordered top-3 distribution is the sole sporting probability source of truth.
    Wide is an overlapping-event vector, so its total event-probability mass is 3, not 1.
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


def derive_frame_probabilities(
    two_shatan: Mapping[PairKey, float],
    car_to_frame: Mapping[int, int],
) -> Dict[str, Dict[PairKey, float]]:
    """Aggregate ordered car top-2 probabilities into sold frame markets.

    Same-frame outcomes are retained naturally when two riders share a frame; this covers
    official same-frame ('zoro-me') frame outcomes without hard-coding a particular field-size
    mapping. The actual car->frame mapping must come from the race card / sold-market metadata.
    """

    two_wakutan: Dict[PairKey, float] = {}
    two_wakuhuku: Dict[PairKey, float] = {}

    for (first_car, second_car), probability in two_shatan.items():
        if first_car not in car_to_frame or second_car not in car_to_frame:
            raise KeyError("missing_car_to_frame_mapping")

        first_frame = int(car_to_frame[first_car])
        second_frame = int(car_to_frame[second_car])

        ordered_frame_pair = (first_frame, second_frame)
        two_wakutan[ordered_frame_pair] = (
            two_wakutan.get(ordered_frame_pair, 0.0) + probability
        )

        unordered_frame_pair = tuple(sorted((first_frame, second_frame)))
        two_wakuhuku[unordered_frame_pair] = (
            two_wakuhuku.get(unordered_frame_pair, 0.0) + probability
        )

    return {
        "2wakutan": two_wakutan,
        "2wakuhuku": two_wakuhuku,
    }


def validate_ordered_top3_probability_object(
    active_car_nos: Sequence[int],
    records: Iterable[Mapping[str, float]],
    tolerance: float = 1e-10,
    car_to_frame: Optional[Mapping[int, int]] = None,
) -> List[str]:
    """Return contract violations for an ordered top-3 probability object.

    If `car_to_frame` is supplied, frame-market aggregation is also validated. Absence of
    a frame mapping is not an error because frame markets are not sold in every race.
    """

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

    # 2shatan(i,j) = sum_k P(i,j,k).
    for (first, second), p_2shatan in markets["2shatan"].items():
        source_sum = sum(
            p
            for (i, j, _k), p in ordered_top3.items()
            if i == first and j == second
        )
        if abs(source_sum - p_2shatan) > tolerance:
            errors.append(f"2shatan_marginal_identity_failed:{first}-{second}")

    # 2shahuku(i,j) = 2shatan(i,j) + 2shatan(j,i).
    for (a, b), p_2shahuku in markets["2shahuku"].items():
        expected = markets["2shatan"].get((a, b), 0.0) + markets["2shatan"].get((b, a), 0.0)
        if abs(expected - p_2shahuku) > tolerance:
            errors.append(f"2shahuku_marginal_identity_failed:{a}-{b}")

    if car_to_frame is not None:
        if set(car_to_frame.keys()) != car_set:
            errors.append("car_to_frame_support_mismatch")
        else:
            try:
                frame_markets = derive_frame_probabilities(
                    markets["2shatan"], car_to_frame=car_to_frame
                )
                for market in ("2wakutan", "2wakuhuku"):
                    observed_mass = sum(frame_markets[market].values())
                    if abs(observed_mass - 1.0) > tolerance:
                        errors.append(f"{market}_mass_mismatch:{observed_mass}!=1.0")
            except Exception as exc:
                errors.append(f"frame_aggregation_failed:{type(exc).__name__}")

    return errors


def fail_closed_probability_object(
    active_car_nos: Sequence[int],
    records: Iterable[Mapping[str, float]],
    tolerance: float = 1e-10,
    car_to_frame: Optional[Mapping[int, int]] = None,
) -> None:
    errors = validate_ordered_top3_probability_object(
        active_car_nos=active_car_nos,
        records=records,
        tolerance=tolerance,
        car_to_frame=car_to_frame,
    )
    if errors:
        raise ValueError("PROBABILITY_OBJECT_FAIL_CLOSED: " + " | ".join(errors))
