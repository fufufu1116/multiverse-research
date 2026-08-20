from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Sequence

from balanced_synthetic_sampler_v1 import balanced_races, stratum_counts
from digital_twin_stress_grid_v1 import StressAssumptions, stress_truth_joint
from digital_twin_v1 import Race, Top3, pre_view
from top3_architecture_core_v1 import (
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)

HERE = Path(__file__).resolve().parent
PREREG = HERE.parent / "governance" / "KEIRIN_PREREG_BALANCED_SYNTHETIC_ABLATION_v1.json"


@dataclass(frozen=True, order=True)
class C1Params:
    line_mean_coef: float
    position_scale: float
    size_coef: float


@dataclass(frozen=True, order=True)
class N1Params:
    same_line_coef: float
    follower_coef: float
    chain_coef: float


def _load_prereg() -> tuple[dict, str]:
    raw = PREREG.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    if data.get("status") != "PREREGISTERED_DESIGN_NOT_FINAL_HOLDOUT_EXECUTED":
        raise ValueError("unexpected_prereg_status")
    if data["real_validation_rule"] != "UNTOUCHED_VALIDATION_MAY_OPEN = NO":
        raise ValueError("real_validation_gate_drift")
    return data, digest


def _scenario(row: Mapping[str, object], prefix: str) -> StressAssumptions:
    scenario_id = str(row["id"])
    if not scenario_id.startswith(prefix):
        raise ValueError(f"scenario_prefix_mismatch:{scenario_id}:{prefix}")
    return StressAssumptions(
        scenario_id=scenario_id,
        world_family=prefix.rstrip("_"),
        assurance="ASSUMPTION_RANGE_ONLY",
        line_static_scale=float(row["line_static_scale"]),
        relation_strength=float(row["relation_strength"]),
        wind_effect_scale=float(row["wind_effect_scale"]),
        bank_effect_scale=float(row["bank_effect_scale"]),
        disruption_weight=float(row["disruption_weight"]),
        shock_sigma=float(row["shock_sigma"]),
        shock_temperature=float(row["shock_temperature"]),
        disrupted_relation_strength=float(row["disrupted_relation_strength"]),
    )


def _line_features(pre: Mapping[str, object]) -> tuple[dict[int, dict], dict[int, float]]:
    riders = {int(r["car_no"]): dict(r) for r in pre["riders"]}
    groups: dict[int, list[float]] = {}
    for r in riders.values():
        groups.setdefault(int(r["line_group_id"]), []).append(float(r["score"]))
    line_mean = {k: sum(v) / len(v) for k, v in groups.items()}
    return riders, line_mean


def _c0(pre: Mapping[str, object]) -> Dict[Top3, float]:
    return pl_top3_from_runner_utilities(
        {int(r["car_no"]): float(r["score"]) for r in pre["riders"]}
    )


def _c1_utilities(
    pre: Mapping[str, object],
    params: C1Params,
    shrinkage: float = 1.0,
) -> Dict[int, float]:
    riders, line_mean = _line_features(pre)
    out: Dict[int, float] = {}
    for car, r in riders.items():
        pos = int(r["line_position"])
        size = int(r["line_size"])
        position_basis = {0: 0.03, 1: 0.08, 2: 0.04}.get(pos, 0.0)
        out[car] = (
            float(r["score"])
            + shrinkage * params.line_mean_coef * line_mean[int(r["line_group_id"])]
            + shrinkage * params.position_scale * position_basis
            + shrinkage * params.size_coef * max(0, size - 1)
        )
    return out


def _c1(
    pre: Mapping[str, object],
    params: C1Params,
    shrinkage: float = 1.0,
) -> Dict[Top3, float]:
    return pl_top3_from_runner_utilities(_c1_utilities(pre, params, shrinkage))


