#!/usr/bin/env python3
from __future__ import annotations

import ast
import inspect
import json
import math
from pathlib import Path
import sys
from typing import Dict, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
NEW_LINEAGE = ROOT / "v3" / "historical_all_market" / "new_lineage"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(NEW_LINEAGE))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base
import digital_twin_v1 as dt
from top3_architecture_core_v1 import pl_top3_from_runner_utilities

BLOCK_SEED_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128
WORLD = "W1"
MODELS = ("C1", "N1", "C1_ORACLE")
ORACLE_SHARED_COEF = 0.16
EXPECTED_PRIOR_N1_MINUS_C1 = -0.001139094451357625
TOL = 1e-12
TOL_MASS = 1e-10


def _assert_source_boundary() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_direct_latent_functions = {"_oracle_shared_line_state"}

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []
            self.violations: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == "latent_skill":
                current = self.stack[-1] if self.stack else "<module>"
                if current not in allowed_direct_latent_functions:
                    self.violations.append(current)
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(tree)
    if visitor.violations:
        raise AssertionError(f"latent_skill_access_outside_oracle_boundary:{visitor.violations}")

    for fn_name in ("_c1", "_c1_utilities", "_n1"):
        if "latent_skill" in inspect.getsource(getattr(base, fn_name)):
            raise AssertionError(f"latent_skill_present_in_nonoracle_base_function:{fn_name}")


def _assert_pre_has_no_latent(pre: Mapping[str, object]) -> None:
    riders = pre.get("riders")
    if not isinstance(riders, list):
        raise AssertionError("invalid_PRE_riders")
    for rider in riders:
        if not isinstance(rider, dict):
            raise AssertionError("invalid_PRE_rider")
        if "latent_skill" in rider:
            raise AssertionError("latent_skill_leaked_into_PRE")


def _oracle_shared_line_state(race: dt.Race) -> Dict[int, float]:
    groups: Dict[int, list[float]] = {}
    for rider in race.riders:
        groups.setdefault(int(rider.line_id), []).append(float(rider.latent_skill))
    return {line_id: sum(values) / len(values) for line_id, values in groups.items()}


def _oracle_shared_component(race: dt.Race) -> Dict[int, float]:
    state = _oracle_shared_line_state(race)
    return {
        int(rider.car_no): ORACLE_SHARED_COEF * state[int(rider.line_id)]
        for rider in race.riders
    }


def _assert_oracle_information_sufficiency(race: dt.Race) -> float:
    oracle = _oracle_shared_component(race)
    w0_util = dt._static_utilities(race, use_line=False)
    w1_util = dt._static_utilities(race, use_line=True)
    max_diff = 0.0
    for rider in race.riders:
        pos_bonus = {0: 0.04, 1: 0.10, 2: 0.05}.get(int(rider.line_position), 0.0)
        size_bonus = 0.025 * max(0, int(rider.line_size) - 1)
        canonical_shared = (
            float(w1_util[int(rider.car_no)])
            - float(w0_util[int(rider.car_no)])
            - pos_bonus
            - size_bonus
        )
        diff = abs(canonical_shared - oracle[int(rider.car_no)])
        max_diff = max(max_diff, diff)
    if max_diff > TOL:
        raise AssertionError(f"oracle_information_insufficient_or_mismatched:{max_diff}")
    return max_diff


def _c1_oracle(
    pre: Mapping[str, object],
    race: dt.Race,
    c1_params: Mapping[str, float],
    shrinkage: float,
) -> Dict[dt.Top3, float]:
    _assert_pre_has_no_latent(pre)
    ordinary_c1_util = base._c1_utilities(pre, c1_params, shrinkage)
    oracle_component = _oracle_shared_component(race)
    if set(ordinary_c1_util) != set(oracle_component):
        raise AssertionError("oracle_C1_support_mismatch")
    oracle_util = {
        car: float(ordinary_c1_util[car]) + float(oracle_component[car])
        for car in ordinary_c1_util
    }
    return pl_top3_from_runner_utilities(oracle_util)


