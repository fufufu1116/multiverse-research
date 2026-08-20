from __future__ import annotations

from dataclasses import replace
import json
from typing import Dict, Mapping, Tuple

from c0_c1_n1_multiworld_stress_v1 import (
    MODELS,
    _expected_log_loss,
    _joint_brier,
    _truth_entropy,
    evaluate as baseline_evaluate,
)
from digital_twin_empirical_pre_adapter_v1 import (
    EmpiricalRaceBundle,
    generate_empirical_candidate_bundle,
    model_pre_view,
)
from digital_twin_stress_grid_v1 import (
    ASSUMPTION_GRID,
    stress_truth_joint,
    validate_assumption_grid,
)

Top3 = Tuple[int, int, int]


def _stress_bundle(seed: int, race_index: int) -> EmpiricalRaceBundle:
    """Use the existing engineering bank/wind cycles for apples-to-apples stress.

    Bank and wind are still unmeasured by the staged PRE sensor source. Equal cycling
    deliberately prevents their synthetic generator frequency from becoming an implied
    population claim while isolating the observable-PRE distribution change.
    """
    bundle = generate_empirical_candidate_bundle(seed=seed, race_index=race_index)
    bank_cycle = (333, 400, 500)
    wind_cycle = (0.0, 1.5, 3.0, 5.0)
    race = replace(
        bundle.race,
        bank_length_m=bank_cycle[race_index % len(bank_cycle)],
        wind_speed_mps=wind_cycle[race_index % len(wind_cycle)],
    )
    return replace(bundle, race=race)


def _aggregate_scenario_means(scenarios: list[dict]) -> dict:
    out = {
        model: {"log_loss": 0.0, "kl": 0.0, "brier": 0.0}
        for model in MODELS
    }
    for row in scenarios:
        for model in MODELS:
            for metric in out[model]:
                out[model][metric] += float(row["models"][model][metric])
    n = len(scenarios)
    return {
        model: {metric: value / n for metric, value in metrics.items()}
        for model, metrics in out.items()
    }


def evaluate(seed: int = 20260820, n_races: int = 96) -> dict:
    validate_assumption_grid()
    if n_races <= 0:
        raise ValueError("n_races_must_be_positive")

    totals = {
        cfg.scenario_id: {
            model: {"log_loss": 0.0, "kl": 0.0, "brier": 0.0}
            for model in MODELS
        }
        for cfg in ASSUMPTION_GRID
    }

    for race_index in range(n_races):
        bundle = _stress_bundle(seed, race_index)
        pre = model_pre_view(bundle)
        if pre.get("calibration_status") != "CANDIDATE_SENSOR_ENVELOPE_NOT_REALITY_ADMISSION":
            raise AssertionError("sensor_only_status_lost_before_model")
        if pre.get("score_semantics") != "BAND_SCALED_MODEL_Z_FROM_SENSOR_ONLY_RAW_SCORE":
            raise AssertionError("score_unit_transform_lost_before_model")

        predictions: Dict[str, Mapping[Top3, float]] = {
            name: fn(pre) for name, fn in MODELS.items()
        }
        for cfg in ASSUMPTION_GRID:
            truth = stress_truth_joint(bundle.race, cfg)
            entropy = _truth_entropy(truth)
            if abs(sum(truth.values()) - 1.0) > 1e-10:
                raise AssertionError(f"truth_mass_failed:{cfg.scenario_id}")

            for model, pred in predictions.items():
                if set(pred) != set(truth):
                    raise AssertionError(f"support_mismatch:{cfg.scenario_id}:{model}")
                if abs(sum(pred.values()) - 1.0) > 1e-10:
                    raise AssertionError(f"prediction_mass_failed:{cfg.scenario_id}:{model}")
                ll = _expected_log_loss(truth, pred)
                totals[cfg.scenario_id][model]["log_loss"] += ll
                totals[cfg.scenario_id][model]["kl"] += ll - entropy
                totals[cfg.scenario_id][model]["brier"] += _joint_brier(truth, pred)

    scenarios = []
    for cfg in ASSUMPTION_GRID:
        rows = {
            model: {
                metric: value / n_races
                for metric, value in totals[cfg.scenario_id][model].items()
            }
            for model in MODELS
        }
        winner = min(rows, key=lambda model: rows[model]["log_loss"])
        scenarios.append(
            {
                "scenario_id": cfg.scenario_id,
                "world_family": cfg.world_family,
                "assurance": cfg.assurance,
                "winner_by_expected_log_loss": winner,
                "models": rows,
            }
        )

    win_counts = {model: 0 for model in MODELS}
    for row in scenarios:
        win_counts[row["winner_by_expected_log_loss"]] += 1

    reality_scaled_means = _aggregate_scenario_means(scenarios)
    baseline = baseline_evaluate(seed=seed, n_races=n_races)
    baseline_means = _aggregate_scenario_means(baseline["scenarios"])
    delta_vs_baseline = {
        model: {
            metric: reality_scaled_means[model][metric] - baseline_means[model][metric]
            for metric in reality_scaled_means[model]
        }
        for model in MODELS
    }

    return {
        "record": "C0_C1_N1_REALITY_SCALED_MULTIWORLD_SYNTHETIC_STRESS_v1",
        "status": "SENSOR_SHAPED_SYNTHETIC_ENGINEERING_EVIDENCE_ONLY",
        "seed": seed,
        "n_races_per_scenario": n_races,
        "scenario_count": len(ASSUMPTION_GRID),
        "observable_pre_source_status": "CANDIDATE_SENSOR_ENVELOPE_NOT_REALITY_ADMISSION",
        "observable_pre_source": "KEIRIN_DT_EMPIRICAL_ENVELOPE_COMPACT_v1",
        "score_semantics": "PREREGISTERED_BAND_SCALED_MODEL_Z_FROM_SENSOR_ONLY_RAW_SCORE",
        "bank_wind_sampling": "EXISTING_EQUAL_ENGINEERING_CYCLES_NOT_REAL_FREQUENCY",
        "line_shape_sampling": "EXISTING_SYNTHETIC_ASSUMPTION_NOT_SENSOR_CALIBRATED",
        "H_sampling": "EXISTING_SYNTHETIC_ASSUMPTION_UNMEASURED_BY_SENSOR",
        "coefficient_retuning": false,
        "scientific_claim_limit": (
            "No real-keirin predictive edge, real-world equivalence, source admission, "
            "frequency, causal coefficient, ROI, or model promotion may be inferred."
        ),
        "win_counts_by_expected_log_loss": win_counts,
        "baseline_win_counts_by_expected_log_loss": baseline["win_counts_by_expected_log_loss"],
        "mean_metrics_across_scenarios": reality_scaled_means,
        "baseline_mean_metrics_across_scenarios": baseline_means,
        "delta_mean_metrics_vs_current_synthetic_baseline": delta_vs_baseline,
        "scenarios": scenarios,
        "scientific_firewall": {
            "ECON_HOLDOUT1000": "SEALED",
            "DEV2000_C_new_lineage_rescue": "PROHIBITED",
            "same_lineage_B_C_rescue_tuning": "PROHIBITED",
            "RESULT_PAYOUT_access": "UNAUTHORIZED",
            "new_untouched_validation_opened": false,
            "model_promotion": "PROHIBITED"
        }
    }


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
