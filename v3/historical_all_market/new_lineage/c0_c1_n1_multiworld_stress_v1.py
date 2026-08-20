from __future__ import annotations

from dataclasses import replace
import json
import math
from typing import Dict, Mapping, Tuple

from digital_twin_v1 import generate_race, pre_view
from digital_twin_stress_grid_v1 import (
    ASSUMPTION_GRID,
    stress_truth_joint,
    validate_assumption_grid,
)
from top3_architecture_core_v1 import (
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)

Top3 = Tuple[int, int, int]


def _c0(pre: Mapping[str, object]) -> Dict[Top3, float]:
    riders = pre["riders"]
    util = {int(r["car_no"]): float(r["score"]) for r in riders}
    return pl_top3_from_runner_utilities(util)


def _line_features(pre: Mapping[str, object]) -> tuple[dict[int, dict], dict[int, float]]:
    riders = {int(r["car_no"]): dict(r) for r in pre["riders"]}
    groups: dict[int, list[float]] = {}
    for r in riders.values():
        groups.setdefault(int(r["line_group_id"]), []).append(float(r["score"]))
    line_mean = {k: sum(v) / len(v) for k, v in groups.items()}
    return riders, line_mean


def _c1_utilities(pre: Mapping[str, object]) -> Dict[int, float]:
    riders, line_mean = _line_features(pre)
    out: Dict[int, float] = {}
    for car, r in riders.items():
        pos = int(r["line_position"])
        size = int(r["line_size"])
        pos_bonus = {0: 0.03, 1: 0.08, 2: 0.04}.get(pos, 0.0)
        size_bonus = 0.02 * max(0, size - 1)
        out[car] = (
            float(r["score"])
            + 0.10 * line_mean[int(r["line_group_id"])]
            + pos_bonus
            + size_bonus
        )
    return out


def _c1(pre: Mapping[str, object]) -> Dict[Top3, float]:
    return pl_top3_from_runner_utilities(_c1_utilities(pre))


def _n1(pre: Mapping[str, object]) -> Dict[Top3, float]:
    riders, _ = _line_features(pre)
    p1 = _c1_utilities(pre)
    cars = list(p1)

    p2: Dict[tuple[int, int], float] = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = float(rc["line_group_id"] == rf["line_group_id"])
            follower = float(
                same
                and int(rc["line_position"]) == int(rf["line_position"]) + 1
            )
            p2[(first, candidate)] = (
                p1[candidate] + 0.20 * same + 0.18 * follower
            )

    p3: Dict[tuple[int, int, int], float] = {}
    for first in cars:
        rf = riders[first]
        for second in cars:
            if second == first:
                continue
            rs = riders[second]
            for candidate in cars:
                if candidate in (first, second):
                    continue
                rc = riders[candidate]
                same_f = float(rc["line_group_id"] == rf["line_group_id"])
                same_s = float(rc["line_group_id"] == rs["line_group_id"])
                chain = float(
                    rf["line_group_id"] == rs["line_group_id"] == rc["line_group_id"]
                    and int(rf["line_position"])
                    < int(rs["line_position"])
                    < int(rc["line_position"])
                )
                p3[(first, second, candidate)] = (
                    p1[candidate]
                    + 0.10 * same_f
                    + 0.08 * same_s
                    + 0.20 * chain
                )

    return conditional_top3_from_context_logits(p1, p2, p3)


# These are deliberately fixed architecture proxies, not fitted real-keirin models.
# Do not retune coefficients merely to win this synthetic grid.
MODELS = {"C0": _c0, "C1": _c1, "N1": _n1}


def _expected_log_loss(
    truth: Mapping[Top3, float],
    pred: Mapping[Top3, float],
) -> float:
    eps = 1e-300
    return -sum(
        float(q) * math.log(max(eps, float(pred[k])))
        for k, q in truth.items()
    )


def _truth_entropy(truth: Mapping[Top3, float]) -> float:
    eps = 1e-300
    return -sum(
        float(q) * math.log(max(eps, float(q)))
        for q in truth.values()
    )


