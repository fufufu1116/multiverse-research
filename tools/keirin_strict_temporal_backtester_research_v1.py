from __future__ import annotations

"""Research-only strict temporal evaluation primitives for Keirin.

This module is intentionally source-safe: it contains no network access, no workflow dispatch,
no settlement/payout imports, and no protected-data paths.  It is a prototype harness for toy,
synthetic, or separately authorized point-in-time rows only.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import permutations
import math
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from v3.historical_all_market.new_lineage.probability_object_contract_v1 import (
    fail_closed_probability_object,
)

Top3 = Tuple[int, int, int]


class TemporalBacktestError(ValueError):
    pass


@dataclass(frozen=True)
class FeatureValue:
    name: str
    value: object
    available_at: datetime


@dataclass(frozen=True)
class RaceEvaluationRow:
    race_id: str
    event_id: str
    prediction_timestamp: datetime
    features: Tuple[FeatureValue, ...]
    active_car_nos: Tuple[int, ...]
    observed_top3: Top3


def _require_aware(ts: datetime, label: str) -> None:
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise TemporalBacktestError(f"{label}_must_be_timezone_aware")


def validate_point_in_time_row(row: RaceEvaluationRow) -> None:
    _require_aware(row.prediction_timestamp, "prediction_timestamp")
    if len(set(row.active_car_nos)) != len(row.active_car_nos):
        raise TemporalBacktestError("duplicate_active_car_no")
    if len(row.active_car_nos) < 3:
        raise TemporalBacktestError("fewer_than_three_active_cars")
    if len(set(row.observed_top3)) != 3:
        raise TemporalBacktestError("observed_top3_repeated_car")
    if not set(row.observed_top3).issubset(set(row.active_car_nos)):
        raise TemporalBacktestError("observed_top3_unknown_car")

    seen = set()
    for feature in row.features:
        if feature.name in seen:
            raise TemporalBacktestError(f"duplicate_feature:{feature.name}")
        seen.add(feature.name)
        _require_aware(feature.available_at, f"available_at:{feature.name}")
        if feature.available_at > row.prediction_timestamp:
            raise TemporalBacktestError(
                f"availability_violation:{feature.name}:"
                f"{feature.available_at.isoformat()}>{row.prediction_timestamp.isoformat()}"
            )


def validate_dataset(rows: Sequence[RaceEvaluationRow]) -> None:
    seen_race_ids = set()
    for row in rows:
        validate_point_in_time_row(row)
        if row.race_id in seen_race_ids:
            raise TemporalBacktestError(f"duplicate_race_id:{row.race_id}")
        seen_race_ids.add(row.race_id)


def chronological_split(
    rows: Sequence[RaceEvaluationRow],
    train_end: datetime,
    calibration_end: datetime,
    evaluation_end: datetime,
) -> Dict[str, List[RaceEvaluationRow]]:
    for name, ts in (
        ("train_end", train_end),
        ("calibration_end", calibration_end),
        ("evaluation_end", evaluation_end),
    ):
        _require_aware(ts, name)
    if not train_end < calibration_end < evaluation_end:
        raise TemporalBacktestError("split_boundaries_not_strictly_increasing")

    validate_dataset(rows)
    out = {"TRAIN": [], "CALIBRATION": [], "DEVELOPMENT_EVALUATION": []}
    for row in sorted(rows, key=lambda r: (r.prediction_timestamp, r.race_id)):
        ts = row.prediction_timestamp
        if ts <= train_end:
            out["TRAIN"].append(row)
        elif ts <= calibration_end:
            out["CALIBRATION"].append(row)
        elif ts <= evaluation_end:
            out["DEVELOPMENT_EVALUATION"].append(row)
        else:
            raise TemporalBacktestError(
                f"row_after_authorized_evaluation_window:{row.race_id}"
            )

    _fail_on_event_cross_split(out)
    return out


def _fail_on_event_cross_split(
    split_rows: Mapping[str, Sequence[RaceEvaluationRow]],
) -> None:
    event_to_split: Dict[str, str] = {}
    for split_name, rows in split_rows.items():
        for row in rows:
            prior = event_to_split.get(row.event_id)
            if prior is not None and prior != split_name:
                raise TemporalBacktestError(
                    f"same_event_cross_split:{row.event_id}:{prior}->{split_name}"
                )
            event_to_split[row.event_id] = split_name


def normalized_market_implied_top3(
    active_car_nos: Sequence[int],
    decimal_odds_by_top3: Mapping[Top3, float],
) -> Dict[Top3, float]:
    """Market-only baseline from one timestamp-proven full 3-rentan quote surface.

    Raw inverse decimal odds are normalized across the complete ordered-top3 support.  This is a
    structural baseline only; it does not claim to remove takeout or recover a causal fair price.
    """
    expected = set(permutations(active_car_nos, 3))
    if set(decimal_odds_by_top3) != expected:
        raise TemporalBacktestError("market_quote_support_mismatch")

    raw: Dict[Top3, float] = {}
    for key, odds in decimal_odds_by_top3.items():
        odds = float(odds)
        if not math.isfinite(odds) or odds <= 1.0:
            raise TemporalBacktestError(f"invalid_decimal_odds:{key}")
        raw[key] = 1.0 / odds

    mass = sum(raw.values())
    if not math.isfinite(mass) or mass <= 0.0:
        raise TemporalBacktestError("invalid_market_implied_mass")
    probs = {key: value / mass for key, value in raw.items()}
    _validate_probability_map(active_car_nos, probs)
    return probs


def plackett_luce_top3_from_positive_weights(
    active_car_nos: Sequence[int],
    positive_weight_by_car: Mapping[int, float],
) -> Dict[Top3, float]:
    """Simple score/PL control from already-declared positive PRE weights.

    Weight construction/training is deliberately outside this function so it cannot silently tune
    on evaluation outcomes.
    """
    cars = tuple(active_car_nos)
    if set(positive_weight_by_car) != set(cars):
        raise TemporalBacktestError("weight_support_mismatch")
    weights = {car: float(positive_weight_by_car[car]) for car in cars}
    for car, weight in weights.items():
        if not math.isfinite(weight) or weight <= 0.0:
            raise TemporalBacktestError(f"invalid_positive_weight:{car}")

    probs: Dict[Top3, float] = {}
    total = sum(weights.values())
    for first, second, third in permutations(cars, 3):
        p1 = weights[first] / total
        rem1 = total - weights[first]
        p2 = weights[second] / rem1
        rem2 = rem1 - weights[second]
        p3 = weights[third] / rem2
        probs[(first, second, third)] = p1 * p2 * p3
    _validate_probability_map(cars, probs)
    return probs


def _validate_probability_map(
    active_car_nos: Sequence[int], probabilities: Mapping[Top3, float]
) -> None:
    records = [
        {"first": key[0], "second": key[1], "third": key[2], "p": value}
        for key, value in probabilities.items()
    ]
    fail_closed_probability_object(active_car_nos, records)


def ordered_top3_log_loss(probabilities: Mapping[Top3, float], observed: Top3) -> float:
    p = float(probabilities.get(observed, 0.0))
    if not math.isfinite(p) or p <= 0.0:
        return math.inf
    return -math.log(p)


def ordered_top3_brier(probabilities: Mapping[Top3, float], observed: Top3) -> float:
    score = 0.0
    for key, p in probabilities.items():
        target = 1.0 if key == observed else 0.0
        score += (float(p) - target) ** 2
    return score


def first_place_marginal(probabilities: Mapping[Top3, float]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for (first, _second, _third), p in probabilities.items():
        out[first] = out.get(first, 0.0) + float(p)
    return out


def multiclass_brier_first_place(
    probabilities: Mapping[Top3, float], observed_first: int
) -> float:
    marginal = first_place_marginal(probabilities)
    return sum(
        (p - (1.0 if car == observed_first else 0.0)) ** 2
        for car, p in marginal.items()
    )


def selftest() -> None:
    utc = timezone.utc
    cars = (1, 2, 3, 4)
    t1 = datetime(2026, 1, 1, 1, 0, tzinfo=utc)
    t2 = datetime(2026, 1, 2, 1, 0, tzinfo=utc)
    t3 = datetime(2026, 1, 3, 1, 0, tzinfo=utc)

    rows = [
        RaceEvaluationRow(
            race_id="R1",
            event_id="E1",
            prediction_timestamp=t1,
            features=(FeatureValue("score", 90.0, t1),),
            active_car_nos=cars,
            observed_top3=(1, 2, 3),
        ),
        RaceEvaluationRow(
            race_id="R2",
            event_id="E2",
            prediction_timestamp=t2,
            features=(FeatureValue("score", 91.0, t2),),
            active_car_nos=cars,
            observed_top3=(2, 1, 3),
        ),
        RaceEvaluationRow(
            race_id="R3",
            event_id="E3",
            prediction_timestamp=t3,
            features=(FeatureValue("score", 92.0, t3),),
            active_car_nos=cars,
            observed_top3=(3, 2, 1),
        ),
    ]
    split = chronological_split(
        rows,
        train_end=t1,
        calibration_end=t2,
        evaluation_end=t3,
    )
    assert [r.race_id for r in split["TRAIN"]] == ["R1"]
    assert [r.race_id for r in split["CALIBRATION"]] == ["R2"]
    assert [r.race_id for r in split["DEVELOPMENT_EVALUATION"]] == ["R3"]

    pl = plackett_luce_top3_from_positive_weights(cars, {1: 4, 2: 3, 3: 2, 4: 1})
    assert math.isfinite(ordered_top3_log_loss(pl, (1, 2, 3)))
    assert ordered_top3_brier(pl, (1, 2, 3)) >= 0.0
    assert multiclass_brier_first_place(pl, 1) >= 0.0

    quote_odds = {key: 100.0 + i for i, key in enumerate(permutations(cars, 3))}
    market = normalized_market_implied_top3(cars, quote_odds)
    assert abs(sum(market.values()) - 1.0) < 1e-12

    leaking = RaceEvaluationRow(
        race_id="LEAK",
        event_id="E4",
        prediction_timestamp=t1,
        features=(FeatureValue("future", 1, t2),),
        active_car_nos=cars,
        observed_top3=(1, 2, 3),
    )
    try:
        validate_point_in_time_row(leaking)
    except TemporalBacktestError as exc:
        assert str(exc).startswith("availability_violation:future")
    else:
        raise AssertionError("availability violation did not fail closed")

    print("KEIRIN_STRICT_TEMPORAL_BACKTESTER_RESEARCH_SELFTEST_PASS")


if __name__ == "__main__":
    selftest()
