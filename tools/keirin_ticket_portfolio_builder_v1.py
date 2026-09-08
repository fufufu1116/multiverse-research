#!/usr/bin/env python3
"""PRE-only ticket portfolio builder for Keirin model output.

Consumes a frozen ordered top-3 probability distribution and constructs
candidate ticket structures without live odds, results, payouts, or network
access. It is a research/execution-planning component only; no bet execution.

Supported structures:
- exacta single
- quinella single
- trifecta top-N
- trifecta N-car box
- trifecta fixed first / K second candidates / all third

For multi-ticket structures, a conservative uniform minimum-odds threshold is
reported. If every funded ticket's current decimal odds is at least that
threshold, the model-implied expected ROI meets the requested margin under the
chosen fixed-race-budget allocation.
"""

from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Hashable, Mapping

Car = Hashable
Top3Key = tuple[Car, Car, Car]


class TicketPortfolioError(ValueError):
    pass


def validate_top3_distribution(
    ordered_top3: Mapping[Top3Key, float],
    tolerance: float = 1e-9,
) -> tuple[dict[Top3Key, float], tuple[Car, ...]]:
    if not ordered_top3:
        raise TicketPortfolioError("empty_top3_distribution")
    cleaned: dict[Top3Key, float] = {}
    cars: set[Car] = set()
    mass = 0.0
    for key, value in ordered_top3.items():
        if not isinstance(key, tuple) or len(key) != 3 or len(set(key)) != 3:
            raise TicketPortfolioError(f"invalid_top3_key:{key!r}")
        p = float(value)
        if not isfinite(p) or p < 0.0:
            raise TicketPortfolioError(f"invalid_probability:{key!r}")
        cleaned[key] = p
        cars.update(key)
        mass += p
    if abs(mass - 1.0) > tolerance:
        raise TicketPortfolioError(f"probability_mass_mismatch:{mass}")
    if len(cars) < 3:
        raise TicketPortfolioError("fewer_than_three_cars")
    return cleaned, tuple(sorted(cars, key=str))


def _rank(probs: Mapping[Hashable, float]):
    def stable_key(item):
        key, probability = item
        parts = key if isinstance(key, tuple) else (key,)
        return (-float(probability), tuple(str(x) for x in parts))
    return sorted(probs.items(), key=stable_key)


def market_probabilities(
    ordered_top3: Mapping[Top3Key, float],
    market: str,
) -> dict[tuple[Car, ...], float]:
    dist, _ = validate_top3_distribution(ordered_top3)
    market = str(market).upper()
    if market == "TRIFECTA":
        return dict(dist)

    out: defaultdict[tuple[Car, ...], float] = defaultdict(float)
    for (first, second, third), probability in dist.items():
        if market == "EXACTA":
            out[(first, second)] += probability
        elif market == "QUINELLA":
            pair = tuple(sorted((first, second), key=str))
            out[pair] += probability
        else:
            raise TicketPortfolioError(f"unsupported_market:{market}")
    return dict(out)


def _structure(
    structure_id: str,
    japanese: str,
    market: str,
    tickets: list[tuple[Car, ...]],
    probabilities: Mapping[tuple[Car, ...], float],
) -> dict:
    hit_probability = sum(float(probabilities[t]) for t in tickets)
    count = len(tickets)
    if count < 1:
        raise TicketPortfolioError("empty_structure")
    return {
        "id": structure_id,
        "japanese": japanese,
        "market": market,
        "tickets": [list(t) for t in tickets],
        "combination_count": count,
        "model_hit_probability": round(hit_probability, 12),
        "coverage_per_combination": round(hit_probability / count, 12),
        "live_odds_used": False,
    }


def exacta_single(ordered_top3: Mapping[Top3Key, float]) -> dict:
    probs = market_probabilities(ordered_top3, "EXACTA")
    ticket = _rank(probs)[0][0]
    return _structure("EXACTA_SINGLE", "2車単 単点", "EXACTA", [ticket], probs)


