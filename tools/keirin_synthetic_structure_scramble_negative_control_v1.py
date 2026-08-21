#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from copy import deepcopy
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
STRUCTURE_FIELDS = (
    "line_group_id",
    "line_position",
    "line_size",
    "is_singleton",
)


def _slot(row: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(row[key] for key in STRUCTURE_FIELDS)


def _scramble_structure(pre: Mapping[str, object]) -> dict:
    original = deepcopy(pre)
    out = deepcopy(pre)
    original_rows = sorted(original["riders"], key=lambda r: int(r["car_no"]))
    out_rows = sorted(out["riders"], key=lambda r: int(r["car_no"]))
    original_slots = [_slot(row) for row in original_rows]
    rotated_slots = original_slots[1:] + original_slots[:1]

    for row, slot in zip(out_rows, rotated_slots):
        for key, value in zip(STRUCTURE_FIELDS, slot):
            row[key] = value

    if Counter(original_slots) != Counter(_slot(row) for row in out_rows):
        raise AssertionError("structure_slot_multiset_not_preserved")
    if int(original["num_lines"]) != int(out["num_lines"]):
        raise AssertionError("num_lines_changed")

    for before, after in zip(original_rows, out_rows):
        if _slot(before) == _slot(after):
            raise AssertionError(f"rider_structure_slot_not_changed:{before['car_no']}")
        for key, value in before.items():
            if key in STRUCTURE_FIELDS:
                continue
            if after[key] != value:
                raise AssertionError(f"individual_PRE_field_changed:{before['car_no']}:{key}")
    return out


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


def _max_abs_probability_diff(a: Mapping[object, float], b: Mapping[object, float]) -> float:
    if set(a) != set(b):
        raise AssertionError("prediction_support_changed")
    return max(abs(float(a[key]) - float(b[key])) for key in a)


def _rank1_shared_check(pred: Mapping[str, Mapping[object, float]]) -> float:
    c1 = base._rank1_marginal(pred["C1"])
    n1 = base._rank1_marginal(pred["N1"])
    if set(c1) != set(n1):
        raise AssertionError("C1_N1_rank1_support_mismatch")
    diff = max(abs(float(c1[car]) - float(n1[car])) for car in c1)
    if diff > 1e-12:
        raise AssertionError(f"C1_N1_shared_P1_invariant_failed:{diff}")
    return diff


def main() -> None:
    frozen = base._load_frozen_params()
    totals = {
        block_seed: {
            world: {
                condition: {
                    model: 0.0 for model in MODELS
                }
                for condition in ("intact", "scrambled")
            }
            for world in WORLDS
        }
        for block_seed in BLOCK_SEED_BASES
    }

    max_c0_scramble_probability_difference = 0.0
    max_c1_n1_rank1_marginal_difference = 0.0
    max_prediction_probability_mass_error = 0.0
    total_cases = 0

    for block_seed in BLOCK_SEED_BASES:
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = base.generate_race(seed=seed, race_index=race_index)
            intact_pre = base.pre_view(race)
            scrambled_pre = _scramble_structure(intact_pre)

            intact_pred = _predict(intact_pre, frozen)
            scrambled_pred = _predict(scrambled_pre, frozen)

            c0_diff = _max_abs_probability_diff(intact_pred["C0"], scrambled_pred["C0"])
            max_c0_scramble_probability_difference = max(
                max_c0_scramble_probability_difference, c0_diff
            )
            if c0_diff != 0.0:
                raise AssertionError(f"C0_changed_under_structure_scramble:{seed}:{case}:{c0_diff}")

            max_c1_n1_rank1_marginal_difference = max(
                max_c1_n1_rank1_marginal_difference,
                _rank1_shared_check(intact_pred),
                _rank1_shared_check(scrambled_pred),
            )

            for world in WORLDS:
                truth = base.world_joint_distribution(race, world)
                support = set(truth)
                if abs(sum(float(q) for q in truth.values()) - 1.0) > 1e-10:
                    raise AssertionError(f"truth_mass_mismatch:{seed}:{case}:{world}")

                for condition, predictions in (
                    ("intact", intact_pred),
                    ("scrambled", scrambled_pred),
                ):
                    for model, pred in predictions.items():
                        max_prediction_probability_mass_error = max(
                            max_prediction_probability_mass_error,
                            base._assert_probability_object(
                                f"{seed}:{case}:{world}:{condition}:{model}", pred, support
                            ),
                        )
                        totals[block_seed][world][condition][model] += base._expected_log_loss(
                            truth, pred
                        )
            total_cases += 1

    blocks = []
    sign_counts = {
        model: {"positive_intact_better": 0, "negative_intact_worse": 0, "zero": 0}
        for model in ("C1", "N1")
    }
    overall_penalty_sum = {
        model: {world: 0.0 for world in WORLDS}
        for model in ("C1", "N1")
    }

    for block_seed in BLOCK_SEED_BASES:
        block_worlds = {}
        for world in WORLDS:
            model_rows = {}
            for model in MODELS:
                intact = totals[block_seed][world]["intact"][model] / CASES_PER_BLOCK
                scrambled = totals[block_seed][world]["scrambled"][model] / CASES_PER_BLOCK
                penalty = scrambled - intact
                model_rows[model] = {
                    "intact_expected_log_loss": intact,
                    "scrambled_expected_log_loss": scrambled,
                    "scrambled_minus_intact_log_loss": penalty,
                }
                if model in sign_counts:
                    overall_penalty_sum[model][world] += penalty
                    if penalty > 0.0:
                        sign_counts[model]["positive_intact_better"] += 1
                    elif penalty < 0.0:
                        sign_counts[model]["negative_intact_worse"] += 1
                    else:
                        sign_counts[model]["zero"] += 1
            block_worlds[world] = {"models": model_rows}
        blocks.append({
            "base_seed": block_seed,
            "cases": CASES_PER_BLOCK,
            "world_results": block_worlds,
        })

    mean_scramble_penalty_by_world = {
        model: {
            world: overall_penalty_sum[model][world] / len(BLOCK_SEED_BASES)
            for world in WORLDS
        }
        for model in ("C1", "N1")
    }

    for model in sign_counts:
        sign_counts[model]["total_cells"] = sum(sign_counts[model].values())

    result = {
        "record": "KEIRIN_SYNTHETIC_STRUCTURE_SCRAMBLE_NEGATIVE_CONTROL_v1",
        "status": "PASS",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "negative_control": "DETERMINISTIC_RIDER_TO_STRUCTURE_SLOT_ROTATION",
        "rotation_slots": 1,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "worlds": list(WORLDS),
        "world_evaluations": total_cases * len(WORLDS),
        "model_condition_world_evaluations": total_cases * len(WORLDS) * len(MODELS) * 2,
        "new_seed_selection": False,
        "structure_slot_multiset_preserved": True,
        "all_riders_structure_changed": True,
        "individual_PRE_fields_preserved": True,
        "truth_distribution_unchanged": True,
        "max_C0_scramble_probability_difference": max_c0_scramble_probability_difference,
        "max_C1_N1_rank1_marginal_difference": max_c1_n1_rank1_marginal_difference,
        "max_prediction_probability_mass_error": max_prediction_probability_mass_error,
        "scramble_penalty_sign_counts": sign_counts,
        "mean_scrambled_minus_intact_log_loss_by_world": mean_scramble_penalty_by_world,
        "blocks": blocks,
        "pass_does_not_require_any_sign_or_ranking": True,
        "scientific_decision": "NEGATIVE_CONTROL_DIAGNOSTIC_ONLY_NO_SELECTION_RETUNING_FREEZE_OR_PROMOTION",
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
    print("KEIRIN_SYNTHETIC_STRUCTURE_SCRAMBLE_NEGATIVE_CONTROL_PASS")


if __name__ == "__main__":
    main()
