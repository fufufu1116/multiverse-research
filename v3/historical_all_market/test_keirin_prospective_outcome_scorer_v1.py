#!/usr/bin/env python3
"""Regression tests for keirin_prospective_outcome_scorer_v1."""

from __future__ import annotations

import json
import math
from pathlib import Path

import keirin_prospective_outcome_scorer_v1 as scorer


ROOT = Path(__file__).resolve().parent
OMIYA_20260427 = (
    ROOT
    / "research_candidates"
    / "retrospective_500m_omiya_20260427_confirmatory_full_day"
    / "KEIRIN_OMIYA_20260427_500M_B1A_CONFIRMATORY_FULL_DAY_R1_R12_v1.json"
)


def _load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_self_test() -> None:
    scorer._self_test()


def test_omiya_20260427_regression() -> None:
    historical = _load(OMIYA_20260427)
    outcomes = {
        "races": {
            race_id: {
                "winner_car_no": race["outcome"]["winner_car_no"],
                "winner_name": race["outcome"]["winner_name"],
            }
            for race_id, race in historical["races"].items()
        }
    }
    got = scorer.score_predictions(historical, outcomes)
    metrics = got["metrics"]
    assert metrics["n"] == 12
    assert metrics["top1_hits"] == 6
    assert metrics["top1_accuracy"] == 0.5
    assert metrics["winner_in_top3"] == 9
    assert metrics["winner_in_top3_rate"] == 0.75
    assert math.isclose(
        metrics["multiclass_log_loss"],
        1.5264461189008423,
        rel_tol=0.0,
        abs_tol=1e-15,
    )


def test_fail_closed_missing_outcome() -> None:
    historical = _load(OMIYA_20260427)
    outcomes = {
        "races": {
            race_id: race["outcome"]["winner_car_no"]
            for race_id, race in historical["races"].items()
            if race_id != "12"
        }
    }
    try:
        scorer.score_predictions(historical, outcomes)
    except scorer.ScoringError as exc:
        assert "missing outcomes" in str(exc)
    else:
        raise AssertionError("missing outcome did not fail closed")


def main() -> int:
    test_self_test()
    test_omiya_20260427_regression()
    test_fail_closed_missing_outcome()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
