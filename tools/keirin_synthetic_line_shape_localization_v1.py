#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base

BLOCK_SEED_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128
WORLDS = ("W0", "W1", "W2", "W3", "W4")
MODELS = ("C0", "C1", "N1")


def _line_shape(pre: Mapping[str, object]) -> str:
    sizes: dict[int, int] = {}
    for rider in pre["riders"]:
        gid = int(rider["line_group_id"])
        size = int(rider["line_size"])
        if gid in sizes and sizes[gid] != size:
            raise AssertionError(f"inconsistent_line_size:{gid}")
        sizes[gid] = size
    if len(sizes) != int(pre["num_lines"]):
        raise AssertionError("num_lines_mismatch")
    if sum(sizes.values()) != int(pre["field_size"]):
        raise AssertionError("line_shape_field_size_mismatch")
    return "-".join(str(x) for x in sorted(sizes.values(), reverse=True))


def _predict(pre: Mapping[str, object], frozen: Mapping[str, object]) -> dict:
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    return {
        "C0": base._c0(pre),
        "C1": base._c1(pre, c1_params, c1_shrinkage),
        "N1": base._n1(pre, c1_params, n1_params, n1_shrinkage),
    }


def main() -> None:
    frozen = base._load_frozen_params()
    totals: dict[str, dict[str, dict[str, float]]] = {}
    shape_counts: dict[str, int] = {}
    max_prediction_mass_error = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0
    total_cases = 0

    for block_seed in BLOCK_SEED_BASES:
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = base.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{seed}:{case}")
            pre = base.pre_view(race)
            shape = _line_shape(pre)
            shape_counts[shape] = shape_counts.get(shape, 0) + 1
            if shape not in totals:
                totals[shape] = {
                    world: {
                        model: 0.0 for model in MODELS
                    }
                    for world in WORLDS
                }

            predictions = _predict(pre, frozen)
            c1_rank1 = base._rank1_marginal(predictions["C1"])
            n1_rank1 = base._rank1_marginal(predictions["N1"])
            rank1_diff = max(abs(c1_rank1[car] - n1_rank1[car]) for car in c1_rank1)
            max_c1_n1_rank1_marginal_difference = max(
                max_c1_n1_rank1_marginal_difference, rank1_diff
            )
            if rank1_diff > 1e-12:
                raise AssertionError(f"C1_N1_shared_P1_invariant_failed:{seed}:{case}:{rank1_diff}")

            for world in WORLDS:
                truth = base.world_joint_distribution(race, world)
                support = set(truth)
                if abs(sum(float(q) for q in truth.values()) - 1.0) > 1e-10:
                    raise AssertionError(f"truth_mass_mismatch:{seed}:{case}:{world}")
                for model, pred in predictions.items():
                    max_prediction_mass_error = max(
                        max_prediction_mass_error,
                        base._assert_probability_object(
                            f"{seed}:{case}:{shape}:{world}:{model}", pred, support
                        ),
                    )
                    totals[shape][world][model] += base._expected_log_loss(truth, pred)
            total_cases += 1

    if sum(shape_counts.values()) != total_cases:
        raise AssertionError("shape_count_total_mismatch")

    shape_results = {}
    n1_minus_c1_sign_counts = {
        "negative_n1_better": 0,
        "positive_n1_worse": 0,
        "zero": 0,
    }
    for shape in sorted(shape_counts):
        n = shape_counts[shape]
        world_results = {}
        overall = {
            model: 0.0 for model in MODELS
        }
        for world in WORLDS:
            rows = {
                model: totals[shape][world][model] / n
                for model in MODELS
            }
            for model in MODELS:
                overall[model] += rows[model] / len(WORLDS)
            delta = rows["N1"] - rows["C1"]
            if delta < 0.0:
                n1_minus_c1_sign_counts["negative_n1_better"] += 1
            elif delta > 0.0:
                n1_minus_c1_sign_counts["positive_n1_worse"] += 1
            else:
                n1_minus_c1_sign_counts["zero"] += 1
            world_results[world] = {
                "expected_log_loss": rows,
                "deltas_lower_is_better": {
                    "C1_minus_C0": rows["C1"] - rows["C0"],
                    "N1_minus_C1": delta,
                    "N1_minus_C0": rows["N1"] - rows["C0"],
                },
            }
        shape_results[shape] = {
            "race_count": n,
            "synthetic_sample_share": n / total_cases,
            "world_results": world_results,
            "overall_equal_world_weight_expected_log_loss": overall,
        }

    n1_minus_c1_sign_counts["total_cells"] = sum(n1_minus_c1_sign_counts.values())
    result = {
        "record": "KEIRIN_SYNTHETIC_LINE_SHAPE_LOCALIZATION_v1",
        "status": "PASS",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "new_seed_selection": False,
        "worlds": list(WORLDS),
        "world_evaluations": total_cases * len(WORLDS),
        "model_world_evaluations": total_cases * len(WORLDS) * len(MODELS),
        "observed_line_shapes": sorted(shape_counts),
        "shape_race_counts": shape_counts,
        "shape_results": shape_results,
        "n1_minus_c1_shape_world_sign_counts": n1_minus_c1_sign_counts,
        "synthetic_shape_frequency_is_real_frequency_claim": False,
        "max_prediction_probability_mass_error": max_prediction_mass_error,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "pass_does_not_require_any_topology_model_ranking": True,
        "scientific_decision": "FAILURE_LOCALIZATION_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
        "model_or_coefficient_change": False,
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
    print("KEIRIN_SYNTHETIC_LINE_SHAPE_LOCALIZATION_PASS")


if __name__ == "__main__":
    main()
