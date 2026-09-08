#!/usr/bin/env python3
from itertools import permutations

import keirin_model_ticket_comparison_v2 as c


def uniform(cars=(1,2,3,4,5,6,7)):
    triples=list(permutations(cars,3))
    return {triple:1.0/len(triples) for triple in triples}


def skewed(cars=(1,2,3,4,5,6,7)):
    triples=list(permutations(cars,3))
    weights={}
    for triple in triples:
        score=1.0
        if triple[0]==1:
            score*=4.0
        if triple[1]==2:
            score*=2.0
        if triple[2]==3:
            score*=1.5
        weights[triple]=score
    total=sum(weights.values())
    return {triple:weight/total for triple,weight in weights.items()}


def must_fail(fn, contains=None):
    try:
        fn()
    except (c.ModelTicketComparisonError, ValueError, TypeError, KeyError) as exc:
        if contains is not None:
            assert contains in str(exc), (contains,str(exc))
        return
    raise AssertionError("expected fail-closed error")


def main():
    out=c.compare_named_models(
        {"C0":uniform(),"C1":skewed(),"N1":uniform()},
        required_roi=0.10,
    )
    assert set(out["models"])=={"C0","C1","N1"}
    assert out["car_universe"]==[1,2,3,4,5,6,7]
    assert out["ordered_top3_count_per_model"]==210
    assert out["minimum_odds_probability_basis"]=="EXACT_MODEL_PROBABILITY"
    assert out["live_odds_used"] is False
    assert out["result_used"] is False
    assert out["payout_used"] is False
    assert out["network_access"] is False
    assert out["automated_bet_execution"] is False

    families=[
        set(model["structures_by_id"])
        for model in out["models"].values()
    ]
    assert families[0]==families[1]==families[2]
    assert families[0]==set(out["ticket_structure_family"])

    # Different model probabilities are allowed, different race universes are not.
    must_fail(
        lambda:c.compare_named_models(
            {"C0":uniform((1,2,3,4,5,6,7)),
             "C1":uniform((1,2,3,4,5,6,8))}
        ),
        "model_car_universe_mismatch",
    )

    # Every model must carry complete ordered-top3 support.
    must_fail(
        lambda:c.compare_named_models(
            {"C0":uniform(),"C1":{(1,2,3):1.0}}
        ),
        "incomplete_ordered_top3_support",
    )

    # Names are exact strings so numeric/string collisions cannot be hidden.
    must_fail(
        lambda:c.compare_named_models({1:uniform()}),
        "model_name_must_be_exact_string",
    )
    must_fail(
        lambda:c.compare_named_models({" ":uniform()}),
        "model_name_must_be_nonempty",
    )
    must_fail(
        lambda:c.compare_named_models({" C0":uniform()}),
        "model_name_must_not_have_edge_whitespace",
    )

    must_fail(
        lambda:c.compare_named_models({"C0":uniform()},required_roi=float("nan")),
        "required_roi_must_be_finite_nonnegative",
    )
    must_fail(
        lambda:c.compare_named_models({}),
        "empty_model_distributions",
    )

    print("PASS 12/12")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