def quinella_single(ordered_top3: Mapping[Top3Key, float]) -> dict:
    probs = market_probabilities(ordered_top3, "QUINELLA")
    ticket = _rank(probs)[0][0]
    return _structure("QUINELLA_SINGLE", "2車複 単点", "QUINELLA", [ticket], probs)


def trifecta_top_n(
    ordered_top3: Mapping[Top3Key, float],
    n: int,
) -> dict:
    probs = market_probabilities(ordered_top3, "TRIFECTA")
    n = int(n)
    if n < 1:
        raise TicketPortfolioError("n_must_be_positive")
    tickets = [key for key, _ in _rank(probs)[:n]]
    return _structure(
        f"TRIFECTA_TOP_{n}",
        f"3連単 上位{n}点",
        "TRIFECTA",
        tickets,
        probs,
    )


def trifecta_box(
    ordered_top3: Mapping[Top3Key, float],
    n: int,
) -> dict:
    dist, cars = validate_top3_distribution(ordered_top3)
    n = int(n)
    if n < 3 or n > len(cars):
        raise TicketPortfolioError("invalid_box_size")

    podium: defaultdict[Car, float] = defaultdict(float)
    for triple, probability in dist.items():
        for car in triple:
            podium[car] += probability

    selected = [car for car, _ in _rank(dict(podium))[:n]]
    selected_set = set(selected)
    tickets = sorted(
        [triple for triple in dist if set(triple).issubset(selected_set)],
        key=lambda triple: tuple(str(x) for x in triple),
    )
    out = _structure(
        f"TRIFECTA_BOX_{n}",
        f"3連単 {n}車BOX",
        "TRIFECTA",
        tickets,
        dist,
    )
    out["selected_cars"] = selected
    return out


def trifecta_fixed_first_second_group_all(
    ordered_top3: Mapping[Top3Key, float],
    second_group_size: int,
) -> dict:
    dist, cars = validate_top3_distribution(ordered_top3)
    k = int(second_group_size)
    if k < 1 or k > len(cars) - 1:
        raise TicketPortfolioError("invalid_second_group_size")

    first_prob: defaultdict[Car, float] = defaultdict(float)
    first_second_prob: defaultdict[tuple[Car, Car], float] = defaultdict(float)
    for (first, second, third), probability in dist.items():
        first_prob[first] += probability
        first_second_prob[(first, second)] += probability

    fixed_first = _rank(dict(first_prob))[0][0]
    second_probs = {
        car: first_second_prob[(fixed_first, car)]
        for car in cars
        if car != fixed_first
    }
    second_group = [car for car, _ in _rank(second_probs)[:k]]
    tickets = sorted(
        [
            (fixed_first, second, third)
            for second in second_group
            for third in cars
            if third not in (fixed_first, second)
        ],
        key=lambda triple: tuple(str(x) for x in triple),
    )
    out = _structure(
        "TRIFECTA_FIXED_FIRST_SECOND_GROUP_ALL",
        "3連単 1着固定・2着複数・3着全",
        "TRIFECTA",
        tickets,
        dist,
    )
    out["fixed_first"] = fixed_first
    out["second_group"] = second_group
    return out


def equal_stake_uniform_minimum_odds(
    structure: Mapping[str, object],
    required_roi: float = 0.10,
) -> float:
    count = int(structure["combination_count"])
    hit_probability = float(structure["model_hit_probability"])
    required_roi = float(required_roi)
    if count < 1 or hit_probability <= 0.0:
        raise TicketPortfolioError("empty_or_zero_probability_structure")
    if required_roi < 0.0:
        raise TicketPortfolioError("required_roi_must_be_nonnegative")
    return count * (1.0 + required_roi) / hit_probability


