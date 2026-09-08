#!/usr/bin/env python3
from itertools import permutations

import keirin_model_ticket_comparison_v1 as c


def uniform(cars):
    triples = list(permutations(cars, 3))
    return {triple: 1.0 / len(triples) for triple in triples}


def skewed(cars):
    triples = list(permutations(cars, 3))
    weights = {}
    for triple in triples:
        score = 1.0
        if triple[0] == cars[0]:
            score *= 4.0
        if triple[1] == cars[1]:
            score *= 2.0
        if triple[2] == cars[2]:
            score *= 1.5
        weights[triple] = score
    total = sum(weights.values())
    return {triple: weight / total for triple, weight in weights.items()}


def selftest():
    out = c.compare_named_models(
        {
            "C0": uniform((1, 2, 3, 4)),
            "C1": skewed((1, 2, 3, 4)),
            "N1": skewed((1, 3, 2, 4)),
        },
        required_roi=0.10,
    )
    assert set(out["models"]) == {"C0", "C1", "N1"}
    for model in out["models"].values():
        assert len(model["structures"]) >= 5
        assert model["lowest_uniform_odds_structure"]["combination_count"] >= 1
    assert out["live_odds_used"] is False
    assert out["result_used"] is False
    return {
        "status": "PASS",
        "models": ["C0", "C1", "N1"],
        "same_structure_family_compared": True,
        "live_odds_used": False,
        "result_used": False,
    }


if __name__ == "__main__":
    print(selftest())
