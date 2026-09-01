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
WORLDS = ("W1", "W2")
MODELS = ("C1", "N1")
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


def _marginals(joint):
    p1 = {}
    p12 = {}
    for (i, j, k), p in joint.items():
        p = float(p)
        p1[i] = p1.get(i, 0.0) + p
        p12[(i, j)] = p12.get((i, j), 0.0) + p
    return p1, p12


def _chain_cross_entropy(truth, pred):
    q1, q12 = _marginals(pred)
    rank1 = 0.0
    rank2 = 0.0
    rank3 = 0.0
    for (i, j, k), p in truth.items():
        p = float(p)
        q1_i = max(EPS, float(q1[i]))
        q12_ij = max(EPS, float(q12[(i, j)]))
        qijk = max(EPS, float(pred[(i, j, k)]))
        q2 = max(EPS, q12_ij / q1_i)
        q3 = max(EPS, qijk / q12_ij)
        rank1 -= p * math.log(q1_i)
        rank2 -= p * math.log(q2)
        rank3 -= p * math.log(q3)
    total = rank1 + rank2 + rank3
    direct = base._expected_log_loss(truth, pred)
    residual = abs(total - direct)
    if residual > TOL:
        raise AssertionError(f"chain_decomposition_residual:{residual}")
    return {
        "rank1": rank1,
        "rank2": rank2,
        "rank3": rank3,
        "total": total,
        "direct_joint": direct,
        "residual": residual,
    }


def _classify(prefix: str, total_delta: float, rank2_delta: float, rank3_delta: float) -> str:
    if total_delta >= 0.0:
        return f"{prefix}_NO_N1_GAIN"
    r2neg = rank2_delta < 0.0
    r3neg = rank3_delta < 0.0
    r2nonneg = rank2_delta >= 0.0
    r3nonneg = rank3_delta >= 0.0
    if r2neg and r3nonneg:
        return f"{prefix}_GAIN_RANK2_ONLY"
    if r3neg and r2nonneg:
        return f"{prefix}_GAIN_RANK3_ONLY"
    if r2neg and r3neg:
        return f"{prefix}_GAIN_BOTH_RANK2_AND_RANK3"
    return f"{prefix}_GAIN_WITH_OFFSETTING_MIX"


def main() -> None:
    frozen = base._load_frozen_params()
    totals = {
        block: {
            world: {
                model: {"rank1": 0.0, "rank2": 0.0, "rank3": 0.0, "total": 0.0}
                for model in MODELS
            }
            for world in WORLDS
        }
        for block in BLOCK_SEED_BASES
    }

    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_decomposition_residual = 0.0
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
            for model in MODELS:
                max_prediction_mass_error = max(max_prediction_mass_error, _assert_prob(pred[model]))
            c1_rank1 = base._rank1_marginal(pred["C1"])
            n1_rank1 = base._rank1_marginal(pred["N1"])
            rank1_diff = max(abs(float(c1_rank1[c]) - float(n1_rank1[c])) for c in c1_rank1)
            max_c1_n1_rank1_marginal_difference = max(max_c1_n1_rank1_marginal_difference, rank1_diff)
            if rank1_diff > TOL:
                raise AssertionError(f"C1_N1_shared_P1_invariant_failed:{block}:{case}:{rank1_diff}")

            for world in WORLDS:
                truth = dt.world_joint_distribution(race, world)
                max_truth_mass_error = max(max_truth_mass_error, _assert_prob(truth))
                if set(truth) != set(pred["C1"]) or set(truth) != set(pred["N1"]):
                    raise AssertionError(f"support_mismatch:{block}:{case}:{world}")
                for model in MODELS:
                    parts = _chain_cross_entropy(truth, pred[model])
                    max_decomposition_residual = max(max_decomposition_residual, parts["residual"])
                    for key in ("rank1", "rank2", "rank3", "total"):
                        totals[block][world][model][key] += parts[key]
            total_cases += 1

    block_results = {}
    aggregate = {
        world: {
            model: {"rank1": 0.0, "rank2": 0.0, "rank3": 0.0, "total": 0.0}
            for model in MODELS
        }
        for world in WORLDS
    }

    for block in BLOCK_SEED_BASES:
        block_results[str(block)] = {}
        for world in WORLDS:
            rows = {
                model: {
                    key: totals[block][world][model][key] / CASES_PER_BLOCK
                    for key in ("rank1", "rank2", "rank3", "total")
                }
                for model in MODELS
            }
            for model in MODELS:
                for key in ("rank1", "rank2", "rank3", "total"):
                    aggregate[world][model][key] += rows[model][key] / len(BLOCK_SEED_BASES)
            deltas = {
                key: rows["N1"][key] - rows["C1"][key]
                for key in ("rank1", "rank2", "rank3", "total")
            }
            if abs(deltas["rank1"]) > TOL:
                raise AssertionError(f"rank1_delta_nonzero:{block}:{world}:{deltas['rank1']}")
            block_results[str(block)][world] = {
                "model_chain_cross_entropy": rows,
                "N1_minus_C1": deltas,
            }

    aggregate_results = {}
    classifications = {}
    for world in WORLDS:
        deltas = {
            key: aggregate[world]["N1"][key] - aggregate[world]["C1"][key]
            for key in ("rank1", "rank2", "rank3", "total")
        }
        if abs(deltas["rank1"]) > TOL:
            raise AssertionError(f"aggregate_rank1_delta_nonzero:{world}:{deltas['rank1']}")
        if abs((deltas["rank1"] + deltas["rank2"] + deltas["rank3"]) - deltas["total"]) > TOL:
            raise AssertionError(f"aggregate_delta_sum_mismatch:{world}")
        classifications[world] = _classify(world, deltas["total"], deltas["rank2"], deltas["rank3"])
        aggregate_results[world] = {
            "model_chain_cross_entropy": aggregate[world],
            "N1_minus_C1": deltas,
            "signed_source_classification": classifications[world],
        }

    result = {
        "record": "KEIRIN_Q_CHAIN_DECOMP_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "worlds": list(WORLDS),
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "aggregate_results": aggregate_results,
        "block_results": block_results,
        "W1_signed_source_classification": classifications["W1"],
        "W2_signed_source_classification": classifications["W2"],
        "new_seed_selection": False,
        "new_kernel_addition": False,
        "new_world_addition": False,
        "models_changed": False,
        "coefficients_changed": False,
        "post_result_retuning": False,
        "post_hoc_subgroup_slicing": False,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_truth_probability_mass_error": max_truth_mass_error,
        "max_decomposition_residual": max_decomposition_residual,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "scientific_decision": "EXACT_CHAIN_RULE_DIAGNOSTIC_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
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
    print("KEIRIN_Q_CHAIN_DECOMP_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
