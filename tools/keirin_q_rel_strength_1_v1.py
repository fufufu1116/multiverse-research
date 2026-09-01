#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
NEW_LINEAGE = ROOT / "v3" / "historical_all_market" / "new_lineage"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(NEW_LINEAGE))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base
import digital_twin_v1 as dt

BLOCK_SEED_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128
MODELS = ("C0", "C1", "N1")
RELATION_STRENGTH_GRID = (0.0, 0.125, 0.25, 0.5, 0.75, 1.0)
TOL_MASS = 1e-10
TOL_EQ = 1e-12


def _predict(pre: Mapping[str, object], frozen: Mapping[str, object]) -> dict:
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"]:
        raise AssertionError("C1_N1_P1_parameter_basis_mismatch")
    if c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_P1_shrinkage_mismatch")
    return {
        "C0": base._c0(pre),
        "C1": base._c1(pre, c1_params, c1_shrinkage),
        "N1": base._n1(pre, c1_params, n1_params, n1_shrinkage),
    }


def _assert_probability_object(obj, support=None) -> float:
    if support is not None and set(obj) != support:
        raise AssertionError("probability_support_mismatch")
    vals = [float(v) for v in obj.values()]
    if any((not math.isfinite(v)) or v < 0.0 for v in vals):
        raise AssertionError("invalid_probability_value")
    mass_error = abs(sum(vals) - 1.0)
    if mass_error > TOL_MASS:
        raise AssertionError(f"probability_mass_mismatch:{mass_error}")
    return mass_error


