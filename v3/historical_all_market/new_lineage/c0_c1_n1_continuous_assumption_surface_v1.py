from __future__ import annotations

from dataclasses import replace
import argparse
import json
import string

from broad_stress_fast_kernel_v1 import score_arrays, stress_truth_array
from c0_c1_n1_broad_assumption_range_stress_v1 import (
    BANKS,
    MODELS,
    PRE_WORLDS,
    RHOS,
    TIER_A_LINE_SHAPES,
    WINDS,
    _apply_exact_rho,
    _cached_predictions,
    _line_race,
)
from continuous_assumption_surface_v1 import (
    POINT_COUNT,
    canonical_points_sha256,
    point_audit_record,
    stress_assumptions,
    validate_surface,
)

LOCKED_SEED = 20260820
LOCKED_RACES_PER_CONTEXT = 24
HALTON_BLOCK_COUNT = 8
POINTS_PER_BLOCK = 8
EXPECTED_CELLS_PER_SHARD = 864
EXPECTED_EVALUATIONS_PER_SHARD = 20736


def point_indices_for_block(block_index: int) -> tuple[int, ...]:
    if not isinstance(block_index, int) or isinstance(block_index, bool):
        raise ValueError("halton_block_index_must_be_integer")
    if block_index < 0 or block_index >= HALTON_BLOCK_COUNT:
        raise ValueError(f"halton_block_not_locked:{block_index}")
    start = block_index * POINTS_PER_BLOCK + 1
    return tuple(range(start, start + POINTS_PER_BLOCK))


def _validate_exact_head(executed_head: str) -> None:
    if len(executed_head) != 40 or any(c not in string.hexdigits for c in executed_head):
        raise ValueError("executed_head_must_be_exact_40_hex_sha")


def evaluate_surface_shard(
    line_id: str,
    block_index: int,
    *,
    seed: int = LOCKED_SEED,
    races_per_context: int = LOCKED_RACES_PER_CONTEXT,
    executed_head: str,
) -> dict:
    validate_surface()
    _validate_exact_head(executed_head)
    if line_id not in TIER_A_LINE_SHAPES:
        raise ValueError(f"continuous_surface_line_not_tier_A:{line_id}")
    if seed != LOCKED_SEED or races_per_context != LOCKED_RACES_PER_CONTEXT:
        raise ValueError(f"continuous_surface_execution_lock_mismatch:{seed}:{races_per_context}")

    point_indices = point_indices_for_block(block_index)
    if point_indices[-1] > POINT_COUNT:
        raise AssertionError("continuous_surface_block_exceeds_point_lock")
    configs = {i: stress_assumptions(i) for i in point_indices}

    totals = {
        (pre_world, bank, wind, rho, point_index): {
            model: [0.0, 0.0, 0.0] for model in MODELS
        }
        for pre_world in PRE_WORLDS
        for bank in BANKS
        for wind in WINDS
        for rho in RHOS
        for point_index in point_indices
    }

    for pre_world in PRE_WORLDS:
        for race_index in range(races_per_context):
            line_race = _line_race(pre_world, line_id, seed, race_index)
            predictions = _cached_predictions(pre_world, line_id, seed, race_index)
            for model, pred in predictions.items():
                if abs(float(pred.sum()) - 1.0) > 1e-10:
                    raise AssertionError(f"prediction_mass:{pre_world}:{line_id}:{race_index}:{model}")
            rho_races = {
                rho: _apply_exact_rho(line_race, seed, race_index, rho)
                for rho in RHOS
            }
            for bank in BANKS:
                for wind in WINDS:
                    for rho in RHOS:
                        race = replace(rho_races[rho], bank_length_m=bank, wind_speed_mps=wind)
                        for point_index in point_indices:
                            truth = stress_truth_array(race, configs[point_index])
                            if abs(float(truth.sum()) - 1.0) > 1e-10:
                                raise AssertionError(
                                    f"truth_mass:{pre_world}:{line_id}:{race_index}:{bank}:{wind}:{rho}:{point_index}"
                                )
                            cell = totals[(pre_world, bank, wind, rho, point_index)]
                            for model, pred in predictions.items():
                                ll, kl, brier = score_arrays(truth, pred)
                                cell[model][0] += ll
                                cell[model][1] += kl
                                cell[model][2] += brier

    cells = []
    for (pre_world, bank, wind, rho, point_index), cell in totals.items():
        rows = {
            model: {
                "log_loss": values[0] / races_per_context,
                "kl": values[1] / races_per_context,
                "brier": values[2] / races_per_context,
            }
            for model, values in cell.items()
        }
        best = min(rows[m]["log_loss"] for m in MODELS)
        winner = min(MODELS, key=lambda m: rows[m]["log_loss"])
        cells.append({
            "pre_world": pre_world,
            "bank": bank,
            "wind": wind,
            "rho": rho,
            "point_index": point_index,
            "scenario_id": configs[point_index].scenario_id,
            "winner": winner,
            "models": rows,
            "excess_log_loss": {m: rows[m]["log_loss"] - best for m in MODELS},
        })

    if len(cells) != EXPECTED_CELLS_PER_SHARD:
        raise AssertionError(
            f"continuous_surface_shard_cell_count_mismatch:{len(cells)}:{EXPECTED_CELLS_PER_SHARD}"
        )

    return {
        "record": "C0_C1_N1_CONTINUOUS_ASSUMPTION_SURFACE_SHARD_v1",
        "status": "SYNTHETIC_ENGINEERING_BOUNDARY_MAPPING_ONLY",
        "executed_head": executed_head,
        "seed": seed,
        "races_per_structural_context_per_truth_point": races_per_context,
        "line_id": line_id,
        "line_shape": list(TIER_A_LINE_SHAPES[line_id]),
        "halton_block_index": block_index,
        "point_indices": list(point_indices),
        "truth_points": [point_audit_record(i) for i in point_indices],
        "canonical_64_point_surface_sha256": canonical_points_sha256(),
        "cell_count": len(cells),
        "scenario_race_evaluations": len(cells) * races_per_context,
        "cells": cells,
        "claim_boundary": "Synthetic interior sensitivity/boundary mapping only; no real-world density, edge, ROI, causal effect, model promotion or equivalence may be inferred.",
        "scientific_firewall": {
            "ECON_HOLDOUT1000": "SEALED",
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "same_source_KDreams_realism_tuning": "CLOSED",
            "DEV2000_C_new_lineage_rescue": "PROHIBITED",
            "same_lineage_B_C_rescue_tuning": "PROHIBITED",
            "new_untouched_validation": "CLOSED",
            "model_promotion": "PROHIBITED",
            "real_money_wagering": "OUT_OF_SCOPE",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line-shape", required=True, choices=tuple(TIER_A_LINE_SHAPES))
    parser.add_argument("--halton-block", required=True, type=int, choices=range(HALTON_BLOCK_COUNT))
    parser.add_argument("--executed-head", required=True)
    args = parser.parse_args()
    result = evaluate_surface_shard(
        args.line_shape,
        args.halton_block,
        executed_head=args.executed_head,
    )
    if result["scenario_race_evaluations"] != EXPECTED_EVALUATIONS_PER_SHARD:
        raise AssertionError("continuous_surface_shard_evaluation_count_drift")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
