#!/usr/bin/env python3
from copy import deepcopy
from itertools import permutations

import keirin_ticket_portfolio_builder_v2 as b


def uniform(cars=(1,2,3,4)):
    triples=list(permutations(cars,3))
    return {triple:1.0/len(triples) for triple in triples}


def must_fail(fn, contains=None):
    try:
        fn()
    except (b.TicketPortfolioError, ValueError, KeyError) as exc:
        if contains is not None:
            assert contains in str(exc), (contains,str(exc))
        return
    raise AssertionError("expected fail-closed error")


def main():
    dist=uniform()

    exacta=b.exacta_single(dist)
    quinella=b.quinella_single(dist)
    top3=b.trifecta_top_n(dist,3)
    box3=b.trifecta_box(dist,3)
    formation=b.trifecta_fixed_first_second_group_all(dist,2)

    assert exacta["combination_count"]==1
    assert quinella["combination_count"]==1
    assert top3["combination_count"]==3
    assert box3["combination_count"]==6
    assert formation["combination_count"]==4
    assert abs(exacta["model_hit_probability"]-1.0/12.0)<1e-9
    assert abs(quinella["model_hit_probability"]-1.0/6.0)<1e-9
    assert abs(top3["model_hit_probability"]-3.0/24.0)<1e-9
    assert abs(box3["model_hit_probability"]-6.0/24.0)<1e-9
    assert abs(formation["model_hit_probability"]-4.0/24.0)<1e-9

    equal=b.allocate_fixed_race_budget(
        dist,top3,total_budget_yen=900,mode="EQUAL",unit_yen=100,required_roi=0.10
    )
    prop=b.allocate_fixed_race_budget(
        dist,top3,total_budget_yen=1000,mode="MODEL_PROPORTIONAL",unit_yen=100,required_roi=0.10
    )
    assert sum(equal["stake_by_ticket_yen"].values())==900
    assert sum(prop["stake_by_ticket_yen"].values())==1000
    assert equal["automated_bet_execution"] is False

    # Complete ordered-top3 support is mandatory even when sparse mass sums to one.
    sparse={(1,2,3):1.0}
    must_fail(lambda:b.validate_top3_distribution(sparse),"incomplete_ordered_top3_support")

    # Top-N must not silently shrink.
    must_fail(lambda:b.trifecta_top_n(dist,25),"n_exceeds_available_combinations")

    # Duplicate externally supplied tickets must not corrupt allocation.
    dup=deepcopy(top3)
    dup["tickets"]=[dup["tickets"][0],dup["tickets"][0],dup["tickets"][1]]
    dup["combination_count"]=3
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,dup,900),
        "duplicate_ticket_in_structure",
    )

    # Declared combination count must match the actual unique ticket list.
    mismatch=deepcopy(top3)
    mismatch["combination_count"]=4
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,mismatch,900),
        "combination_count_metadata_mismatch",
    )
    must_fail(
        lambda:b.equal_stake_uniform_minimum_odds(mismatch,0.10),
        "combination_count_metadata_mismatch",
    )

    # Market/ticket mismatch must fail cleanly.
    wrong_market=deepcopy(top3)
    wrong_market["market"]="EXACTA"
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,wrong_market,900),
        "ticket_not_in_market_distribution",
    )

    # Non-finite ROI requests are invalid.
    must_fail(
        lambda:b.equal_stake_uniform_minimum_odds(top3,float("nan")),
        "required_roi_must_be_finite_nonnegative",
    )
    must_fail(
        lambda:b.allocate_fixed_race_budget(dist,top3,900,required_roi=float("inf")),
        "required_roi_must_be_finite_nonnegative",
    )

    ranked=b.compare_default_structures(dist,required_roi=0.10)
    assert ranked[0]["id"]=="QUINELLA_SINGLE"

    print("PASS 11/11")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