def _assert_probability_object(
    name: str,
    pred: Mapping[dt.Top3, float],
    support: set[dt.Top3],
) -> float:
    if set(pred) != support:
        raise AssertionError(f"support_mismatch:{name}")
    mass_error = abs(sum(float(p) for p in pred.values()) - 1.0)
    if mass_error > TOL_MASS:
        raise AssertionError(f"mass_mismatch:{name}:{mass_error}")
    if any(not math.isfinite(float(p)) or float(p) < 0.0 for p in pred.values()):
        raise AssertionError(f"invalid_probability:{name}")
    return mass_error


def _expected_log_loss(
    truth: Mapping[dt.Top3, float],
    pred: Mapping[dt.Top3, float],
) -> float:
    eps = 1e-300
    return -sum(float(q) * math.log(max(eps, float(pred[key]))) for key, q in truth.items())


def _chain_cross_entropy(
    truth: Mapping[dt.Top3, float],
    pred: Mapping[dt.Top3, float],
) -> Dict[str, float]:
    eps = 1e-300
    p1: Dict[int, float] = {}
    p12: Dict[tuple[int, int], float] = {}
    for (i, j, _k), p in pred.items():
        p1[i] = p1.get(i, 0.0) + float(p)
        p12[(i, j)] = p12.get((i, j), 0.0) + float(p)

    rank1 = 0.0
    rank2 = 0.0
    rank3 = 0.0
    for (i, j, k), q_raw in truth.items():
        q = float(q_raw)
        p1_i = max(eps, p1[i])
        p12_ij = max(eps, p12[(i, j)])
        p2 = max(eps, p12_ij / p1_i)
        p3 = max(eps, float(pred[(i, j, k)]) / p12_ij)
        rank1 -= q * math.log(p1_i)
        rank2 -= q * math.log(p2)
        rank3 -= q * math.log(p3)
    return {"rank1": rank1, "rank2": rank2, "rank3": rank3, "total": rank1 + rank2 + rank3}


