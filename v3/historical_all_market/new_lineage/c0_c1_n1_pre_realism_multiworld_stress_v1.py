from __future__ import annotations

from dataclasses import replace
import json
from typing import Dict, Mapping, Tuple

from c0_c1_n1_multiworld_stress_v1 import (
    MODELS,
    _expected_log_loss,
    _joint_brier,
    _stress_race,
    _truth_entropy,
)
from c0_c1_n1_reality_scaled_multiworld_stress_v1 import _stress_bundle
from digital_twin_empirical_pre_adapter_v1 import model_pre_view
from digital_twin_empirical_pre_adapter_v2 import (
    generate_empirical_joint_v2_bundle,
    model_pre_view_v2,
)
from digital_twin_stress_grid_v1 import (
    ASSUMPTION_GRID,
    stress_truth_joint,
    validate_assumption_grid,
)
from digital_twin_v1 import pre_view

Top3 = Tuple[int, int, int]
LOCKED_SEED = 20260820
LOCKED_N_RACES = 240
PRE_WORLDS = ("R0_CURRENT_SYNTHETIC", "R1_EMPIRICAL_MARGINAL", "R2_EMPIRICAL_JOINT")


def _r2_stress_bundle(seed: int, race_index: int):
    bundle = generate_empirical_joint_v2_bundle(seed=seed, race_index=race_index)
    bank_cycle = (333, 400, 500)
    wind_cycle = (0.0, 1.5, 3.0, 5.0)
    race = replace(
        bundle.race,
        bank_length_m=bank_cycle[race_index % len(bank_cycle)],
        wind_speed_mps=wind_cycle[race_index % len(wind_cycle)],
    )
    return replace(bundle, race=race)


def _race_and_pre(pre_world: str, seed: int, race_index: int):
    if pre_world == "R0_CURRENT_SYNTHETIC":
        race = _stress_race(seed, race_index)
        return race, pre_view(race)
    if pre_world == "R1_EMPIRICAL_MARGINAL":
        bundle = _stress_bundle(seed, race_index)
        return bundle.race, model_pre_view(bundle)
    if pre_world == "R2_EMPIRICAL_JOINT":
        bundle = _r2_stress_bundle(seed, race_index)
        return bundle.race, model_pre_view_v2(bundle)
    raise ValueError(f"unknown_pre_world:{pre_world}")


def evaluate(seed: int = LOCKED_SEED, n_races: int = LOCKED_N_RACES) -> dict:
    validate_assumption_grid()
    if seed != LOCKED_SEED or n_races != LOCKED_N_RACES:
        raise ValueError(
            f"pre_realism_execution_lock_mismatch:{seed}:{n_races}:"
            f"expected={LOCKED_SEED}:{LOCKED_N_RACES}"
        )

    totals = {
        pre_world: {
            cfg.scenario_id: {
                model: {"log_loss": 0.0, "kl": 0.0, "brier": 0.0}
                for model in MODELS
            }
            for cfg in ASSUMPTION_GRID
        }
        for pre_world in PRE_WORLDS
    }

    for pre_world in PRE_WORLDS:
        for race_index in range(n_races):
            race, pre = _race_and_pre(pre_world, seed, race_index)
            predictions: Dict[str, Mapping[Top3, float]] = {
                name: fn(pre) for name, fn in MODELS.items()
            }
            for cfg in ASSUMPTION_GRID:
                truth = stress_truth_joint(race, cfg)
                entropy = _truth_entropy(truth)
                if abs(sum(truth.values()) - 1.0) > 1e-10:
                    raise AssertionError(f"truth_mass:{pre_world}:{cfg.scenario_id}")
                for model, pred in predictions.items():
                    if set(pred) != set(truth):
                        raise AssertionError(f"support:{pre_world}:{cfg.scenario_id}:{model}")
                    if abs(sum(pred.values()) - 1.0) > 1e-10:
                        raise AssertionError(f"pred_mass:{pre_world}:{cfg.scenario_id}:{model}")
                    ll = _expected_log_loss(truth, pred)
                    totals[pre_world][cfg.scenario_id][model]["log_loss"] += ll
                    totals[pre_world][cfg.scenario_id][model]["kl"] += ll - entropy
                    totals[pre_world][cfg.scenario_id][model]["brier"] += _joint_brier(truth, pred)

    cells = []
    winner_counts = {model: 0 for model in MODELS}
    excess = {model: [] for model in MODELS}
    for pre_world in PRE_WORLDS:
        for cfg in ASSUMPTION_GRID:
            rows = {
                model: {
                    metric: value / n_races
                    for metric, value in totals[pre_world][cfg.scenario_id][model].items()
                }
                for model in MODELS
            }
            best_ll = min(rows[m]["log_loss"] for m in MODELS)
            winner = min(MODELS, key=lambda m: rows[m]["log_loss"])
            winner_counts[winner] += 1
            regret = {m: rows[m]["log_loss"] - best_ll for m in MODELS}
            for m in MODELS:
                excess[m].append(regret[m])
            cells.append({
                "pre_world": pre_world,
                "scenario_id": cfg.scenario_id,
                "truth_world_family": cfg.world_family,
                "winner_by_expected_log_loss": winner,
                "excess_log_loss_vs_cell_best": regret,
                "models": rows,
            })

    robustness = {
        model: {
            "mean_excess_log_loss": sum(vals) / len(vals),
            "worst_case_excess_log_loss": max(vals),
            "zero_regret_cell_count": sum(abs(x) <= 1e-15 for x in vals),
        }
        for model, vals in excess.items()
    }
    return {
        "record": "C0_C1_N1_PRE_REALISM_MULTIWORLD_STRESS_v1",
        "status": "SYNTHETIC_ENGINEERING_ROBUSTNESS_ONLY",
        "seed": seed,
        "n_races_per_truth_scenario_per_pre_world": n_races,
        "pre_worlds": list(PRE_WORLDS),
        "truth_scenario_count": len(ASSUMPTION_GRID),
        "scenario_world_cell_count": len(cells),
        "winner_counts": winner_counts,
        "robustness": robustness,
        "cells": cells,
        "scientific_claim_limit": "No real-keirin edge, ROI, source admission, world selection, model promotion or real-world equivalence may be inferred.",
        "scientific_firewall": {
            "ECON_HOLDOUT1000": "SEALED",
            "DEV2000_C_new_lineage_rescue": "PROHIBITED",
            "same_lineage_B_C_rescue_tuning": "PROHIBITED",
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "new_untouched_validation_opened": False,
            "model_promotion": "PROHIBITED"
        }
    }


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
