from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import argparse
import json
import math
import random
from typing import Dict, Mapping, Tuple

from c0_c1_n1_multiworld_stress_v1 import MODELS, _stress_race
from c0_c1_n1_reality_scaled_multiworld_stress_v1 import _stress_bundle
from c0_c1_n1_pre_realism_multiworld_stress_v1 import _r2_stress_bundle
from digital_twin_stress_grid_v1 import ASSUMPTION_GRID, validate_assumption_grid
from digital_twin_v1 import Race, pre_view
from long_line_topology_fixture_v1 import apply_line_shape_fixture, assert_line_topology_invariants
from broad_stress_fast_kernel_v1 import pred_array, score_arrays, stress_truth_array

Top3 = Tuple[int, int, int]
LOCKED_SEED = 20260820
LOCKED_RACES_PER_CONTEXT = 24
PRE_WORLDS = ("R0_CURRENT_SYNTHETIC", "R1_EMPIRICAL_MARGINAL", "R2_EMPIRICAL_JOINT")
TIER_A_LINE_SHAPES = {
    "L43": (4, 3), "L421": (4, 2, 1), "L4111": (4, 1, 1, 1),
    "L331": (3, 3, 1), "L322": (3, 2, 2), "L2221": (2, 2, 2, 1),
}
TIER_B_LINE_SHAPES = {
    "L7": (7,), "L61": (6, 1), "L52": (5, 2), "L511": (5, 1, 1),
    "L3211": (3, 2, 1, 1), "L31111": (3, 1, 1, 1, 1),
    "L22111": (2, 2, 1, 1, 1), "L211111": (2, 1, 1, 1, 1, 1),
    "L1111111": (1, 1, 1, 1, 1, 1, 1),
}
LINE_SHAPES = {**TIER_A_LINE_SHAPES, **TIER_B_LINE_SHAPES}
BANKS = (333, 400, 500)
WINDS = (0.0, 1.5, 3.0, 5.0)
RHOS = (0.55, 0.75, 0.90)


@lru_cache(maxsize=None)
def _base_race(pre_world: str, seed: int, race_index: int) -> Race:
    if pre_world == "R0_CURRENT_SYNTHETIC":
        return _stress_race(seed, race_index)
    if pre_world == "R1_EMPIRICAL_MARGINAL":
        return _stress_bundle(seed, race_index).race
    if pre_world == "R2_EMPIRICAL_JOINT":
        return _r2_stress_bundle(seed, race_index).race
    raise ValueError(f"unknown_pre_world:{pre_world}")


def _car_order(seed: int, race_index: int, race: Race) -> tuple[int, ...]:
    cars = sorted(r.car_no for r in race.riders)
    rng = random.Random(f"keirin-broad-line-order:{seed}:{race_index}")
    rng.shuffle(cars)
    return tuple(cars)


def _sample_standardize(values: list[float]) -> list[float]:
    n = len(values)
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    if var <= 1e-15:
        raise ValueError("rho_visible_score_variance_too_small")
    sd = math.sqrt(var)
    return [(x - mean) / sd for x in values]


def _apply_exact_rho(race: Race, seed: int, race_index: int, rho: float) -> Race:
    if rho not in RHOS:
        raise ValueError(f"rho_not_locked:{rho}")
    riders = list(race.riders)
    z = _sample_standardize([float(r.observed_score) for r in riders])
    rng = random.Random(f"keirin-broad-rho-residual:{seed}:{race_index}")
    residual = _sample_standardize([rng.gauss(0.0, 1.0) for _ in riders])
    projection = sum(a * b for a, b in zip(residual, z)) / sum(x * x for x in z)
    orthogonal = _sample_standardize([a - projection * b for a, b in zip(residual, z)])
    covariance = sum(a * b for a, b in zip(orthogonal, z)) / (len(z) - 1)
    if abs(covariance) > 1e-10:
        raise AssertionError(f"rho_residual_not_orthogonal:{covariance}")
    w = math.sqrt(1.0 - rho * rho)
    latent = [rho * a + w * b for a, b in zip(z, orthogonal)]
    return replace(race, riders=tuple(replace(r, latent_skill=latent[i]) for i, r in enumerate(riders)))


@lru_cache(maxsize=None)
def _line_race(pre_world: str, line_id: str, seed: int, race_index: int) -> Race:
    if line_id not in LINE_SHAPES:
        raise ValueError(f"line_shape_not_locked:{line_id}")
    base = _base_race(pre_world, seed, race_index)
    out = apply_line_shape_fixture(base, LINE_SHAPES[line_id], car_order=_car_order(seed, race_index, base))
    assert_line_topology_invariants(out, LINE_SHAPES[line_id])
    return out