def _max_prediction_diff(a: Mapping[dt.Top3, float], b: Mapping[dt.Top3, float]) -> float:
    if set(a) != set(b):
        raise AssertionError("prediction_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


def _classification(n1_minus_c1_oracle: float, baseline_n1_minus_c1: float) -> tuple[str, float]:
    if baseline_n1_minus_c1 >= 0.0:
        raise AssertionError("prior_baseline_not_an_N1_advantage")
    if n1_minus_c1_oracle >= 0.0:
        return "ADVANTAGE_DISAPPEARS_OR_REVERSES_STRONG_SUPPORT", 0.0
    residual_ratio = abs(n1_minus_c1_oracle) / abs(baseline_n1_minus_c1)
    if residual_ratio <= 0.25:
        return "ADVANTAGE_MAJORITY_ERASED_STRONG_SUPPORT", residual_ratio
    if residual_ratio <= 0.75:
        return "PARTIAL_SHRINK_MIXED_MECHANISM", residual_ratio
    return "LITTLE_CHANGE_CLEAR_RESIDUAL_WEAKENS_DOMINANT_PROXY", residual_ratio


def main() -> None:
    _assert_source_boundary()
    frozen = base._load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])

    if c1_params != frozen["N1"]["c1_base_train_params"]:
        raise AssertionError("C1_N1_base_parameter_drift")
    if c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_shrinkage_drift")

    aggregate_sums = {
        model: {"rank1": 0.0, "rank2": 0.0, "rank3": 0.0, "total": 0.0}
        for model in MODELS
    }
    block_results: Dict[str, object] = {}
    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_decomposition_residual = 0.0
    max_oracle_component_diff = 0.0
    max_nonoracle_C1_reproduction_diff = 0.0
    max_nonoracle_N1_reproduction_diff = 0.0

    for block_seed in BLOCK_SEED_BASES:
        block_sums = {
            model: {"rank1": 0.0, "rank2": 0.0, "rank3": 0.0, "total": 0.0}
            for model in MODELS
        }
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = dt.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block_seed}:{case}")

            pre = dt.pre_view(race)
            _assert_pre_has_no_latent(pre)
            max_oracle_component_diff = max(
                max_oracle_component_diff,
                _assert_oracle_information_sufficiency(race),
            )

            c1 = base._c1(pre, c1_params, c1_shrinkage)
            n1 = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            c1_oracle = _c1_oracle(pre, race, c1_params, c1_shrinkage)

            c1_repeat = base._c1(pre, c1_params, c1_shrinkage)
            n1_repeat = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            max_nonoracle_C1_reproduction_diff = max(
                max_nonoracle_C1_reproduction_diff,
                _max_prediction_diff(c1, c1_repeat),
            )
            max_nonoracle_N1_reproduction_diff = max(
                max_nonoracle_N1_reproduction_diff,
                _max_prediction_diff(n1, n1_repeat),
            )

            truth = dt.world_joint_distribution(race, WORLD)
            support = set(truth)
            truth_mass_error = abs(sum(float(q) for q in truth.values()) - 1.0)
            max_truth_mass_error = max(max_truth_mass_error, truth_mass_error)
            if truth_mass_error > TOL_MASS:
                raise AssertionError(f"truth_mass_mismatch:{block_seed}:{case}:{truth_mass_error}")

            predictions = {"C1": c1, "N1": n1, "C1_ORACLE": c1_oracle}
            for model, pred in predictions.items():
                max_prediction_mass_error = max(
                    max_prediction_mass_error,
                    _assert_probability_object(f"{block_seed}:{case}:{model}", pred, support),
                )
                chain = _chain_cross_entropy(truth, pred)
                direct = _expected_log_loss(truth, pred)
                residual = abs(chain["total"] - direct)
                max_decomposition_residual = max(max_decomposition_residual, residual)
                if residual > TOL:
                    raise AssertionError(f"chain_decomposition_residual:{block_seed}:{case}:{model}:{residual}")
                for metric in ("rank1", "rank2", "rank3", "total"):
                    block_sums[model][metric] += float(chain[metric])
                    aggregate_sums[model][metric] += float(chain[metric])

        block_means = {
            model: {metric: value / CASES_PER_BLOCK for metric, value in sums.items()}
            for model, sums in block_sums.items()
        }
        block_n1_minus_c1 = block_means["N1"]["total"] - block_means["C1"]["total"]
        block_n1_minus_oracle = block_means["N1"]["total"] - block_means["C1_ORACLE"]["total"]
        block_class, block_ratio = _classification(block_n1_minus_oracle, block_n1_minus_c1)
        block_results[str(block_seed)] = {
            "model_chain_cross_entropy": block_means,
            "N1_minus_C1": {
                metric: block_means["N1"][metric] - block_means["C1"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
            "N1_minus_C1_ORACLE": {
                metric: block_means["N1"][metric] - block_means["C1_ORACLE"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
            "C1_ORACLE_minus_C1": {
                metric: block_means["C1_ORACLE"][metric] - block_means["C1"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
            "residual_advantage_ratio": block_ratio,
            "classification": block_class,
        }

    total_cases = len(BLOCK_SEED_BASES) * CASES_PER_BLOCK
    aggregate_means = {
        model: {metric: value / total_cases for metric, value in sums.items()}
        for model, sums in aggregate_sums.items()
    }
    baseline_n1_minus_c1 = aggregate_means["N1"]["total"] - aggregate_means["C1"]["total"]
    if abs(baseline_n1_minus_c1 - EXPECTED_PRIOR_N1_MINUS_C1) > TOL:
        raise AssertionError(
            f"prior_W1_baseline_not_reproduced:{baseline_n1_minus_c1}:{EXPECTED_PRIOR_N1_MINUS_C1}"
        )

    n1_minus_oracle = aggregate_means["N1"]["total"] - aggregate_means["C1_ORACLE"]["total"]
    primary_classification, residual_ratio = _classification(n1_minus_oracle, baseline_n1_minus_c1)

    block_oracle_beats_or_ties_n1 = sum(
        1 for row in block_results.values()
        if float(row["N1_minus_C1_ORACLE"]["total"]) >= 0.0
    )
    block_majority_erased = sum(
        1 for row in block_results.values()
        if float(row["N1_minus_C1_ORACLE"]["total"]) >= 0.0
        or float(row["residual_advantage_ratio"]) <= 0.25
    )

    result = {
        "record": "KEIRIN_Q_ORACLE_SHARED_STATE_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "primary_hypothesis_classification": primary_classification,
        "hypothesis_under_test": "LATENT_SHARED_PROXY_DOMINANT",
        "world": WORLD,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "oracle_control": {
            "id": "C1_ORACLE",
            "formal_model_candidate": False,
            "base": "frozen_C1",
            "exact_added_component": "0.16_times_true_line_average_latent_skill",
            "oracle_coefficient_fitted": False,
            "normal_PRE_mutated": False,
            "normal_C1_or_N1_code_mutated": False,
        },
        "aggregate_model_chain_cross_entropy": aggregate_means,
        "aggregate_deltas": {
            "N1_minus_C1": {
                metric: aggregate_means["N1"][metric] - aggregate_means["C1"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
            "N1_minus_C1_ORACLE": {
                metric: aggregate_means["N1"][metric] - aggregate_means["C1_ORACLE"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
            "C1_ORACLE_minus_C1": {
                metric: aggregate_means["C1_ORACLE"][metric] - aggregate_means["C1"][metric]
                for metric in ("rank1", "rank2", "rank3", "total")
            },
        },
        "residual_advantage_ratio": residual_ratio,
        "block_results": block_results,
        "block_oracle_beats_or_ties_n1_count": block_oracle_beats_or_ties_n1,
        "block_majority_erased_count": block_majority_erased,
        "mechanical_checks": {
            "max_oracle_component_vs_canonical_W1_shared_component_diff": max_oracle_component_diff,
            "max_nonoracle_C1_reproduction_diff": max_nonoracle_C1_reproduction_diff,
            "max_nonoracle_N1_reproduction_diff": max_nonoracle_N1_reproduction_diff,
            "max_prediction_probability_mass_error": max_prediction_mass_error,
            "max_truth_probability_mass_error": max_truth_mass_error,
            "max_chain_decomposition_residual": max_decomposition_residual,
            "prior_W1_N1_minus_C1_reproduction_error": abs(baseline_n1_minus_c1 - EXPECTED_PRIOR_N1_MINUS_C1),
            "oracle_nonoracle_source_boundary_check": True,
            "PRE_latent_skill_absent": True,
        },
        "new_seed_selection": False,
        "result_adaptive_condition_selection": False,
        "post_result_retuning": False,
        "models_or_frozen_coefficients_changed": False,
        "authorization_auto_expanded": False,
        "protected_or_quarantined_input_access": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "econ_holdout1000_access": False,
        "dev2000_c_rescue": False,
        "same_lineage_b_c_rescue_tuning": False,
        "real_or_untouched_validation": False,
        "real_live_input_collection": False,
        "economics_bankroll_roi": False,
        "model_promotion_or_freeze": False,
        "external_provider_contact": False,
        "core_phase_c_main_ruleset_runtime_production_authority_change": False,
        "real_world_edge_or_roi_evidence": False,
        "scientific_segment_c_scoring_count": 0,
        "scientific_decision": "ORACLE_DIAGNOSTIC_ONLY_RECORD_DIRECTION_REGARDLESS_NO_RETUNING_NO_PROMOTION_NO_AUTO_SCOPE_EXPANSION",
    }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    print("KEIRIN_Q_ORACLE_SHARED_STATE_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
