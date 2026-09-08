#!/usr/bin/env python3
from copy import deepcopy
from itertools import permutations
import math

import keirin_ticket_portfolio_builder_v3 as b


def uniform(cars=(1,2,3,4,5,6,7)):
    triples=list(permutations(cars,3))
    return {triple:1.0/len(triples) for triple in triples}


def must_fail(fn, contains=None):
    try:
        fn()
    except (b.TicketPortfolioError, ValueError, TypeError, KeyError) as exc:
        if contains is not None:
            assert contains in str(exc), (contains,str(exc))
        return
    raise AssertionError("expected fail-closed error")


def main():
    dist=uniform()
    normalized,cars=b.validate_top3_distribution(dist)
    assert len(cars)==7
    assert len(normalized)==7*6*5==210
    assert abs(sum(normalized.values())-1.0)<1e-12

    box3=b.trifecta_box(dist,3)
    box4=b.trifecta_box(dist,4)
    box5=b.trifecta_box(dist,5)
    formation=b.trifecta_fixed_first_second_group_all(dist,3)
    top5=b.trifecta_top_n(dist,5)

    assert box3["combination_count"]==6
    assert box4["combination_count"]==24
    assert box5["combination_count"]==60
    assert formation["combination_count"]==15
    assert top5["combination_count"]==5

    # Exact probability basis, not rounded display snapshot.
    exact_threshold=b.equal_stake_uniform_minimum_odds(dist,top5,0.10)
    assert abs(exact_threshold-231.0)<1e-10
    ranked=b.compare_default_structures(dist,0.10)
    assert all(
        s["minimum_odds_probability_basis"]=="EXACT_MODEL_PROBABILITY"
        for s in ranked
    )

    equal=b.allocate_fixed_race_budget(
        dist,top5,total_budget_yen=1000,mode="EQUAL",unit_yen=100,required_roi=0.10
    )
    prop=b.allocate_fixed_race_budget(
        dist,top5,total_budget_yen=1000,mode="MODEL_PROPORTIONAL",unit_yen=100,required_roi=0.10
    )
    assert sum(equal["stake_by_ticket_yen"].values())==1000
    assert sum(prop["stake_by_ticket_yen"].values())==1000
    assert equal["automated_bet_execution"] is False

    # Sparse mass=1 is still invalid.
    must_fail(
        lambda:b.validate_top3_distribution({(1,2,3):1.0}),
        "incomplete_ordered_top3_support",
    )

    # Keirin car domain and exact integer types.
    must_fail(
        lambda:b.validate_top3_distribution(uniform((1,2,3,10))),
        "car_no_outside_keirin_domain_1_to_9",
    )
    must_fail(
        lambda:b.validate_top3_distribution(uniform((True,2,3,4))),
        "car_no_must_be_exact_integer",
    )
    must_fail(lambda:b.trifecta_top_n(dist,3.0),"n_must_be_exact_integer")
    must_fail(lambda:b.trifecta_box(dist,True),"n_must_be_exact_integer")

    # No silent int() truncation/coercion in money inputs.
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,top5,900.9),
        "total_budget_yen_must_be_exact_integer",
    )
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,top5,True),
        "total_budget_yen_must_be_exact_integer",
    )
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,top5,1000,unit_yen=100.5),
        "unit_yen_must_be_exact_integer",
    )

    # Forged/stale structure economics metadata cannot pass.
    forged=deepcopy(top5)
    forged["model_hit_probability"]=0.9
    must_fail(
        lambda:b.equal_stake_uniform_minimum_odds(dist,forged,0.10),
        "model_hit_probability_metadata_mismatch",
    )
    duplicate=deepcopy(top5)
    duplicate["tickets"][1]=duplicate["tickets"][0]
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,duplicate,1000),
        "duplicate_ticket_in_structure",
    )
    wrong_count=deepcopy(top5)
    wrong_count["combination_count"]=4
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,wrong_count,1000),
        "combination_count_metadata_mismatch",
    )

    must_fail(
        lambda:b.equal_stake_uniform_minimum_odds(dist,top5,float("nan")),
        "required_roi_must_be_finite_nonnegative",
    )
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,top5,1000,required_roi=float("inf")),
        "required_roi_must_be_finite_nonnegative",
    )

    print("PASS 20/20")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
