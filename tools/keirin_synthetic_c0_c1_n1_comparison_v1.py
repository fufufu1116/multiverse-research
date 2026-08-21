#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Dict, Mapping, Tuple

ROOT = Path(__file__).resolve().parents[1]
NEW_LINEAGE = ROOT / "v3" / "historical_all_market" / "new_lineage"
COEFF_RECEIPT = ROOT / "v3" / "historical_all_market" / "governance" / "KEIRIN_FROZEN_PRE_HOLDOUT_COEFFICIENT_RECEIPT_v1.json"
sys.path.insert(0, str(NEW_LINEAGE))

from digital_twin_v1 import Top3, generate_race, pre_view, world_joint_distribution
from top3_architecture_core_v1 import conditional_top3_from_context_logits, pl_top3_from_runner_utilities

WORLDS = ("W0", "W1", "W2", "W3", "W4")
MODELS = ("C0", "C1", "N1")
CASE_COUNT = 128


def _load_frozen_params() -> dict:
    receipt = json.loads(COEFF_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "FROZEN_PRE_HOLDOUT_INPUT_NOT_EXECUTED":
        raise AssertionError("unexpected_pre_holdout_receipt_status")
    if receipt.get("holdout_execution") != "NOT_EXECUTED":
        raise AssertionError("pre_holdout_receipt_execution_drift")
    if receipt.get("post_holdout_retuning") != "PROHIBITED":
        raise AssertionError("retuning_rule_drift")

    frozen = receipt["frozen_after_cal"]
    expected_c1 = {
        "line_mean_coef": 0.0,
        "position_scale": 0.5,
        "size_coef": 0.0,
    }
    expected_n1 = {
        "same_line_coef": 0.1,
        "follower_coef": 0.1,
        "chain_coef": 0.2,
    }
    if frozen["C0"] != {"architecture": "score_only_PL", "fitted": False}:
        raise AssertionError("C0_frozen_definition_drift")
    if frozen["C1"]["train_params"] != expected_c1 or float(frozen["C1"]["cal_shrinkage"]) != 0.75:
        raise AssertionError("C1_frozen_params_drift")
    if frozen["N1"]["c1_base_train_params"] != expected_c1:
        raise AssertionError("N1_C1_base_drift")
    if frozen["N1"]["conditional_train_params"] != expected_n1 or float(frozen["N1"]["cal_shrinkage"]) != 0.75:
        raise AssertionError("N1_frozen_params_drift")
    return frozen


def _line_features(pre: Mapping[str, object]) -> tuple[dict[int, dict], dict[int, float]]:
    riders = {int(r["car_no"]): dict(r) for r in pre["riders"]}
    groups: dict[int, list[float]] = {}
    for rider in riders.values():
        groups.setdefault(int(rider["line_group_id"]), []).append(float(rider["score"]))
    return riders, {group: sum(values) / len(values) for group, values in groups.items()}


def _c0(pre: Mapping[str, object]) -> Dict[Top3, float]:
    return pl_top3_from_runner_utilities(
        {int(r["car_no"]): float(r["score"]) for r in pre["riders"]}
    )


def _c1_utilities(pre: Mapping[str, object], params: Mapping[str, float], shrinkage: float) -> Dict[int, float]:
    riders, line_mean = _line_features(pre)
    out: Dict[int, float] = {}
    for car, rider in riders.items():
        pos = int(rider["line_position"])
        size = int(rider["line_size"])
        position_basis = {0: 0.03, 1: 0.08, 2: 0.04}.get(pos, 0.0)
        out[car] = (
            float(rider["score"])
            + shrinkage * float(params["line_mean_coef"]) * line_mean[int(rider["line_group_id"])]
            + shrinkage * float(params["position_scale"]) * position_basis
            + shrinkage * float(params["size_coef"]) * max(0, size - 1)
        )
    return out


def _c1(pre: Mapping[str, object], params: Mapping[str, float], shrinkage: float) -> Dict[Top3, float]:
    return pl_top3_from_runner_utilities(_c1_utilities(pre, params, shrinkage))


def _n1(
    pre: Mapping[str, object],
    c1_params: Mapping[str, float],
    n1_params: Mapping[str, float],
    shrinkage: float,
) -> Dict[Top3, float]:
    riders, _ = _line_features(pre)
    p1 = _c1_utilities(pre, c1_params, shrinkage)
    cars = list(p1)

    same_coef = shrinkage * float(n1_params["same_line_coef"])
    follower_coef = shrinkage * float(n1_params["follower_coef"])
    chain_coef = shrinkage * float(n1_params["chain_coef"])

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
    return -sum(float(q) * math.log(max(eps, float(pred[key]))) for key, q in truth.items())


def _truth_entropy(truth: Mapping[Top3, float]) -> float:
    eps = 1e-300
    return -sum(float(q) * math.log(max(eps, float(q))) for q in truth.values())


def _joint_brier(truth: Mapping[Top3, float], pred: Mapping[Top3, float]) -> float:
    return sum((float(pred[key]) - float(q)) ** 2 for key, q in truth.items())


def _rank1_marginal(joint: Mapping[Top3, float]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for (first, _second, _third), p in joint.items():
        out[first] = out.get(first, 0.0) + float(p)
    return out


def _assert_probability_object(name: str, pred: Mapping[Top3, float], support: set[Top3]) -> float:
    if set(pred) != support:
        raise AssertionError(f"support_mismatch:{name}")
    mass_error = abs(sum(float(p) for p in pred.values()) - 1.0)
    if mass_error > 1e-10:
        raise AssertionError(f"mass_mismatch:{name}:{mass_error}")
    if any(not math.isfinite(float(p)) or float(p) < 0.0 for p in pred.values()):
        raise AssertionError(f"invalid_probability:{name}")
    return mass_error


def main() -> None:
    frozen = _load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"]:
        raise AssertionError("C1_N1_P1_parameter_basis_mismatch")
    if c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_P1_shrinkage_mismatch")

    totals = {
        world: {
            model: {"expected_log_loss": 0.0, "kl_regret": 0.0, "joint_brier": 0.0}
            for model in MODELS
        }
        for world in WORLDS
    }
    max_prediction_mass_error = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0

    for case in range(CASE_COUNT):
        seed = 20260821 + case
        race_index = case % 32
        race = generate_race(seed=seed, race_index=race_index)
        if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
            raise AssertionError(f"unexpected_format:{case}")
        pre = pre_view(race)
        if any("latent_skill" in rider for rider in pre["riders"]):
            raise AssertionError(f"latent_skill_leak:{case}")

        predictions = {
            "C0": _c0(pre),
            "C1": _c1(pre, c1_params, c1_shrinkage),
            "N1": _n1(pre, c1_params, n1_params, n1_shrinkage),
        }

        c1_rank1 = _rank1_marginal(predictions["C1"])
        n1_rank1 = _rank1_marginal(predictions["N1"])
        if set(c1_rank1) != set(n1_rank1):
            raise AssertionError("C1_N1_rank1_support_mismatch")
        rank1_diff = max(abs(c1_rank1[car] - n1_rank1[car]) for car in c1_rank1)
        max_c1_n1_rank1_marginal_difference = max(max_c1_n1_rank1_marginal_difference, rank1_diff)
        if rank1_diff > 1e-12:
            raise AssertionError(f"C1_N1_shared_P1_invariant_failed:{case}:{rank1_diff}")

        for world in WORLDS:
            truth = world_joint_distribution(race, world)
            support = set(truth)
            truth_mass_error = abs(sum(float(q) for q in truth.values()) - 1.0)
            if truth_mass_error > 1e-10:
                raise AssertionError(f"truth_mass_mismatch:{case}:{world}:{truth_mass_error}")
            entropy = _truth_entropy(truth)

            for model, pred in predictions.items():
                max_prediction_mass_error = max(
                    max_prediction_mass_error,
                    _assert_probability_object(f"{case}:{world}:{model}", pred, support),
                )
                ll = _expected_log_loss(truth, pred)
                totals[world][model]["expected_log_loss"] += ll
                totals[world][model]["kl_regret"] += ll - entropy
                totals[world][model]["joint_brier"] += _joint_brier(truth, pred)

    world_results = {}
    overall = {
        model: {"expected_log_loss": 0.0, "kl_regret": 0.0, "joint_brier": 0.0}
        for model in MODELS
    }
    for world in WORLDS:
        rows = {}
        for model in MODELS:
            rows[model] = {
                metric: total / CASE_COUNT
                for metric, total in totals[world][model].items()
            }
            for metric, value in rows[model].items():
                overall[model][metric] += value / len(WORLDS)
        world_results[world] = {
            "models": rows,
            "diagnostic_deltas_lower_is_better": {
                "C1_minus_C0_expected_log_loss": rows["C1"]["expected_log_loss"] - rows["C0"]["expected_log_loss"],
                "N1_minus_C1_expected_log_loss": rows["N1"]["expected_log_loss"] - rows["C1"]["expected_log_loss"],
                "N1_minus_C0_expected_log_loss": rows["N1"]["expected_log_loss"] - rows["C0"]["expected_log_loss"],
            },
        }

    result = {
        "record": "KEIRIN_SYNTHETIC_C0_C1_N1_COMPARISON_v1",
        "status": "PASS",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "cases": CASE_COUNT,
        "worlds": list(WORLDS),
        "world_evaluations": CASE_COUNT * len(WORLDS),
        "model_world_evaluations": CASE_COUNT * len(WORLDS) * len(MODELS),
        "sampling_matches_batch2": True,
        "fixed_pre_holdout_coefficients_used": True,
        "result_adaptive_sampling_or_retuning": False,
        "locked_legacy_synthetic_holdout_used": False,
        "fresh_synthetic_holdout_used": False,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "world_results": world_results,
        "overall_equal_world_weight_models": overall,
        "scientific_decision": "DIAGNOSTIC_ONLY_NO_MODEL_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
        "real_live_input_collection": False,
        "economics": False,
        "real_world_validation": False,
        "protected_or_quarantined_input": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "holdout_access": False,
        "scientific_segment_c_scoring_count": 0,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_SYNTHETIC_C0_C1_N1_COMPARISON_PASS")


if __name__ == "__main__":
    main()