def _n1(
    pre: Mapping[str, object],
    c1_params: C1Params,
    n1_params: N1Params,
    shrinkage: float = 1.0,
) -> Dict[Top3, float]:
    riders, _ = _line_features(pre)
    p1 = _c1_utilities(pre, c1_params, shrinkage)
    cars = list(p1)

    same_coef = shrinkage * n1_params.same_line_coef
    follower_coef = shrinkage * n1_params.follower_coef
    chain_coef = shrinkage * n1_params.chain_coef

    p2: Dict[tuple[int, int], float] = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = float(rc["line_group_id"] == rf["line_group_id"])
            follower = float(
                same and int(rc["line_position"]) == int(rf["line_position"]) + 1
            )
            p2[(first, candidate)] = p1[candidate] + same_coef * same + follower_coef * follower

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
                    and int(rf["line_position"]) < int(rs["line_position"]) < int(rc["line_position"])
                )
                p3[(first, second, candidate)] = (
                    p1[candidate]
                    + 0.50 * same_coef * same_f
                    + 0.40 * same_coef * same_s
                    + chain_coef * chain
                )

    return conditional_top3_from_context_logits(p1, p2, p3)


def _expected_log_loss(truth: Mapping[Top3, float], pred: Mapping[Top3, float]) -> float:
    eps = 1e-300
    return -sum(float(q) * math.log(max(eps, float(pred[k]))) for k, q in truth.items())


def _truth_entropy(truth: Mapping[Top3, float]) -> float:
    eps = 1e-300
    return -sum(float(q) * math.log(max(eps, float(q))) for q in truth.values())


def _joint_brier(truth: Mapping[Top3, float], pred: Mapping[Top3, float]) -> float:
    return sum((float(pred[k]) - float(q)) ** 2 for k, q in truth.items())


def _build_split(seed_values: Sequence[int], repeats_per_stratum: int) -> list[Race]:
    races: list[Race] = []
    for seed in seed_values:
        races.extend(balanced_races(seed=seed, repeats_per_stratum=repeats_per_stratum))
    return races


def _truth_cache(
    races: Sequence[Race],
    scenarios: Sequence[StressAssumptions],
) -> list[tuple[Mapping[str, object], list[Dict[Top3, float]]]]:
    out = []
    for race in races:
        truths = [stress_truth_joint(race, cfg) for cfg in scenarios]
        out.append((pre_view(race), truths))
    return out


def _mean_ll(
    cache: Sequence[tuple[Mapping[str, object], Sequence[Mapping[Top3, float]]]],
    predict: Callable[[Mapping[str, object]], Mapping[Top3, float]],
) -> float:
    total = 0.0
    n = 0
    for pre, truths in cache:
        pred = predict(pre)
        if abs(sum(pred.values()) - 1.0) > 1e-10:
            raise ValueError("prediction_mass_mismatch")
        for truth in truths:
            if set(pred) != set(truth):
                raise ValueError("prediction_truth_support_mismatch")
            total += _expected_log_loss(truth, pred)
            n += 1
    if n == 0:
        raise ValueError("empty_objective")
    return total / n


def _l1_c1(p: C1Params) -> float:
    return abs(p.line_mean_coef) + abs(p.position_scale) + abs(p.size_coef)


def _l1_n1(p: N1Params) -> float:
    return abs(p.same_line_coef) + abs(p.follower_coef) + abs(p.chain_coef)


def _select_best(rows: Iterable[tuple[float, float, tuple, object]]):
    rows = list(rows)
    if not rows:
        raise ValueError("empty_candidate_set")
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    return rows[0]