def _joint_brier(
    truth: Mapping[Top3, float],
    pred: Mapping[Top3, float],
) -> float:
    return sum((float(pred[k]) - float(q)) ** 2 for k, q in truth.items())


def _stress_race(seed: int, race_index: int):
    """Equalize environment coverage without claiming real population frequencies."""
    race = generate_race(
        seed=seed,
        race_index=race_index,
        event_format="STANDARD_FI_FII_7",
    )
    bank_cycle = (333, 400, 500)
    wind_cycle = (0.0, 1.5, 3.0, 5.0)
    return replace(
        race,
        bank_length_m=bank_cycle[race_index % len(bank_cycle)],
        wind_speed_mps=wind_cycle[race_index % len(wind_cycle)],
    )


def evaluate(
    seed: int = 20260820,
    n_races: int = 48,
) -> dict:
    validate_assumption_grid()

    totals = {
        cfg.scenario_id: {
            model: {"log_loss": 0.0, "kl": 0.0, "brier": 0.0}
            for model in MODELS
        }
        for cfg in ASSUMPTION_GRID
    }

    for race_index in range(n_races):
        race = _stress_race(seed, race_index)
        pre = pre_view(race)
        predictions = {name: fn(pre) for name, fn in MODELS.items()}

        for cfg in ASSUMPTION_GRID:
            truth = stress_truth_joint(race, cfg)
            entropy = _truth_entropy(truth)
            if abs(sum(truth.values()) - 1.0) > 1e-10:
                raise AssertionError(f"truth_mass_failed:{cfg.scenario_id}")

            for model, pred in predictions.items():
                if set(pred) != set(truth):
                    raise AssertionError(
                        f"support_mismatch:{cfg.scenario_id}:{model}"
                    )
                if abs(sum(pred.values()) - 1.0) > 1e-10:
                    raise AssertionError(
                        f"prediction_mass_failed:{cfg.scenario_id}:{model}"
                    )
                ll = _expected_log_loss(truth, pred)
                totals[cfg.scenario_id][model]["log_loss"] += ll
                totals[cfg.scenario_id][model]["kl"] += ll - entropy
                totals[cfg.scenario_id][model]["brier"] += _joint_brier(truth, pred)

    scenarios = []
    for cfg in ASSUMPTION_GRID:
        rows = {}
        for model in MODELS:
            rows[model] = {
                metric: value / n_races
                for metric, value in totals[cfg.scenario_id][model].items()
            }
        winner = min(rows, key=lambda m: rows[m]["log_loss"])
        scenarios.append(
            {
                "scenario_id": cfg.scenario_id,
                "world_family": cfg.world_family,
                "assurance": cfg.assurance,
                "winner_by_expected_log_loss": winner,
                "models": rows,
            }
        )

    win_counts = {model: 0 for model in MODELS}
    for row in scenarios:
        win_counts[row["winner_by_expected_log_loss"]] += 1

    return {
        "record": "C0_C1_N1_MULTIWORLD_SYNTHETIC_STRESS_v1",
        "status": "SYNTHETIC_ENGINEERING_EVIDENCE_ONLY",
        "seed": seed,
        "n_races_per_scenario": n_races,
        "scenario_count": len(ASSUMPTION_GRID),
        "scientific_claim_limit": (
            "No real-keirin predictive edge, frequency, causal coefficient, ROI, "
            "or protected-validation claim may be inferred from this run."
        ),
        "sample_weighting_limit": (
            "Race generation is an engineering stress sample; aggregate scores are "
            "not population-weighted real-keirin estimates."
        ),
        "proper_scoring": [
            "expected ordered-top3 log loss under exact synthetic truth",
            "KL(prediction regret to exact synthetic truth)",
            "ordered-top3 joint Brier distance",
        ],
        "win_counts_by_expected_log_loss": win_counts,
        "scenarios": scenarios,
    }


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
