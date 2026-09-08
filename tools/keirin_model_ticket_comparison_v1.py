#!/usr/bin/env python3
"""Bridge named Keirin top-3 model distributions into ticket comparison.

Input example:
{
  "C0": {(1,2,3): 0.1, ...},
  "C1": {...},
  "N1": {...},
}

No outcomes, payouts, live odds, scraping, or bet execution are used.
"""

from __future__ import annotations

from typing import Mapping

import keirin_ticket_portfolio_builder_v1 as ticket


def compare_named_models(
    model_distributions: Mapping[str, Mapping[tuple, float]],
    required_roi: float = 0.10,
) -> dict:
    if not model_distributions:
        raise ValueError("empty_model_distributions")

    models = {}
    for model_name in sorted(model_distributions):
        distribution = model_distributions[model_name]
        ticket.validate_top3_distribution(distribution)
        structures = ticket.compare_default_structures(
            distribution,
            required_roi=required_roi,
        )
        models[str(model_name)] = {
            "structures": structures,
            "lowest_uniform_odds_structure": structures[0],
        }

    return {
        "record": "KEIRIN_MODEL_TICKET_COMPARISON_v1",
        "required_roi": float(required_roi),
        "models": models,
        "comparison_rule": (
            "Compare the same predeclared ticket structures separately for each "
            "frozen model distribution. Do not select a structure using race results."
        ),
        "live_odds_used": False,
        "result_used": False,
        "payout_used": False,
        "automated_bet_execution": False,
    }