def allocate_fixed_race_budget(
    ordered_top3: Mapping[Top3Key, float],
    structure: Mapping[str, object],
    total_budget_yen: int,
    mode: str = "EQUAL",
    unit_yen: int = 100,
    required_roi: float = 0.10,
) -> dict:
    budget = int(total_budget_yen)
    unit = int(unit_yen)
    if budget <= 0 or unit <= 0 or budget % unit != 0:
        raise TicketPortfolioError("budget_must_be_positive_multiple_of_unit")

    market = str(structure["market"])
    probs = market_probabilities(ordered_top3, market)
    tickets = [tuple(ticket) for ticket in structure["tickets"]]
    total_units = budget // unit
    if total_units < len(tickets):
        raise TicketPortfolioError("budget_too_small_to_fund_every_ticket")

    mode = str(mode).upper()
    if mode == "EQUAL":
        weights = {ticket: 1.0 for ticket in tickets}
    elif mode == "MODEL_PROPORTIONAL":
        weights = {ticket: float(probs[ticket]) for ticket in tickets}
    else:
        raise TicketPortfolioError(f"unsupported_allocation_mode:{mode}")

    weight_sum = sum(weights.values())
    if weight_sum <= 0.0:
        raise TicketPortfolioError("zero_allocation_weight_sum")

    raw_units = {
        ticket: total_units * weights[ticket] / weight_sum
        for ticket in tickets
    }
    allocated_units = {
        ticket: max(1, int(raw_units[ticket]))
        for ticket in tickets
    }

    used = sum(allocated_units.values())
    while used > total_units:
        candidates = [ticket for ticket in tickets if allocated_units[ticket] > 1]
        if not candidates:
            raise TicketPortfolioError("cannot_resolve_minimum_unit_allocation")
        ticket = max(
            candidates,
            key=lambda t: (
                allocated_units[t] - raw_units[t],
                allocated_units[t],
                tuple(str(x) for x in t),
            ),
        )
        allocated_units[ticket] -= 1
        used -= 1

    while used < total_units:
        ticket = max(
            tickets,
            key=lambda t: (
                raw_units[t] - allocated_units[t],
                weights[t],
                tuple(str(x) for x in t),
            ),
        )
        allocated_units[ticket] += 1
        used += 1

    stakes = {
        ticket: allocated_units[ticket] * unit
        for ticket in tickets
    }
    probability_weighted_stake = sum(
        float(probs[ticket]) * stakes[ticket]
        for ticket in tickets
    )
    if probability_weighted_stake <= 0.0:
        raise TicketPortfolioError("zero_probability_weighted_stake")

    required_roi = float(required_roi)
    if required_roi < 0.0:
        raise TicketPortfolioError("required_roi_must_be_nonnegative")
    uniform_threshold = (
        budget * (1.0 + required_roi) / probability_weighted_stake
    )

    return {
        "mode": mode,
        "total_budget_yen": budget,
        "unit_yen": unit,
        "stake_by_ticket_yen": {
            "-".join(str(x) for x in ticket): stake
            for ticket, stake in stakes.items()
        },
        "required_roi": required_roi,
        "conservative_uniform_minimum_odds": round(uniform_threshold, 4),
        "owner_instruction": (
            f"全購入点の現在オッズが {uniform_threshold:.1f}倍以上なら"
            "指定ROI条件を満たす購入候補。下回る点がある場合は個別再計算。"
        ),
        "live_odds_used": False,
        "automated_bet_execution": False,
    }


def compare_default_structures(
    ordered_top3: Mapping[Top3Key, float],
    required_roi: float = 0.10,
) -> list[dict]:
    _, cars = validate_top3_distribution(ordered_top3)
    structures = [
        exacta_single(ordered_top3),
        quinella_single(ordered_top3),
        trifecta_top_n(ordered_top3, min(3, len(ordered_top3))),
        trifecta_top_n(ordered_top3, min(5, len(ordered_top3))),
        trifecta_box(ordered_top3, 3),
        trifecta_fixed_first_second_group_all(
            ordered_top3,
            min(3, len(cars) - 1),
        ),
    ]
    for structure in structures:
        structure["equal_stake_minimum_odds_for_required_roi"] = round(
            equal_stake_uniform_minimum_odds(structure, required_roi),
            4,
        )
    return sorted(
        structures,
        key=lambda s: (
            float(s["equal_stake_minimum_odds_for_required_roi"]),
            int(s["combination_count"]),
            str(s["id"]),
        ),
    )