@lru_cache(maxsize=None)
def _cached_predictions(pre_world: str, line_id: str, seed: int, race_index: int):
    pre = pre_view(_line_race(pre_world, line_id, seed, race_index))
    return {model: pred_array(fn(pre)) for model, fn in MODELS.items()}


def _materialize(pre_world: str, line_id: str, bank: int, wind: float, rho: float, seed: int, race_index: int) -> Race:
    if bank not in BANKS or wind not in WINDS or rho not in RHOS:
        raise ValueError("broad_axis_not_locked")
    race = _apply_exact_rho(_line_race(pre_world, line_id, seed, race_index), seed, race_index, rho)
    return replace(race, bank_length_m=bank, wind_speed_mps=wind)


def evaluate_line_shape(
    line_id: str,
    *,
    seed: int = LOCKED_SEED,
    races_per_context: int = LOCKED_RACES_PER_CONTEXT,
    executed_head: str,
) -> dict:
    validate_assumption_grid()
    if line_id not in LINE_SHAPES:
        raise ValueError(f"line_shape_not_locked:{line_id}")
    if seed != LOCKED_SEED or races_per_context != LOCKED_RACES_PER_CONTEXT:
        raise ValueError(f"broad_execution_lock_mismatch:{seed}:{races_per_context}")
    if not executed_head or len(executed_head) != 40:
        raise ValueError("executed_head_must_be_exact_40_hex_sha")

    cells = []
    for pre_world in PRE_WORLDS:
        totals = {
            (bank, wind, rho, cfg.scenario_id): {m: [0.0, 0.0, 0.0] for m in MODELS}
            for bank in BANKS for wind in WINDS for rho in RHOS for cfg in ASSUMPTION_GRID
        }
        for race_index in range(races_per_context):
            line_race = _line_race(pre_world, line_id, seed, race_index)
            preds = _cached_predictions(pre_world, line_id, seed, race_index)
            rho_races = {rho: _apply_exact_rho(line_race, seed, race_index, rho) for rho in RHOS}
            for bank in BANKS:
                for wind in WINDS:
                    for rho in RHOS:
                        race = replace(rho_races[rho], bank_length_m=bank, wind_speed_mps=wind)
                        for cfg in ASSUMPTION_GRID:
                            truth = stress_truth_array(race, cfg)
                            if abs(float(truth.sum()) - 1.0) > 1e-10:
                                raise AssertionError("truth_mass")
                            cell = totals[(bank, wind, rho, cfg.scenario_id)]
                            for model, pred in preds.items():
                                if abs(float(pred.sum()) - 1.0) > 1e-10:
                                    raise AssertionError("prediction_mass")
                                ll, kl, brier = score_arrays(truth, pred)
                                cell[model][0] += ll
                                cell[model][1] += kl
                                cell[model][2] += brier
        for (bank, wind, rho, scenario_id), cell in totals.items():
            rows = {
                m: {
                    "log_loss": cell[m][0] / races_per_context,
                    "kl": cell[m][1] / races_per_context,
                    "brier": cell[m][2] / races_per_context,
                }
                for m in MODELS
            }
            best = min(rows[m]["log_loss"] for m in MODELS)
            winner = min(MODELS, key=lambda m: rows[m]["log_loss"])
            cells.append({
                "pre_world": pre_world,
                "bank": bank,
                "wind": wind,
                "rho": rho,
                "scenario_id": scenario_id,
                "winner": winner,
                "models": rows,
                "excess_log_loss": {m: rows[m]["log_loss"] - best for m in MODELS},
            })

    expected_cells = len(PRE_WORLDS) * len(BANKS) * len(WINDS) * len(RHOS) * len(ASSUMPTION_GRID)
    if len(cells) != expected_cells:
        raise AssertionError(f"line_shard_cell_count_mismatch:{len(cells)}:{expected_cells}")
    return {
        "record": "C0_C1_N1_BROAD_ASSUMPTION_RANGE_LINE_SHARD_v1",
        "status": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "executed_head": executed_head,
        "seed": seed,
        "races_per_structural_context": races_per_context,
        "line_id": line_id,
        "line_shape": list(LINE_SHAPES[line_id]),
        "topology_tier": "A" if line_id in TIER_A_LINE_SHAPES else "B",
        "cell_count": expected_cells,
        "scenario_race_evaluations": expected_cells * races_per_context,
        "cells": cells,
        "claim_boundary": "No topology frequency, real causal effect, predictive edge, ROI, promotion or real-world equivalence may be inferred.",
        "scientific_firewall": {
            "ECON_HOLDOUT1000": "SEALED",
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "same_source_realism_retuning": "CLOSED",
            "untouched_validation": "CLOSED",
            "model_promotion": "PROHIBITED",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--line-shape", required=True, choices=tuple(LINE_SHAPES))
    parser.add_argument("--executed-head", required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate_line_shape(args.line_shape, executed_head=args.executed_head), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
