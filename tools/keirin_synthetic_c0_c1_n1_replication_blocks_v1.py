#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import keirin_synthetic_c0_c1_n1_comparison_v1 as b3

BLOCK_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128


def _blank_totals():
    return {
        world: {
            model: {"expected_log_loss": 0.0, "kl_regret": 0.0, "joint_brier": 0.0}
            for model in b3.MODELS
        }
        for world in b3.WORLDS
    }


def _finalize_block(totals):
    world_results = {}
    overall = {
        model: {"expected_log_loss": 0.0, "kl_regret": 0.0, "joint_brier": 0.0}
        for model in b3.MODELS
    }
    for world in b3.WORLDS:
        rows = {}
        for model in b3.MODELS:
            rows[model] = {
                metric: total / CASES_PER_BLOCK
                for metric, total in totals[world][model].items()
            }
            for metric, value in rows[model].items():
                overall[model][metric] += value / len(b3.WORLDS)
        world_results[world] = {
            "models": rows,
            "deltas_lower_is_better": {
                "C1_minus_C0_log_loss": rows["C1"]["expected_log_loss"] - rows["C0"]["expected_log_loss"],
                "N1_minus_C1_log_loss": rows["N1"]["expected_log_loss"] - rows["C1"]["expected_log_loss"],
                "N1_minus_C0_log_loss": rows["N1"]["expected_log_loss"] - rows["C0"]["expected_log_loss"],
            },
        }
    return world_results, overall


def main() -> None:
    frozen = b3._load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"] or c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_shared_P1_basis_drift")

    blocks = []
    max_prediction_mass_error = 0.0
    max_rank1_difference = 0.0
    negative_n1_c1_cells = 0
    positive_n1_c1_cells = 0
    zero_n1_c1_cells = 0

    for block_index, base_seed in enumerate(BLOCK_BASES):
        totals = _blank_totals()
        for case in range(CASES_PER_BLOCK):
            seed = base_seed + case
            race = b3.generate_race(seed=seed, race_index=case % 32)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block_index}:{case}")
            pre = b3.pre_view(race)
            if any("latent_skill" in rider for rider in pre["riders"]):
                raise AssertionError(f"latent_skill_leak:{block_index}:{case}")

            predictions = {
                "C0": b3._c0(pre),
                "C1": b3._c1(pre, c1_params, c1_shrinkage),
                "N1": b3._n1(pre, c1_params, n1_params, n1_shrinkage),
            }
            c1_rank1 = b3._rank1_marginal(predictions["C1"])
            n1_rank1 = b3._rank1_marginal(predictions["N1"])
            if set(c1_rank1) != set(n1_rank1):
                raise AssertionError("rank1_support_mismatch")
            rank1_diff = max(abs(c1_rank1[car] - n1_rank1[car]) for car in c1_rank1)
            max_rank1_difference = max(max_rank1_difference, rank1_diff)
            if rank1_diff > 1e-12:
                raise AssertionError(f"shared_P1_failed:{block_index}:{case}:{rank1_diff}")

            for world in b3.WORLDS:
                truth = b3.world_joint_distribution(race, world)
                support = set(truth)
                entropy = b3._truth_entropy(truth)
                for model, pred in predictions.items():
                    max_prediction_mass_error = max(
                        max_prediction_mass_error,
                        b3._assert_probability_object(
                            f"{block_index}:{case}:{world}:{model}", pred, support
                        ),
                    )
                    ll = b3._expected_log_loss(truth, pred)
                    totals[world][model]["expected_log_loss"] += ll
                    totals[world][model]["kl_regret"] += ll - entropy
                    totals[world][model]["joint_brier"] += b3._joint_brier(truth, pred)

        world_results, overall = _finalize_block(totals)
        for world in b3.WORLDS:
            delta = world_results[world]["deltas_lower_is_better"]["N1_minus_C1_log_loss"]
            if delta < 0.0:
                negative_n1_c1_cells += 1
            elif delta > 0.0:
                positive_n1_c1_cells += 1
            else:
                zero_n1_c1_cells += 1
        blocks.append(
            {
                "block_index": block_index,
                "base_seed": base_seed,
                "cases": CASES_PER_BLOCK,
                "world_results": world_results,
                "overall_equal_world_weight_models": overall,
            }
        )

    result = {
        "record": "KEIRIN_SYNTHETIC_C0_C1_N1_REPLICATION_BLOCKS_v1",
        "status": "PASS",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "post_batch3_robustness_not_holdout": True,
        "block_seed_bases": list(BLOCK_BASES),
        "blocks": blocks,
        "block_count": len(BLOCK_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": len(BLOCK_BASES) * CASES_PER_BLOCK,
        "worlds": list(b3.WORLDS),
        "world_evaluations": len(BLOCK_BASES) * CASES_PER_BLOCK * len(b3.WORLDS),
        "model_world_evaluations": len(BLOCK_BASES) * CASES_PER_BLOCK * len(b3.WORLDS) * len(b3.MODELS),
        "n1_minus_c1_world_block_sign_counts": {
            "negative_better": negative_n1_c1_cells,
            "positive_worse": positive_n1_c1_cells,
            "zero": zero_n1_c1_cells,
            "total_cells": len(BLOCK_BASES) * len(b3.WORLDS),
        },
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_C1_N1_rank1_marginal_difference": max_rank1_difference,
        "pass_does_not_require_any_model_ranking": True,
        "model_or_coefficient_change": False,
        "locked_legacy_synthetic_holdout_used": False,
        "fresh_synthetic_holdout_used": False,
        "real_live_input_collection": False,
        "economics": False,
        "real_world_validation": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "holdout_access": False,
        "scientific_segment_c_scoring_count": 0,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False,
        "scientific_decision": "POST_HOC_ROBUSTNESS_DIAGNOSTIC_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_SYNTHETIC_C0_C1_N1_REPLICATION_BLOCKS_PASS")


if __name__ == "__main__":
    main()
