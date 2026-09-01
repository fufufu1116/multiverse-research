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
KERNELS = (
    "MATCHED_W2_REFERENCE",
    "REVERSE_DIRECTION",
    "SPARSE_HEAD_TAIL",
    "SIGN_INVERTED_COUNTEREXAMPLE",
)
PRIMARY_MISMATCH_KERNELS = ("REVERSE_DIRECTION", "SPARSE_HEAD_TAIL")
TOL_MASS = 1e-10
TOL_REFERENCE = 1e-12

EXPECTED_MATCHED_W2_N1_MINUS_C1 = {
    20261001: -0.009806604332961655,
    20262001: -0.011536745806851378,
    20263001: -0.010152770610321937,
    20264001: -0.010535808655032675,
}


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


def _custom_w2_truth(race, kernel: str):
    util = dt._static_utilities(race, use_line=True)
    cars = [r.car_no for r in race.riders]
    riders = {r.car_no: r for r in race.riders}
    p1 = dt._softmax(util)
    joint = {}

    for first in cars:
        rf = riders[first]
        rem2 = [c for c in cars if c != first]
        u2 = {}
        for candidate in rem2:
            rc = riders[candidate]
            same = float(rc.line_id == rf.line_id)

            if kernel == "REVERSE_DIRECTION":
                predecessor = float(
                    same and int(rc.line_position) + 1 == int(rf.line_position)
                )
                bonus = 0.30 * same + 0.28 * predecessor
            elif kernel == "SPARSE_HEAD_TAIL":
                head_to_tail = float(
                    same
                    and int(rf.line_position) == 0
                    and int(rf.line_size) >= 3
                    and int(rc.line_position) == int(rf.line_size) - 1
                )
                bonus = 0.58 * head_to_tail
            elif kernel == "SIGN_INVERTED_COUNTEREXAMPLE":
                follower = float(
                    same and int(rc.line_position) == int(rf.line_position) + 1
                )
                bonus = -0.30 * same - 0.28 * follower
            else:
                raise ValueError(f"unsupported_custom_kernel:{kernel}")
            u2[candidate] = util[candidate] + bonus

        p2 = dt._softmax(u2)

        for second in rem2:
            rs = riders[second]
            rem3 = [c for c in rem2 if c != second]
            u3 = {}
            for candidate in rem3:
                rc = riders[candidate]
                same_f = float(rc.line_id == rf.line_id)
                same_s = float(rc.line_id == rs.line_id)

                if kernel == "REVERSE_DIRECTION":
                    reverse_chain = float(
                        rf.line_id == rs.line_id == rc.line_id
                        and int(rf.line_position) > int(rs.line_position) > int(rc.line_position)
                    )
                    bonus = 0.17 * same_f + 0.14 * same_s + 0.30 * reverse_chain
                elif kernel == "SPARSE_HEAD_TAIL":
                    head_tail_middle = float(
                        rf.line_id == rs.line_id == rc.line_id
                        and int(rf.line_size) == 3
                        and int(rf.line_position) == 0
                        and int(rs.line_position) == 2
                        and int(rc.line_position) == 1
                    )
                    bonus = 0.61 * head_tail_middle
                elif kernel == "SIGN_INVERTED_COUNTEREXAMPLE":
                    chain = float(
                        rf.line_id == rs.line_id == rc.line_id
                        and int(rf.line_position) < int(rs.line_position) < int(rc.line_position)
                    )
                    bonus = -0.17 * same_f - 0.14 * same_s - 0.30 * chain
                else:
                    raise ValueError(f"unsupported_custom_kernel:{kernel}")
                u3[candidate] = util[candidate] + bonus

            p3 = dt._softmax(u3)
            for third in rem3:
                joint[(first, second, third)] = p1[first] * p2[second] * p3[third]

    _assert_probability_object(joint)
    return joint


def _truth(race, kernel: str):
    if kernel == "MATCHED_W2_REFERENCE":
        return dt.world_joint_distribution(race, "W2")
    return _custom_w2_truth(race, kernel)


def _stable_advantage(block_deltas: list[float], aggregate_delta: float) -> bool:
    return aggregate_delta < 0.0 and sum(d < 0.0 for d in block_deltas) >= 3


