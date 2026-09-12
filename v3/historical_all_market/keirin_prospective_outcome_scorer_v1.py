#!/usr/bin/env python3
"""Deterministic offline scorer for frozen prospective keirin predictions."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

SUM_TOLERANCE = 1e-9


class ScoringError(ValueError):
    """Fail-closed validation error."""


def _load_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, dict):
        raise ScoringError(f"JSON root must be an object: {path}")
    return obj


def _race_map(doc: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    races = doc.get("races")
    if not isinstance(races, Mapping) or not races:
        raise ScoringError(f"{label}.races must be a non-empty object")
    return races


def _normalise_race_ids(values: Iterable[Any]) -> List[str]:
    ids = [str(v) for v in values]
    if len(ids) != len(set(ids)):
        raise ScoringError("expected race IDs contain duplicates")
    return ids


def _extract_ranked(race: Mapping[str, Any], race_id: str) -> List[Tuple[int, str, float]]:
    raw = race.get("probabilities_ranked")
    if raw is None:
        raw = race.get("b1a_probabilities")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ScoringError(
            f"race {race_id}: missing probabilities_ranked/b1a_probabilities"
        )

    rows: List[Tuple[int, str, float]] = []
    seen_cars = set()
    for idx, row in enumerate(raw, start=1):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) < 3:
            raise ScoringError(f"race {race_id}: probability row {idx} must have car,name,prob")
        car = int(row[0])
        name = str(row[1])
        prob = float(row[2])
        if car in seen_cars:
            raise ScoringError(f"race {race_id}: duplicate car_no {car}")
        if not name:
            raise ScoringError(f"race {race_id}: empty name for car_no {car}")
        if not math.isfinite(prob) or prob <= 0.0 or prob > 1.0:
            raise ScoringError(f"race {race_id}: invalid probability for car_no {car}: {prob}")
        seen_cars.add(car)
        rows.append((car, name, prob))

    total = math.fsum(r[2] for r in rows)
    if abs(total - 1.0) > SUM_TOLERANCE:
        raise ScoringError(f"race {race_id}: probability sum {total!r} is not 1")

    for left, right in zip(rows, rows[1:]):
        if left[2] + 1e-15 < right[2]:
            raise ScoringError(f"race {race_id}: probability rows are not ranked descending")
    return rows


def _extract_winner(outcome: Any, race_id: str) -> Tuple[int, str | None]:
    if isinstance(outcome, bool):
        raise ScoringError(f"race {race_id}: boolean outcome is invalid")
    if isinstance(outcome, (int, float)):
        car = int(outcome)
        if float(car) != float(outcome):
            raise ScoringError(f"race {race_id}: winner car must be an integer")
        return car, None
    if not isinstance(outcome, Mapping):
        raise ScoringError(f"race {race_id}: outcome must be object or winner car number")
    if "winner_car_no" not in outcome:
        raise ScoringError(f"race {race_id}: missing winner_car_no")
    car = int(outcome["winner_car_no"])
    name = outcome.get("winner_name")
    return car, None if name is None else str(name)


def _wilson_interval(hits: int, n: int, z: float = 1.959963984540054) -> List[float]:
    if n <= 0:
        return [0.0, 0.0]
    p = hits / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def score_predictions(
    predictions: Mapping[str, Any],
    outcomes: Mapping[str, Any],
    expected_races: Iterable[Any] | None = None,
) -> Dict[str, Any]:
    pred_races = _race_map(predictions, "predictions")
    outcome_races = _race_map(outcomes, "outcomes")

    if expected_races is None:
        target_ids = list(pred_races.keys())
    else:
        target_ids = _normalise_race_ids(expected_races)

    if not target_ids:
        raise ScoringError("no target races")

    missing_pred = [rid for rid in target_ids if rid not in pred_races]
    missing_out = [rid for rid in target_ids if rid not in outcome_races]
    if missing_pred:
        raise ScoringError(f"missing predictions for races: {','.join(missing_pred)}")
    if missing_out:
        raise ScoringError(f"missing outcomes for races: {','.join(missing_out)}")

    if expected_races is None:
        extra_out = [rid for rid in outcome_races if rid not in pred_races]
        if extra_out:
            raise ScoringError(f"outcomes contain races absent from predictions: {','.join(extra_out)}")
        extra_pred = [rid for rid in pred_races if rid not in outcome_races]
        if extra_pred:
            raise ScoringError(f"predictions contain races absent from outcomes: {','.join(extra_pred)}")

    per_race: Dict[str, Any] = {}
    top1_hits = 0
    top3_hits = 0
    losses: List[float] = []

    for rid in target_ids:
        pred_obj = pred_races[rid]
        if not isinstance(pred_obj, Mapping):
            raise ScoringError(f"race {rid}: prediction object must be an object")
        ranked = _extract_ranked(pred_obj, rid)
        winner_car, outcome_winner_name = _extract_winner(outcome_races[rid], rid)

        by_car = {car: (rank, name, prob) for rank, (car, name, prob) in enumerate(ranked, start=1)}
        if winner_car not in by_car:
            raise ScoringError(f"race {rid}: winner car {winner_car} absent from candidate set")
        winner_rank, model_winner_name, winner_prob = by_car[winner_car]
        if outcome_winner_name is not None and outcome_winner_name != model_winner_name:
            raise ScoringError(
                f"race {rid}: winner name mismatch: outcome={outcome_winner_name!r}, "
                f"prediction={model_winner_name!r}"
            )

        top_car, top_name, top_prob = ranked[0]
        top1_hit = winner_rank == 1
        top3_hit = winner_rank <= 3
        nll = -math.log(winner_prob)

        top1_hits += int(top1_hit)
        top3_hits += int(top3_hit)
        losses.append(nll)
        per_race[rid] = {
            "winner_car_no": winner_car,
            "winner_name": model_winner_name,
            "winner_model_rank": winner_rank,
            "winner_probability": winner_prob,
            "top1_car_no": top_car,
            "top1_name": top_name,
            "top1_probability": top_prob,
            "top1_hit": top1_hit,
            "top3_hit": top3_hit,
            "negative_log_likelihood": nll,
        }

    n = len(target_ids)
    return {
        "status": "PASS",
        "scoring_policy": {
            "deterministic": True,
            "retune": False,
            "actual_odds_used": False,
            "probability_sum_tolerance": SUM_TOLERANCE,
        },
        "race_ids": target_ids,
        "per_race": per_race,
        "metrics": {
            "n": n,
            "top1_hits": top1_hits,
            "top1_accuracy": top1_hits / n,
            "top1_wilson_95_ci": _wilson_interval(top1_hits, n),
            "winner_in_top3": top3_hits,
            "winner_in_top3_rate": top3_hits / n,
            "winner_in_top3_wilson_95_ci": _wilson_interval(top3_hits, n),
            "multiclass_log_loss": math.fsum(losses) / n,
        },
    }


def _self_test() -> None:
    pred = {
        "races": {
            "1": {"probabilities_ranked": [[1, "A", 0.6], [2, "B", 0.3], [3, "C", 0.1]]},
            "2": {"b1a_probabilities": [[1, "D", 0.5], [2, "E", 0.3], [3, "F", 0.2]]},
        }
    }
    out = {"races": {"1": {"winner_car_no": 1, "winner_name": "A"}, "2": 3}}
    got = score_predictions(pred, out)
    assert got["metrics"]["n"] == 2
    assert got["metrics"]["top1_hits"] == 1
    assert got["metrics"]["winner_in_top3"] == 2
    expected = (-math.log(0.6) - math.log(0.2)) / 2.0
    assert abs(got["metrics"]["multiclass_log_loss"] - expected) < 1e-15

    bad = {"races": {"1": {"probabilities_ranked": [[1, "A", 0.7], [2, "B", 0.2]]}}}
    try:
        score_predictions(bad, {"races": {"1": 1}})
    except ScoringError:
        pass
    else:
        raise AssertionError("invalid probability sum did not fail closed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", help="Frozen prediction JSON")
    parser.add_argument("--outcomes", help="Outcome JSON")
    parser.add_argument("--output", help="Write scoring JSON here; stdout if omitted")
    parser.add_argument(
        "--expected-races",
        help="Comma-separated race IDs. If omitted, prediction/outcome race sets must match exactly.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        print("PASS")
        return 0

    if not args.predictions or not args.outcomes:
        parser.error("--predictions and --outcomes are required unless --self-test is used")

    expected = None
    if args.expected_races is not None:
        expected = [part.strip() for part in args.expected_races.split(",") if part.strip()]
        if not expected:
            parser.error("--expected-races must contain at least one race ID")

    result = score_predictions(
        _load_json(args.predictions),
        _load_json(args.outcomes),
        expected_races=expected,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