def fit_train_cal() -> dict:
    prereg, prereg_sha256 = _load_prereg()
    repeats = int(prereg["sample_control"]["repeats_per_stratum"])
    train_races = _build_split(prereg["splits"]["TRAIN"]["seeds"], repeats)
    cal_races = _build_split(prereg["splits"]["CAL"]["seeds"], repeats)
    train_scenarios = [_scenario(x, "TR_") for x in prereg["train_truth_scenarios"]]
    cal_scenarios = [_scenario(x, "CA_") for x in prereg["cal_truth_scenarios"]]
    train_cache = _truth_cache(train_races, train_scenarios)
    cal_cache = _truth_cache(cal_races, cal_scenarios)

    c1_grid = prereg["model_search"]["C1_train_grid"]
    c1_rows = []
    for line_mean_coef in c1_grid["line_mean_coef"]:
        for position_scale in c1_grid["position_scale"]:
            for size_coef in c1_grid["size_coef"]:
                p = C1Params(float(line_mean_coef), float(position_scale), float(size_coef))
                score = _mean_ll(train_cache, lambda pre, p=p: _c1(pre, p))
                c1_rows.append((score, _l1_c1(p), tuple(asdict(p).values()), p))
    c1_train_score, _, _, c1_train = _select_best(c1_rows)

    n1_grid = prereg["model_search"]["N1_train_grid_after_C1_base_fit"]
    n1_rows = []
    for same_line_coef in n1_grid["same_line_coef"]:
        for follower_coef in n1_grid["follower_coef"]:
            for chain_coef in n1_grid["chain_coef"]:
                p = N1Params(float(same_line_coef), float(follower_coef), float(chain_coef))
                score = _mean_ll(train_cache, lambda pre, p=p: _n1(pre, c1_train, p))
                n1_rows.append((score, _l1_n1(p), tuple(asdict(p).values()), p))
    n1_train_score, _, _, n1_train = _select_best(n1_rows)

    shrinkages = [float(x) for x in prereg["model_search"]["CAL_shrinkage_candidates"]]
    c1_cal_rows = []
    n1_cal_rows = []
    for shrink in shrinkages:
        c1_score = _mean_ll(cal_cache, lambda pre, s=shrink: _c1(pre, c1_train, s))
        c1_cal_rows.append((c1_score, abs(shrink - 1.0), (shrink,), shrink))
        n1_score = _mean_ll(cal_cache, lambda pre, s=shrink: _n1(pre, c1_train, n1_train, s))
        n1_cal_rows.append((n1_score, abs(shrink - 1.0), (shrink,), shrink))

    c1_cal_score, _, _, c1_shrink = _select_best(c1_cal_rows)
    n1_cal_score, _, _, n1_shrink = _select_best(n1_cal_rows)
    c0_cal_score = _mean_ll(cal_cache, _c0)

    return {
        "record": "KEIRIN_BALANCED_SYNTHETIC_FIT_CAL_RESULT_v1",
        "status": "TRAIN_CAL_COMPLETE_COEFFICIENTS_FROZEN_PENDING_LAB_RECHECK_AND_HOLDOUT",
        "prereg_sha256": prereg_sha256,
        "scientific_claim_limit": "SYNTHETIC_ENGINEERING_ONLY_NO_REAL_EDGE_OR_REAL_VALIDATION_CLAIM",
        "sample": {
            "train_races": len(train_races),
            "cal_races": len(cal_races),
            "train_strata": stratum_counts(train_races),
            "cal_strata": stratum_counts(cal_races),
        },
        "frozen_after_cal": {
            "C0": {"architecture": "score_only_PL", "fitted": False},
            "C1": {
                "train_params": asdict(c1_train),
                "train_mean_log_loss": c1_train_score,
                "cal_shrinkage": c1_shrink,
                "cal_mean_log_loss": c1_cal_score,
            },
            "N1": {
                "c1_base_train_params": asdict(c1_train),
                "conditional_train_params": asdict(n1_train),
                "train_mean_log_loss": n1_train_score,
                "cal_shrinkage": n1_shrink,
                "cal_mean_log_loss": n1_cal_score,
            },
            "C0_cal_mean_log_loss": c0_cal_score,
        },
        "holdout_execution": "NOT_EXECUTED",
        "post_holdout_retuning": "PROHIBITED",
        "untouched_real_validation_may_open": False,
    }


def main() -> None:
    # This module is intentionally TRAIN/CAL-only.
    # Fresh synthetic holdout is available only through locked_synthetic_holdout_runner_v1.py,
    # which binds execution to the exact frozen receipt identity.
    result = fit_train_cal()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