def main() -> None:
    frozen = base._load_frozen_params()
    totals = {
        block: {
            kernel: {model: 0.0 for model in MODELS}
            for kernel in KERNELS
        }
        for block in BLOCK_SEED_BASES
    }
    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0
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
            if rank1_diff > 1e-12:
                raise AssertionError(
                    f"C1_N1_shared_P1_invariant_failed:{block}:{case}:{rank1_diff}"
                )

            for kernel in KERNELS:
                truth = _truth(race, kernel)
                support = set(truth)
                max_truth_mass_error = max(
                    max_truth_mass_error,
                    _assert_probability_object(truth),
                )
                for model in MODELS:
                    max_prediction_mass_error = max(
                        max_prediction_mass_error,
                        _assert_probability_object(pred[model], support),
                    )
                    totals[block][kernel][model] += base._expected_log_loss(truth, pred[model])
            total_cases += 1

    block_results = {}
    aggregate = {
        kernel: {model: 0.0 for model in MODELS}
        for kernel in KERNELS
    }

    for block in BLOCK_SEED_BASES:
        block_results[str(block)] = {}
        for kernel in KERNELS:
            means = {
                model: totals[block][kernel][model] / CASES_PER_BLOCK
                for model in MODELS
            }
            for model in MODELS:
                aggregate[kernel][model] += means[model] / len(BLOCK_SEED_BASES)
            block_results[str(block)][kernel] = {
                "mean_expected_log_loss": means,
                "N1_minus_C1": means["N1"] - means["C1"],
                "N1_minus_C0": means["N1"] - means["C0"],
                "C1_minus_C0": means["C1"] - means["C0"],
            }

    max_reference_delta_error = 0.0
    for block, expected in EXPECTED_MATCHED_W2_N1_MINUS_C1.items():
        observed = block_results[str(block)]["MATCHED_W2_REFERENCE"]["N1_minus_C1"]
        err = abs(observed - expected)
        max_reference_delta_error = max(max_reference_delta_error, err)
        if err > TOL_REFERENCE:
            raise AssertionError(
                f"matched_W2_reference_drift:{block}:{observed}:{expected}:{err}"
            )

    aggregate_results = {}
    stability = {}
    for kernel in KERNELS:
        means = aggregate[kernel]
        delta = means["N1"] - means["C1"]
        block_deltas = [
            block_results[str(block)][kernel]["N1_minus_C1"]
            for block in BLOCK_SEED_BASES
        ]
        aggregate_results[kernel] = {
            "mean_expected_log_loss": means,
            "N1_minus_C1": delta,
            "N1_minus_C0": means["N1"] - means["C0"],
            "C1_minus_C0": means["C1"] - means["C0"],
            "negative_N1_better_block_count": sum(d < 0.0 for d in block_deltas),
            "positive_N1_worse_block_count": sum(d > 0.0 for d in block_deltas),
        }
        stability[kernel] = _stable_advantage(block_deltas, delta)

    if not stability["MATCHED_W2_REFERENCE"]:
        classification = "NO_STABLE_RELATIONAL_ADVANTAGE"
    elif all(stability[k] for k in PRIMARY_MISMATCH_KERNELS):
        classification = "GENERIC_RELATIONAL_VALUE"
    else:
        classification = "MATCHED_SIMULATOR_AFFINITY"

    result = {
        "record": "KEIRIN_Q_MISMATCH_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "primary_hypothesis_classification": classification,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "new_seed_selection": False,
        "untouched_validation_claim": False,
        "models_changed": False,
        "coefficients_changed": False,
        "post_result_retuning": False,
        "post_hoc_kernel_addition": False,
        "block_results": block_results,
        "aggregate_results": aggregate_results,
        "stable_N1_advantage_by_kernel": stability,
        "primary_mismatch_kernels": list(PRIMARY_MISMATCH_KERNELS),
        "sign_inverted_counterexample_enters_primary_classification": False,
        "max_matched_W2_reference_delta_error": max_reference_delta_error,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_truth_probability_mass_error": max_truth_mass_error,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "scientific_decision": "DIAGNOSTIC_CLASSIFICATION_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
        "protected_or_quarantined_input_access": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "econ_holdout1000_access": False,
        "dev2000_c_rescue": False,
        "scientific_segment_c_scoring_count": 0,
        "real_live_input_collection": False,
        "economics": False,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_Q_MISMATCH_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
