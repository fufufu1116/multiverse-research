#!/usr/bin/env python3
from itertools import permutations

import keirin_ticket_portfolio_builder_v1 as b


def uniform_four_car_distribution():
    return {
        triple: 1.0 / 24.0
        for triple in permutations((1, 2, 3, 4), 3)
    }


def selftest():
    dist = uniform_four_car_distribution()

    exacta = b.exacta_single(dist)
    quinella = b.quinella_single(dist)
    top3 = b.trifecta_top_n(dist, 3)
    box3 = b.trifecta_box(dist, 3)
    formation = b.trifecta_fixed_first_second_group_all(dist, 2)

    assert exacta["combination_count"] == 1
    assert abs(exacta["model_hit_probability"] - 1.0 / 12.0) < 1e-9
    assert quinella["combination_count"] == 1
    assert abs(quinella["model_hit_probability"] - 1.0 / 6.0) < 1e-9
    assert top3["combination_count"] == 3
    assert abs(top3["model_hit_probability"] - 3.0 / 24.0) < 1e-9
    assert box3["combination_count"] == 6
    assert abs(box3["model_hit_probability"] - 6.0 / 24.0) < 1e-9
    assert formation["combination_count"] == 4
    assert abs(formation["model_hit_probability"] - 4.0 / 24.0) < 1e-9

    # At +10% required ROI, these uniform examples have these conservative
    # equal-stake minimum odds thresholds.
    assert abs(b.equal_stake_uniform_minimum_odds(exacta, 0.10) - 13.2) < 1e-9
    assert abs(b.equal_stake_uniform_minimum_odds(quinella, 0.10) - 6.6) < 1e-9
    assert abs(b.equal_stake_uniform_minimum_odds(top3, 0.10) - 26.4) < 1e-9
    assert abs(b.equal_stake_uniform_minimum_odds(box3, 0.10) - 26.4) < 1e-9
    assert abs(b.equal_stake_uniform_minimum_odds(formation, 0.10) - 26.4) < 1e-9

    allocation = b.allocate_fixed_race_budget(
        dist,
        top3,
        total_budget_yen=900,
        mode="EQUAL",
        unit_yen=100,
        required_roi=0.10,
    )
    assert allocation["total_budget_yen"] == 900
    assert sum(allocation["stake_by_ticket_yen"].values()) == 900
    assert abs(allocation["conservative_uniform_minimum_odds"] - 26.4) < 1e-9

    ranked = b.compare_default_structures(dist, required_roi=0.10)
    assert ranked[0]["id"] == "QUINELLA_SINGLE"

    return {
        "status": "PASS",
        "markets": ["EXACTA", "QUINELLA", "TRIFECTA"],
        "structures_checked": 5,
        "fixed_race_budget_allocation_checked": True,
        "live_odds_used": False,
        "result_used": False,
        "payout_used": False,
        "automated_bet_execution": False,
    }


if __name__ == "__main__":
    print(selftest())
