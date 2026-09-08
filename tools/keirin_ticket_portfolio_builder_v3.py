#!/usr/bin/env python3
"""Strict PRE-only Keirin ticket portfolio builder v3.

v3 keeps the v2 ticket-family semantics while tightening public economics
boundaries:
- Keirin car numbers must be exact integers 1..9 (bool is rejected).
- size/budget/unit parameters must be exact integers; no int() truncation.
- external structure metadata is cross-checked against the model distribution.
- minimum-odds economics are recomputed from exact model probabilities rather
  than the rounded display snapshot stored in a structure.
No RESULT, PAYOUT, live ODDS, network access, or automated execution is used.
"""

from __future__ import annotations

from math import isfinite
from typing import Mapping

import keirin_ticket_portfolio_builder_v2 as v2

TicketPortfolioError = v2.TicketPortfolioError
Top3Key = tuple[int, int, int]


def _exact_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TicketPortfolioError(f"{label}_must_be_exact_integer")
    return value


def _finite_nonnegative(value, label: str) -> float:
    try:
        x = float(value)
    except Exception as exc:
        raise TicketPortfolioError(f"{label}_must_be_numeric") from exc
    if not isfinite(x) or x < 0.0:
        raise TicketPortfolioError(f"{label}_must_be_finite_nonnegative")
    return x


def validate_top3_distribution(
    ordered_top3: Mapping[Top3Key, float],
    tolerance: float = 1e-9,
) -> tuple[dict[Top3Key, float], tuple[int, ...]]:
    dist, cars = v2.validate_top3_distribution(ordered_top3, tolerance=tolerance)
    checked_cars = []
    for car in cars:
        if isinstance(car, bool) or not isinstance(car, int):
            raise TicketPortfolioError("car_no_must_be_exact_integer")
        if not (1 <= car <= 9):
            raise TicketPortfolioError("car_no_outside_keirin_domain_1_to_9")
        checked_cars.append(car)
    return dist, tuple(checked_cars)


def market_probabilities(ordered_top3, market: str):
    validate_top3_distribution(ordered_top3)
    return v2.market_probabilities(ordered_top3, market)


def _validated_structure(
    ordered_top3,
    structure: Mapping[str, object],
):
    validate_top3_distribution(ordered_top3)
    if not isinstance(structure, Mapping):
        raise TicketPortfolioError("structure_must_be_mapping")
    try:
        market = str(structure["market"]).upper()
        raw_tickets = list(structure["tickets"])
        declared_count = structure["combination_count"]
        declared_hit = float(structure["model_hit_probability"])
    except Exception as exc:
        raise TicketPortfolioError("invalid_structure_metadata") from exc

    _exact_int(declared_count, "combination_count")
    tickets = [tuple(ticket) for ticket in raw_tickets]
    if not tickets:
        raise TicketPortfolioError("empty_structure")
    if declared_count != len(tickets):
        raise TicketPortfolioError("combination_count_metadata_mismatch")
    if len(set(tickets)) != len(tickets):
        raise TicketPortfolioError("duplicate_ticket_in_structure")

    probs = market_probabilities(ordered_top3, market)
    for ticket in tickets:
        if ticket not in probs:
            raise TicketPortfolioError(f"ticket_not_in_market_distribution:{ticket!r}")

    exact_hit = sum(float(probs[ticket]) for ticket in tickets)
    expected_snapshot = round(exact_hit, 12)
    if not isfinite(declared_hit) or abs(declared_hit - expected_snapshot) > 5e-13:
        raise TicketPortfolioError("model_hit_probability_metadata_mismatch")
    return market, tickets, probs, exact_hit


def exacta_single(ordered_top3):
    validate_top3_distribution(ordered_top3)
    out = v2.exacta_single(ordered_top3)
    _validated_structure(ordered_top3, out)
    return out


def quinella_single(ordered_top3):
    validate_top3_distribution(ordered_top3)
    out = v2.quinella_single(ordered_top3)
    _validated_structure(ordered_top3, out)
    return out


def trifecta_top_n(ordered_top3, n: int):
    validate_top3_distribution(ordered_top3)
    n = _exact_int(n, "n")
    out = v2.trifecta_top_n(ordered_top3, n)
    _validated_structure(ordered_top3, out)
    return out


def trifecta_box(ordered_top3, n: int):
    validate_top3_distribution(ordered_top3)
    n = _exact_int(n, "n")
    out = v2.trifecta_box(ordered_top3, n)
    _validated_structure(ordered_top3, out)
    return out


def trifecta_fixed_first_second_group_all(ordered_top3, second_group_size: int):
    validate_top3_distribution(ordered_top3)
    k = _exact_int(second_group_size, "second_group_size")
    out = v2.trifecta_fixed_first_second_group_all(ordered_top3, k)
    _validated_structure(ordered_top3, out)
    return out


def equal_stake_uniform_minimum_odds(
    ordered_top3,
    structure,
    required_roi: float = 0.10,
) -> float:
    """Exact economics from the source probability distribution.

    Unlike v1/v2's structure-only helper, this function does not trust the
    rounded model_hit_probability snapshot for threshold arithmetic.
    """
    _, tickets, _, exact_hit = _validated_structure(ordered_top3, structure)
    roi = _finite_nonnegative(required_roi, "required_roi")
    if exact_hit <= 0.0:
        raise TicketPortfolioError("selected_structure_has_zero_hit_probability")
    return len(tickets) * (1.0 + roi) / exact_hit


def allocate_fixed_race_budget(
    ordered_top3,
    structure,
    total_budget_yen: int,
    mode: str = "EQUAL",
    unit_yen: int = 100,
    required_roi: float = 0.10,
):
    _validated_structure(ordered_top3, structure)
    budget = _exact_int(total_budget_yen, "total_budget_yen")
    unit = _exact_int(unit_yen, "unit_yen")
    if budget <= 0 or unit <= 0 or budget % unit != 0:
        raise TicketPortfolioError("budget_must_be_positive_multiple_of_unit")
    roi = _finite_nonnegative(required_roi, "required_roi")
    return v2.allocate_fixed_race_budget(
        ordered_top3,
        structure,
        total_budget_yen=budget,
        mode=mode,
        unit_yen=unit,
        required_roi=roi,
    )


def compare_default_structures(ordered_top3, required_roi: float = 0.10):
    _, cars = validate_top3_distribution(ordered_top3)
    roi = _finite_nonnegative(required_roi, "required_roi")
    structures = [
        exacta_single(ordered_top3),
        quinella_single(ordered_top3),
        trifecta_top_n(ordered_top3, 3),
        trifecta_top_n(ordered_top3, 5),
        trifecta_box(ordered_top3, 3),
        trifecta_fixed_first_second_group_all(
            ordered_top3, min(3, len(cars) - 1)
        ),
    ]
    for structure in structures:
        structure["equal_stake_minimum_odds_for_required_roi"] = round(
            equal_stake_uniform_minimum_odds(
                ordered_top3, structure, required_roi=roi
            ),
            4,
        )
        structure["minimum_odds_probability_basis"] = "EXACT_MODEL_PROBABILITY"
    return sorted(
        structures,
        key=lambda s: (
            float(s["equal_stake_minimum_odds_for_required_roi"]),
            int(s["combination_count"]),
            str(s["id"]),
        ),
    )
