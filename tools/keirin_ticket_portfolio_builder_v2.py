#!/usr/bin/env python3
"""Hardened PRE-only ticket structure builder v2.

This version keeps v1 structure semantics but rejects incomplete ordered-top3
distributions, impossible top-N requests, duplicate structure tickets, and
structure metadata mismatches before fixed-budget allocation.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import permutations
from math import isfinite
from typing import Hashable, Mapping

import keirin_ticket_portfolio_builder_v1 as v1

Car = Hashable
Top3Key = tuple[Car, Car, Car]
TicketPortfolioError = v1.TicketPortfolioError


def validate_top3_distribution(
    ordered_top3: Mapping[Top3Key, float],
    tolerance: float = 1e-9,
) -> tuple[dict[Top3Key, float], tuple[Car, ...]]:
    dist, cars = v1.validate_top3_distribution(ordered_top3, tolerance=tolerance)
    expected = set(permutations(cars, 3))
    actual = set(dist)
    if actual != expected:
        missing = len(expected - actual)
        extra = len(actual - expected)
        raise TicketPortfolioError(
            f"incomplete_ordered_top3_support:missing={missing}:extra={extra}"
        )
    if len(dist) != len(cars) * (len(cars)-1) * (len(cars)-2):
        raise TicketPortfolioError("ordered_top3_count_mismatch")
    for key, probability in dist.items():
        p = float(probability)
        if not isfinite(p) or p < 0.0 or p > 1.0:
            raise TicketPortfolioError(f"invalid_probability:{key!r}")
    return dist, cars


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


def _rank(probs):
    def stable_key(item):
        key, probability = item
        parts = key if isinstance(key, tuple) else (key,)
        return (-float(probability), tuple(str(x) for x in parts))
    return sorted(probs.items(), key=stable_key)


def _structure(
    structure_id: str,
    japanese: str,
    market: str,
    tickets: list[tuple[Car, ...]],
    probabilities: Mapping[tuple[Car, ...], float],
) -> dict:
    if not tickets:
        raise TicketPortfolioError("empty_structure")
    if len(set(tickets)) != len(tickets):
        raise TicketPortfolioError("duplicate_ticket_in_structure")
    unknown = [ticket for ticket in tickets if ticket not in probabilities]
    if unknown:
        raise TicketPortfolioError(f"ticket_not_in_market_distribution:{unknown[0]!r}")
    hit_probability = sum(float(probabilities[t]) for t in tickets)
    return {
        "id": structure_id,
        "japanese": japanese,
        "market": market,
        "tickets": [list(t) for t in tickets],
        "combination_count": len(tickets),
        "model_hit_probability": round(hit_probability, 12),
        "coverage_per_combination": round(hit_probability / len(tickets), 12),
        "live_odds_used": False,
    }


def exacta_single(ordered_top3):
    probs = market_probabilities(ordered_top3, "EXACTA")
    ticket = _rank(probs)[0][0]
    return _structure("EXACTA_SINGLE","2車単 単点","EXACTA",[ticket],probs)


def quinella_single(ordered_top3):
    probs = market_probabilities(ordered_top3, "QUINELLA")
    ticket = _rank(probs)[0][0]
    return _structure("QUINELLA_SINGLE","2車複 単点","QUINELLA",[ticket],probs)


def trifecta_top_n(ordered_top3, n: int):
    probs = market_probabilities(ordered_top3, "TRIFECTA")
    n = int(n)
    if n < 1:
        raise TicketPortfolioError("n_must_be_positive")
    if n > len(probs):
        raise TicketPortfolioError("n_exceeds_available_combinations")
    tickets = [key for key, _ in _rank(probs)[:n]]
    return _structure(f"TRIFECTA_TOP_{n}",f"3連単 上位{n}点","TRIFECTA",tickets,probs)


def trifecta_box(ordered_top3, n: int):
    dist, cars = validate_top3_distribution(ordered_top3)
    n = int(n)
    if n < 3 or n > len(cars):
        raise TicketPortfolioError("invalid_box_size")
    podium: defaultdict[Car,float] = defaultdict(float)
    for triple, probability in dist.items():
        for car in triple:
            podium[car] += probability
    selected = [car for car, _ in _rank(dict(podium))[:n]]
    selected_set = set(selected)
    tickets = sorted(
        [triple for triple in dist if set(triple).issubset(selected_set)],
        key=lambda triple: tuple(str(x) for x in triple),
    )
    out = _structure(f"TRIFECTA_BOX_{n}",f"3連単 {n}車BOX","TRIFECTA",tickets,dist)
    out["selected_cars"] = selected
    expected_count = n * (n-1) * (n-2)
    if out["combination_count"] != expected_count:
        raise TicketPortfolioError("box_combination_count_mismatch")
    return out


def trifecta_fixed_first_second_group_all(ordered_top3, second_group_size: int):
    dist, cars = validate_top3_distribution(ordered_top3)
    k = int(second_group_size)
    if k < 1 or k > len(cars)-1:
        raise TicketPortfolioError("invalid_second_group_size")
    first_prob: defaultdict[Car,float] = defaultdict(float)
    first_second_prob: defaultdict[tuple[Car,Car],float] = defaultdict(float)
    for (first,second,third), probability in dist.items():
        first_prob[first] += probability
        first_second_prob[(first,second)] += probability
    fixed_first = _rank(dict(first_prob))[0][0]
    second_probs = {
        car:first_second_prob[(fixed_first,car)]
        for car in cars if car != fixed_first
    }
    second_group = [car for car,_ in _rank(second_probs)[:k]]
    tickets = sorted(
        [
            (fixed_first,second,third)
            for second in second_group
            for third in cars
            if third not in (fixed_first,second)
        ],
        key=lambda triple: tuple(str(x) for x in triple),
    )
    out = _structure(
        "TRIFECTA_FIXED_FIRST_SECOND_GROUP_ALL",
        "3連単 1着固定・2着複数・3着全",
        "TRIFECTA",tickets,dist,
    )
    out["fixed_first"] = fixed_first
    out["second_group"] = second_group
    expected_count = k * (len(cars)-2)
    if out["combination_count"] != expected_count:
        raise TicketPortfolioError("formation_combination_count_mismatch")
    return out


def _validated_external_structure(
    ordered_top3,
    structure: Mapping[str,object],
) -> tuple[str, list[tuple[Car,...]], dict[tuple[Car,...],float]]:
    validate_top3_distribution(ordered_top3)
    if not isinstance(structure, Mapping):
        raise TicketPortfolioError("structure_must_be_mapping")
    try:
        market = str(structure["market"]).upper()
        raw_tickets = list(structure["tickets"])
        declared_count = int(structure["combination_count"])
    except Exception as exc:
        raise TicketPortfolioError("invalid_structure_metadata") from exc
    tickets = [tuple(ticket) for ticket in raw_tickets]
    if not tickets:
        raise TicketPortfolioError("empty_structure")
    if len(set(tickets)) != len(tickets):
        raise TicketPortfolioError("duplicate_ticket_in_structure")
    if declared_count != len(tickets):
        raise TicketPortfolioError("combination_count_metadata_mismatch")
    probs = market_probabilities(ordered_top3, market)
    for ticket in tickets:
        if ticket not in probs:
            raise TicketPortfolioError(f"ticket_not_in_market_distribution:{ticket!r}")
    return market, tickets, probs


def equal_stake_uniform_minimum_odds(structure, required_roi: float=0.10) -> float:
    try:
        count=int(structure["combination_count"])
        tickets=list(structure["tickets"])
        hit_probability=float(structure["model_hit_probability"])
    except Exception as exc:
        raise TicketPortfolioError("invalid_structure_metadata") from exc
    if count != len(tickets) or count < 1:
        raise TicketPortfolioError("combination_count_metadata_mismatch")
    normalized=[tuple(t) for t in tickets]
    if len(set(normalized)) != len(normalized):
        raise TicketPortfolioError("duplicate_ticket_in_structure")
    roi=float(required_roi)
    if not isfinite(roi) or roi < 0.0:
        raise TicketPortfolioError("required_roi_must_be_finite_nonnegative")
    if not isfinite(hit_probability) or hit_probability <= 0.0 or hit_probability > 1.0:
        raise TicketPortfolioError("invalid_structure_hit_probability")
    return count * (1.0 + roi) / hit_probability


def allocate_fixed_race_budget(
    ordered_top3,
    structure,
    total_budget_yen: int,
    mode: str="EQUAL",
    unit_yen: int=100,
    required_roi: float=0.10,
):
    market,tickets,probs = _validated_external_structure(ordered_top3,structure)
    budget=int(total_budget_yen); unit=int(unit_yen)
    if budget <= 0 or unit <= 0 or budget % unit != 0:
        raise TicketPortfolioError("budget_must_be_positive_multiple_of_unit")
    total_units=budget//unit
    if total_units < len(tickets):
        raise TicketPortfolioError("budget_too_small_to_fund_every_ticket")
    mode=str(mode).upper()
    if mode=="EQUAL":
        weights={ticket:1.0 for ticket in tickets}
    elif mode=="MODEL_PROPORTIONAL":
        weights={ticket:float(probs[ticket]) for ticket in tickets}
    else:
        raise TicketPortfolioError(f"unsupported_allocation_mode:{mode}")
    weight_sum=sum(weights.values())
    if not isfinite(weight_sum) or weight_sum <= 0.0:
        raise TicketPortfolioError("zero_or_nonfinite_allocation_weight_sum")
    raw={ticket:total_units*weights[ticket]/weight_sum for ticket in tickets}
    allocated={ticket:max(1,int(raw[ticket])) for ticket in tickets}
    used=sum(allocated.values())
    while used>total_units:
        candidates=[t for t in tickets if allocated[t]>1]
        if not candidates:
            raise TicketPortfolioError("cannot_resolve_minimum_unit_allocation")
        t=max(candidates,key=lambda x:(allocated[x]-raw[x],allocated[x],tuple(str(v) for v in x)))
        allocated[t]-=1; used-=1
    while used<total_units:
        t=max(tickets,key=lambda x:(raw[x]-allocated[x],weights[x],tuple(str(v) for v in x)))
        allocated[t]+=1; used+=1
    stakes={t:allocated[t]*unit for t in tickets}
    probability_weighted_stake=sum(float(probs[t])*stakes[t] for t in tickets)
    if not isfinite(probability_weighted_stake) or probability_weighted_stake<=0.0:
        raise TicketPortfolioError("zero_or_nonfinite_probability_weighted_stake")
    roi=float(required_roi)
    if not isfinite(roi) or roi<0.0:
        raise TicketPortfolioError("required_roi_must_be_finite_nonnegative")
    threshold=budget*(1.0+roi)/probability_weighted_stake
    return {
        "mode":mode,
        "market":market,
        "total_budget_yen":budget,
        "unit_yen":unit,
        "stake_by_ticket_yen":{"-".join(str(x) for x in t):stakes[t] for t in tickets},
        "required_roi":roi,
        "conservative_uniform_minimum_odds":round(threshold,4),
        "live_odds_used":False,
        "automated_bet_execution":False,
    }


def compare_default_structures(ordered_top3, required_roi: float=0.10):
    _,cars=validate_top3_distribution(ordered_top3)
    structures=[
        exacta_single(ordered_top3),
        quinella_single(ordered_top3),
        trifecta_top_n(ordered_top3,min(3,len(ordered_top3))),
        trifecta_top_n(ordered_top3,min(5,len(ordered_top3))),
        trifecta_box(ordered_top3,3),
        trifecta_fixed_first_second_group_all(ordered_top3,min(3,len(cars)-1)),
    ]
    for structure in structures:
        structure["equal_stake_minimum_odds_for_required_roi"]=round(
            equal_stake_uniform_minimum_odds(structure,required_roi),4
        )
    return sorted(
        structures,
        key=lambda s:(
            float(s["equal_stake_minimum_odds_for_required_roi"]),
            int(s["combination_count"]),str(s["id"])
        ),
    )
