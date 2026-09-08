#!/usr/bin/env python3
"""Fair PRE-only comparison of named Keirin model ticket portfolios v2.

All models must describe the exact same Keirin car universe with complete
ordered-top3 support. The same frozen ticket-structure family is evaluated for
each model using ticket builder v3. No RESULT, PAYOUT, live ODDS, network
access, structure selection from outcomes, or automated betting is used.
"""

from __future__ import annotations

from math import isfinite
from typing import Mapping

import keirin_ticket_portfolio_builder_v3 as ticket


class ModelTicketComparisonError(ValueError):
    pass


def _model_name(value) -> str:
    if not isinstance(value, str):
        raise ModelTicketComparisonError("model_name_must_be_exact_string")
    if not value.strip():
        raise ModelTicketComparisonError("model_name_must_be_nonempty")
    if value != value.strip():
        raise ModelTicketComparisonError("model_name_must_not_have_edge_whitespace")
    return value


def _required_roi(value) -> float:
    try:
        x=float(value)
    except Exception as exc:
        raise ModelTicketComparisonError("required_roi_must_be_numeric") from exc
    if not isfinite(x) or x<0.0:
        raise ModelTicketComparisonError("required_roi_must_be_finite_nonnegative")
    return x


def compare_named_models(
    model_distributions: Mapping[str, Mapping[tuple, float]],
    required_roi: float = 0.10,
) -> dict:
    if not isinstance(model_distributions, Mapping) or not model_distributions:
        raise ModelTicketComparisonError("empty_model_distributions")

    roi=_required_roi(required_roi)
    normalized={}
    common_cars=None

    for raw_name, distribution in model_distributions.items():
        name=_model_name(raw_name)
        if name in normalized:
            raise ModelTicketComparisonError("duplicate_model_name")
        dist,cars=ticket.validate_top3_distribution(distribution)
        car_tuple=tuple(sorted(cars))
        if common_cars is None:
            common_cars=car_tuple
        elif car_tuple != common_cars:
            raise ModelTicketComparisonError("model_car_universe_mismatch")
        normalized[name]=dist

    models={}
    family_ids=None
    for name in sorted(normalized):
        structures=ticket.compare_default_structures(
            normalized[name],
            required_roi=roi,
        )
        ids={str(s["id"]) for s in structures}
        if family_ids is None:
            family_ids=ids
        elif ids != family_ids:
            raise ModelTicketComparisonError("ticket_structure_family_mismatch")
        models[name]={
            "structures":structures,
            "structures_by_id":{str(s["id"]):s for s in structures},
            "lowest_uniform_odds_structure":structures[0],
        }

    return {
        "record":"KEIRIN_MODEL_TICKET_COMPARISON_v2",
        "required_roi":roi,
        "car_universe":list(common_cars or ()),
        "ordered_top3_count_per_model":(
            len(common_cars)*(len(common_cars)-1)*(len(common_cars)-2)
            if common_cars else 0
        ),
        "ticket_structure_family":sorted(family_ids or ()),
        "models":models,
        "comparison_rule":(
            "Exact same car universe and complete ordered-top3 support; compare "
            "the same frozen ticket structures per model before outcomes."
        ),
        "minimum_odds_probability_basis":"EXACT_MODEL_PROBABILITY",
        "live_odds_used":False,
        "result_used":False,
        "payout_used":False,
        "human_comments_used":False,
        "network_access":False,
        "automated_bet_execution":False,
    }