def _max_abs_diff(a, b) -> float:
    if set(a) != set(b):
        raise AssertionError("distribution_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


def _stable(block_deltas: list[float], aggregate_delta: float) -> bool:
    return aggregate_delta < 0.0 and sum(d < 0.0 for d in block_deltas) >= 3


def _primary_classification(stability: dict[str, bool]) -> tuple[str, float | None, bool]:
    ordered = [str(x) for x in RELATION_STRENGTH_GRID]
    seq = [stability[key] for key in ordered]
    nonmonotonic = any(seq[i] and not seq[i + 1] for i in range(len(seq) - 1))

    if not stability[str(1.0)]:
        return "NO_STABLE_RELATIONAL_ADVANTAGE", None, nonmonotonic
    if stability[str(0.0)]:
        return "STATIC_OR_ZERO_CONDITIONAL_ADVANTAGE", 0.0, nonmonotonic

    interior = [x for x in RELATION_STRENGTH_GRID if 0.0 < x < 1.0 and stability[str(x)]]
    if interior:
        return "INTERIOR_RELATIONAL_ONSET", min(interior), nonmonotonic
    return "ONLY_FULL_W2_STABLE", 1.0, nonmonotonic


def main() -> None:
    frozen = base._load_frozen_params()
    totals = {
        block: {
            str(strength): {model: 0.0 for model in MODELS}
            for strength in RELATION_STRENGTH_GRID
        }
        for block in BLOCK_SEED_BASES
    }

    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0
    max_lambda0_vs_w1_truth_diff = 0.0
    max_lambda1_vs_w2_truth_diff = 0.0
    total_cases = 0

    for block in BLOCK_SEED_BASES:
        for case in range(CASES_PER_BLOCK):
            seed = block + case
            race_index = case % 32
            race = base.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block}:{case}")
            pre = base.pre_view(race)
            if any("latent_skill" in rider for rider in pre["riders"]):
                raise AssertionError(f"latent_skill_leak:{block}:{case}")

            pred = _predict(pre, frozen)
            c1_rank1 = base._rank1_marginal(pred["C1"])
            n1_rank1 = base._rank1_marginal(pred["N1"])
            rank1_diff = max(abs(float(c1_rank1[c]) - float(n1_rank1[c])) for c in c1_rank1)
            max_c1_n1_rank1_marginal_difference = max(
                max_c1_n1_rank1_marginal_difference, rank1_diff
            )
            if rank1_diff > TOL_EQ:
                raise AssertionError(
                    f"C1_N1_shared_P1_invariant_failed:{block}:{case}:{rank1_diff}"
                )

            stable_util = dt._static_utilities(race, use_line=True)
            endpoint_w1 = dt.world_joint_distribution(race, "W1")
            endpoint_w2 = dt.world_joint_distribution(race, "W2")

            for strength in RELATION_STRENGTH_GRID:
                key = str(strength)
                truth = dt._joint_from_utilities(
                    race, stable_util, relation_strength=float(strength)
                )
                support = set(truth)
                max_truth_mass_error = max(
                    max_truth_mass_error, _assert_probability_object(truth)
                )
                if strength == 0.0:
                    max_lambda0_vs_w1_truth_diff = max(
                        max_lambda0_vs_w1_truth_diff,
                        _max_abs_diff(truth, endpoint_w1),
                    )
                if strength == 1.0:
                    max_lambda1_vs_w2_truth_diff = max(
                        max_lambda1_vs_w2_truth_diff,
                        _max_abs_diff(truth, endpoint_w2),
                    )
                for model in MODELS:
                    max_prediction_mass_error = max(
                        max_prediction_mass_error,
                        _assert_probability_object(pred[model], support),
                    )
                    totals[block][key][model] += base._expected_log_loss(
                        truth, pred[model]
                    )
            total_cases += 1

    if max_lambda0_vs_w1_truth_diff > TOL_EQ:
        raise AssertionError(f"lambda0_not_exact_W1:{max_lambda0_vs_w1_truth_diff}")
    if max_lambda1_vs_w2_truth_diff > TOL_EQ:
        raise AssertionError(f"lambda1_not_exact_W2:{max_lambda1_vs_w2_truth_diff}")

    block_results = {}
    aggregate_results = {}
    stability = {}

    for block in BLOCK_SEED_BASES:
        block_results[str(block)] = {}
        for strength in RELATION_STRENGTH_GRID:
            key = str(strength)
            means = {
                model: totals[block][key][model] / CASES_PER_BLOCK
                for model in MODELS
            }
            block_results[str(block)][key] = {
                "mean_expected_log_loss": means,
                "N1_minus_C1": means["N1"] - means["C1"],
                "N1_minus_C0": means["N1"] - means["C0"],
                "C1_minus_C0": means["C1"] - means["C0"],
            }

    for strength in RELATION_STRENGTH_GRID:
        key = str(strength)
        means = {
            model: sum(
                block_results[str(block)][key]["mean_expected_log_loss"][model]
                for block in BLOCK_SEED_BASES
            ) / len(BLOCK_SEED_BASES)
            for model in MODELS
        }
        block_deltas = [
            block_results[str(block)][key]["N1_minus_C1"]
            for block in BLOCK_SEED_BASES
        ]
        delta = means["N1"] - means["C1"]
        stability[key] = _stable(block_deltas, delta)
        aggregate_results[key] = {
            "mean_expected_log_loss": means,
            "N1_minus_C1": delta,
            "N1_minus_C0": means["N1"] - means["C0"],
            "C1_minus_C0": means["C1"] - means["C0"],
            "negative_N1_better_block_count": sum(d < 0.0 for d in block_deltas),
            "positive_N1_worse_block_count": sum(d > 0.0 for d in block_deltas),
            "stable_N1_advantage": stability[key],
        }

    primary_classification, onset_grid_lambda, nonmonotonic = _primary_classification(stability)

    result = {
        "record": "KEIRIN_Q_REL_STRENGTH_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "primary_hypothesis_classification": primary_classification,
        "relation_strength_grid": list(RELATION_STRENGTH_GRID),
        "onset_grid_lambda": onset_grid_lambda,
        "nonmonotonic_stability_pattern": nonmonotonic,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "new_seed_selection": False,
        "new_kernel_addition": False,
        "models_changed": False,
        "coefficients_changed": False,
        "post_result_retuning": False,
        "post_hoc_grid_refinement": False,
        "block_results": block_results,
        "aggregate_results": aggregate_results,
        "stable_N1_advantage_by_relation_strength": stability,
        "max_lambda0_vs_W1_truth_diff": max_lambda0_vs_w1_truth_diff,
        "max_lambda1_vs_W2_truth_diff": max_lambda1_vs_w2_truth_diff,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_truth_probability_mass_error": max_truth_mass_error,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "scientific_decision": "DIAGNOSTIC_BOUNDARY_CLASSIFICATION_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
        "protected_or_quarantined_input_access": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "econ_holdout1000_access": False,
        "dev2000_c_rescue": False,
        "same_lineage_b_c_rescue_tuning": False,
        "scientific_segment_c_scoring_count": 0,
        "real_live_input_collection": False,
        "economics": False,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_Q_REL_STRENGTH_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
