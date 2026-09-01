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
MODELS = ("C1", "N1")
CONDITIONS = (
    "W0_BASE_ONLY",
    "W1_OBSERVED_STRUCTURE_ONLY",
    "W1_LATENT_SHARED_ONLY",
    "W1_FULL",
)
TOL = 1e-12
TOL_MASS = 1e-10
EPS = 1e-300


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
        "C1": base._c1(pre, c1_params, c1_shrinkage),
        "N1": base._n1(pre, c1_params, n1_params, n1_shrinkage),
    }


def _assert_prob(obj) -> float:
    vals = [float(v) for v in obj.values()]
    if any((not math.isfinite(v)) or v < 0.0 for v in vals):
        raise AssertionError("invalid_probability")
    err = abs(sum(vals) - 1.0)
    if err > TOL_MASS:
        raise AssertionError(f"mass_mismatch:{err}")
    return err


def _max_abs_diff(a, b) -> float:
    if set(a) != set(b):
        raise AssertionError("distribution_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


def _truth(race, condition: str):
    line_strength = dt._line_strengths(race)
    util = {}
    for r in race.riders:
        value = dt._base_utility(r, race)
        pos_bonus = {0: 0.04, 1: 0.10, 2: 0.05}.get(r.line_position, 0.0)
        size_bonus = 0.025 * max(0, r.line_size - 1)
        latent_shared = 0.16 * line_strength[r.line_id]
        if condition == "W0_BASE_ONLY":
            pass
        elif condition == "W1_OBSERVED_STRUCTURE_ONLY":
            value += pos_bonus + size_bonus
        elif condition == "W1_LATENT_SHARED_ONLY":
            value += latent_shared
        elif condition == "W1_FULL":
            value += latent_shared + pos_bonus + size_bonus
        else:
            raise ValueError(condition)
        util[r.car_no] = value
    return dt._joint_from_utilities(race, util, relation_strength=0.0)


def _marginals(joint):
    p1 = {}
    p12 = {}
    for (i, j, _k), p in joint.items():
        p = float(p)
        p1[i] = p1.get(i, 0.0) + p
        p12[(i, j)] = p12.get((i, j), 0.0) + p
    return p1, p12


def _chain_cross_entropy(truth, pred):
    q1, q12 = _marginals(pred)
    rank1 = rank2 = rank3 = 0.0
    for (i, j, k), p in truth.items():
        p = float(p)
        q1_i = max(EPS, float(q1[i]))
        q12_ij = max(EPS, float(q12[(i, j)]))
        qijk = max(EPS, float(pred[(i, j, k)]))
        rank1 -= p * math.log(q1_i)
        rank2 -= p * math.log(max(EPS, q12_ij / q1_i))
        rank3 -= p * math.log(max(EPS, qijk / q12_ij))
    total = rank1 + rank2 + rank3
    direct = base._expected_log_loss(truth, pred)
    residual = abs(total - direct)
    if residual > TOL:
        raise AssertionError(f"chain_residual:{residual}")
    return {"rank1": rank1, "rank2": rank2, "rank3": rank3, "total": total, "residual": residual}


def _stable(block_deltas, aggregate_delta):
    return aggregate_delta < 0.0 and sum(d < 0.0 for d in block_deltas) >= 3


def _classify(stability):
    full = stability["W1_FULL"]
    obs = stability["W1_OBSERVED_STRUCTURE_ONLY"]
    latent = stability["W1_LATENT_SHARED_ONLY"]
    if not full:
        return "NO_STABLE_W1_GAIN"
    if latent and not obs:
        return "LATENT_SHARED_PROXY_DOMINANT"
    if obs and not latent:
        return "OBSERVED_STRUCTURE_PROXY_DOMINANT"
    if obs and latent:
        return "BOTH_COMPONENTS_INDEPENDENTLY_SUPPORT_GAIN"
    if not obs and not latent:
        return "INTERACTION_ONLY_W1_GAIN"
    return "MIXED_OR_NONMONOTONIC_COMPONENT_PATTERN"


def main() -> None:
    frozen = base._load_frozen_params()
    totals = {
        block: {
            condition: {
                model: {"rank1": 0.0, "rank2": 0.0, "rank3": 0.0, "total": 0.0}
                for model in MODELS
            }
            for condition in CONDITIONS
        }
        for block in BLOCK_SEED_BASES
    }
    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_decomposition_residual = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0
    max_w0_endpoint_diff = 0.0
    max_w1_endpoint_diff = 0.0
    total_cases = 0

    for block in BLOCK_SEED_BASES:
        for case in range(CASES_PER_BLOCK):
            race = base.generate_race(seed=block + case, race_index=case % 32)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block}:{case}")
            pre = base.pre_view(race)
            if any("latent_skill" in rider for rider in pre["riders"]):
                raise AssertionError(f"latent_skill_leak:{block}:{case}")
            pred = _predict(pre, frozen)
            for model in MODELS:
                max_prediction_mass_error = max(max_prediction_mass_error, _assert_prob(pred[model]))
            c1_rank1 = base._rank1_marginal(pred["C1"])
            n1_rank1 = base._rank1_marginal(pred["N1"])
            rank1_diff = max(abs(float(c1_rank1[c]) - float(n1_rank1[c])) for c in c1_rank1)
            max_c1_n1_rank1_marginal_difference = max(max_c1_n1_rank1_marginal_difference, rank1_diff)
            if rank1_diff > TOL:
                raise AssertionError(f"rank1_prediction_mismatch:{block}:{case}:{rank1_diff}")

            canonical_w0 = dt.world_joint_distribution(race, "W0")
            canonical_w1 = dt.world_joint_distribution(race, "W1")
            for condition in CONDITIONS:
                truth = _truth(race, condition)
                max_truth_mass_error = max(max_truth_mass_error, _assert_prob(truth))
                if condition == "W0_BASE_ONLY":
                    max_w0_endpoint_diff = max(max_w0_endpoint_diff, _max_abs_diff(truth, canonical_w0))
                if condition == "W1_FULL":
                    max_w1_endpoint_diff = max(max_w1_endpoint_diff, _max_abs_diff(truth, canonical_w1))
                if set(truth) != set(pred["C1"]) or set(truth) != set(pred["N1"]):
                    raise AssertionError(f"support_mismatch:{block}:{case}:{condition}")
                for model in MODELS:
                    parts = _chain_cross_entropy(truth, pred[model])
                    max_decomposition_residual = max(max_decomposition_residual, parts["residual"])
                    for key in ("rank1", "rank2", "rank3", "total"):
                        totals[block][condition][model][key] += parts[key]
            total_cases += 1

    if max_w0_endpoint_diff > TOL:
        raise AssertionError(f"W0_endpoint_drift:{max_w0_endpoint_diff}")
    if max_w1_endpoint_diff > TOL:
        raise AssertionError(f"W1_endpoint_drift:{max_w1_endpoint_diff}")

    block_results = {}
    aggregate_results = {}
    stability = {}
    for block in BLOCK_SEED_BASES:
        block_results[str(block)] = {}
        for condition in CONDITIONS:
            rows = {
                model: {
                    key: totals[block][condition][model][key] / CASES_PER_BLOCK
                    for key in ("rank1", "rank2", "rank3", "total")
                }
                for model in MODELS
            }
            deltas = {key: rows["N1"][key] - rows["C1"][key] for key in ("rank1", "rank2", "rank3", "total")}
            if abs(deltas["rank1"]) > TOL:
                raise AssertionError(f"rank1_delta_nonzero:{block}:{condition}:{deltas['rank1']}")
            block_results[str(block)][condition] = {"N1_minus_C1": deltas}

    for condition in CONDITIONS:
        deltas = {}
        for key in ("rank1", "rank2", "rank3", "total"):
            deltas[key] = sum(block_results[str(block)][condition]["N1_minus_C1"][key] for block in BLOCK_SEED_BASES) / len(BLOCK_SEED_BASES)
        block_total_deltas = [block_results[str(block)][condition]["N1_minus_C1"]["total"] for block in BLOCK_SEED_BASES]
        stability[condition] = _stable(block_total_deltas, deltas["total"])
        aggregate_results[condition] = {
            "N1_minus_C1": deltas,
            "negative_N1_better_block_count": sum(d < 0.0 for d in block_total_deltas),
            "positive_N1_worse_block_count": sum(d > 0.0 for d in block_total_deltas),
            "stable_N1_advantage": stability[condition],
        }

    result = {
        "record": "KEIRIN_Q_W1_STATIC_ABLATION_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "primary_hypothesis_classification": _classify(stability),
        "conditions": list(CONDITIONS),
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "aggregate_results": aggregate_results,
        "block_results": block_results,
        "stable_N1_advantage_by_condition": stability,
        "new_seed_selection": False,
        "new_relation_kernel": False,
        "relation_strength_all_conditions": 0.0,
        "new_model_addition": False,
        "models_changed": False,
        "coefficients_changed": False,
        "post_result_retuning": False,
        "post_hoc_condition_addition": False,
        "max_W0_BASE_ONLY_vs_canonical_W0_truth_diff": max_w0_endpoint_diff,
        "max_W1_FULL_vs_canonical_W1_truth_diff": max_w1_endpoint_diff,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_truth_probability_mass_error": max_truth_mass_error,
        "max_decomposition_residual": max_decomposition_residual,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "scientific_decision": "STATIC_W1_COMPONENT_FAILURE_DIAGNOSTIC_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
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
    print("KEIRIN_Q_W1_STATIC_ABLATION_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
