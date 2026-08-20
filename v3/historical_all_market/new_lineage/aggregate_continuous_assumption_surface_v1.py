from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import string
from typing import Iterable

from c0_c1_n1_broad_assumption_range_stress_v1 import MODELS, TIER_A_LINE_SHAPES
from c0_c1_n1_continuous_assumption_surface_v1 import (
    EXPECTED_CELLS_PER_SHARD,
    EXPECTED_EVALUATIONS_PER_SHARD,
    HALTON_BLOCK_COUNT,
    LOCKED_RACES_PER_CONTEXT,
    LOCKED_SEED,
    point_indices_for_block,
)
from continuous_assumption_surface_v1 import (
    DIMENSION_RANGES,
    EXPECTED_CANONICAL_POINTS_SHA256,
    POINT_COUNT,
    point_audit_record,
    quartile_for_dimension,
    validate_surface,
)

EXPECTED_SHARD_COUNT = 48
EXPECTED_CELL_COUNT = 41472
EXPECTED_SCENARIO_RACE_EVALUATIONS = 995328


def _validate_exact_head(executed_head: str) -> None:
    if len(executed_head) != 40 or any(c not in string.hexdigits for c in executed_head):
        raise ValueError("executed_head_must_be_exact_40_hex_sha")


def _bucket() -> dict:
    return {
        "count": 0,
        "winner_counts": {model: 0 for model in MODELS},
        "sum_N1_minus_C0_log_loss": 0.0,
        "sum_C1_minus_C0_log_loss": 0.0,
    }


def _update_bucket(bucket: dict, cell: dict) -> None:
    bucket["count"] += 1
    bucket["winner_counts"][cell["winner"]] += 1
    bucket["sum_N1_minus_C0_log_loss"] += (
        float(cell["models"]["N1"]["log_loss"]) - float(cell["models"]["C0"]["log_loss"])
    )
    bucket["sum_C1_minus_C0_log_loss"] += (
        float(cell["models"]["C1"]["log_loss"]) - float(cell["models"]["C0"]["log_loss"])
    )


def _finish_bucket(bucket: dict) -> dict:
    n = bucket["count"]
    if n <= 0:
        raise AssertionError("empty_surface_breakdown_bucket")
    return {
        "cell_count": n,
        "winner_counts": bucket["winner_counts"],
        "mean_signed_N1_minus_C0_log_loss": bucket["sum_N1_minus_C0_log_loss"] / n,
        "mean_signed_C1_minus_C0_log_loss": bucket["sum_C1_minus_C0_log_loss"] / n,
    }


def _nearest_rank_p90(values: list[float]) -> float:
    if not values:
        raise AssertionError("empty_p90_values")
    ordered = sorted(values)
    rank = max(1, math.ceil(0.90 * len(ordered)))
    return ordered[rank - 1]


def _load_shards(input_dir: Path) -> list[dict]:
    shards = []
    for path in sorted(input_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if data.get("record") == "C0_C1_N1_CONTINUOUS_ASSUMPTION_SURFACE_SHARD_v1":
            shards.append(data)
    return shards


def aggregate(input_dir: Path, executed_head: str) -> dict:
    validate_surface()
    _validate_exact_head(executed_head)
    shards = _load_shards(input_dir)
    if len(shards) != EXPECTED_SHARD_COUNT:
        raise AssertionError(f"continuous_surface_shard_count:{len(shards)}:{EXPECTED_SHARD_COUNT}")

    expected_keys = {
        (line_id, block)
        for line_id in TIER_A_LINE_SHAPES
        for block in range(HALTON_BLOCK_COUNT)
    }
    seen_shards = set()
    seen_cells = set()
    canonical_cell_lines: list[str] = []

    overall = _bucket()
    model_metric_sums = {
        model: {"log_loss": 0.0, "kl": 0.0, "brier": 0.0}
        for model in MODELS
    }
    excess_values = {model: [] for model in MODELS}

    by_line = {line_id: _bucket() for line_id in TIER_A_LINE_SHAPES}
    by_pre: dict[str, dict] = {}
    by_bank: dict[str, dict] = {}
    by_wind: dict[str, dict] = {}
    by_rho: dict[str, dict] = {}
    by_point = {str(i): _bucket() for i in range(1, POINT_COUNT + 1)}
    by_parameter_quartile = {
        name: {str(q): _bucket() for q in range(1, 5)}
        for name, _, _ in DIMENSION_RANGES
    }
    by_relation_q_rho: dict[str, dict] = {}
    by_relation_q_disruption_q_rho: dict[str, dict] = {}

    evaluation_total = 0
    for shard in shards:
        key = (shard.get("line_id"), int(shard.get("halton_block_index", -1)))
        if key not in expected_keys:
            raise AssertionError(f"unexpected_continuous_surface_shard:{key}")
        if key in seen_shards:
            raise AssertionError(f"duplicate_continuous_surface_shard:{key}")
        seen_shards.add(key)
        line_id, block = key

        if shard.get("executed_head") != executed_head:
            raise AssertionError(f"mixed_surface_head:{key}:{shard.get('executed_head')}")
        if shard.get("seed") != LOCKED_SEED:
            raise AssertionError(f"surface_seed_drift:{key}")
        if shard.get("races_per_structural_context_per_truth_point") != LOCKED_RACES_PER_CONTEXT:
            raise AssertionError(f"surface_race_count_drift:{key}")
        if shard.get("canonical_64_point_surface_sha256") != EXPECTED_CANONICAL_POINTS_SHA256:
            raise AssertionError(f"surface_point_hash_drift:{key}")
        if shard.get("line_shape") != list(TIER_A_LINE_SHAPES[line_id]):
            raise AssertionError(f"surface_line_shape_drift:{key}")
        if shard.get("point_indices") != list(point_indices_for_block(block)):
            raise AssertionError(f"surface_block_point_membership_drift:{key}")
        if shard.get("cell_count") != EXPECTED_CELLS_PER_SHARD:
            raise AssertionError(f"surface_shard_cell_count_drift:{key}")
        if shard.get("scenario_race_evaluations") != EXPECTED_EVALUATIONS_PER_SHARD:
            raise AssertionError(f"surface_shard_evaluation_count_drift:{key}")
        firewall = shard.get("scientific_firewall", {})
        if firewall.get("ECON_HOLDOUT1000") != "SEALED":
            raise AssertionError(f"surface_holdout_firewall_drift:{key}")
        if firewall.get("RESULT_PAYOUT_access") != "UNAUTHORIZED":
            raise AssertionError(f"surface_result_payout_firewall_drift:{key}")
        if firewall.get("new_untouched_validation") != "CLOSED":
            raise AssertionError(f"surface_untouched_firewall_drift:{key}")
        if firewall.get("model_promotion") != "PROHIBITED":
            raise AssertionError(f"surface_promotion_firewall_drift:{key}")

        evaluation_total += int(shard["scenario_race_evaluations"])
        for cell in shard["cells"]:
            point_index = int(cell["point_index"])
            if point_index not in point_indices_for_block(block):
                raise AssertionError(f"surface_cell_outside_block:{key}:{point_index}")
            cell_key = (
                line_id,
                cell["pre_world"],
                int(cell["bank"]),
                float(cell["wind"]),
                float(cell["rho"]),
                point_index,
            )
            if cell_key in seen_cells:
                raise AssertionError(f"duplicate_surface_cell:{cell_key}")
            seen_cells.add(cell_key)

            if cell["winner"] not in MODELS:
                raise AssertionError(f"surface_unknown_winner:{cell_key}:{cell['winner']}")
            for model in MODELS:
                metrics = cell["models"].get(model)
                if set(metrics or {}) != {"log_loss", "kl", "brier"}:
                    raise AssertionError(f"surface_model_metrics_missing:{cell_key}:{model}")
                for metric in ("log_loss", "kl", "brier"):
                    value = float(metrics[metric])
                    if not math.isfinite(value):
                        raise AssertionError(f"surface_nonfinite_metric:{cell_key}:{model}:{metric}")
                    model_metric_sums[model][metric] += value
                excess = float(cell["excess_log_loss"][model])
                if excess < -1e-12 or not math.isfinite(excess):
                    raise AssertionError(f"surface_invalid_excess:{cell_key}:{model}:{excess}")
                excess_values[model].append(max(0.0, excess))

            _update_bucket(overall, cell)
            _update_bucket(by_line[line_id], cell)
            by_pre.setdefault(cell["pre_world"], _bucket())
            _update_bucket(by_pre[cell["pre_world"]], cell)
            bank_key = str(cell["bank"])
            by_bank.setdefault(bank_key, _bucket())
            _update_bucket(by_bank[bank_key], cell)
            wind_key = str(cell["wind"])
            by_wind.setdefault(wind_key, _bucket())
            _update_bucket(by_wind[wind_key], cell)
            rho_key = str(cell["rho"])
            by_rho.setdefault(rho_key, _bucket())
            _update_bucket(by_rho[rho_key], cell)
            _update_bucket(by_point[str(point_index)], cell)

            for name, _, _ in DIMENSION_RANGES:
                q = str(quartile_for_dimension(point_index, name))
                _update_bucket(by_parameter_quartile[name][q], cell)

            relation_q = quartile_for_dimension(point_index, "relation_strength")
            disruption_q = quartile_for_dimension(point_index, "disruption_weight")
            rq_key = f"relation_Q{relation_q}|rho_{rho_key}"
            by_relation_q_rho.setdefault(rq_key, _bucket())
            _update_bucket(by_relation_q_rho[rq_key], cell)
            rdq_key = f"relation_Q{relation_q}|disruption_Q{disruption_q}|rho_{rho_key}"
            by_relation_q_disruption_q_rho.setdefault(rdq_key, _bucket())
            _update_bucket(by_relation_q_disruption_q_rho[rdq_key], cell)

            canonical_cell_lines.append(json.dumps({
                "key": cell_key,
                "winner": cell["winner"],
                "models": cell["models"],
                "excess_log_loss": cell["excess_log_loss"],
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    if seen_shards != expected_keys:
        raise AssertionError(f"surface_missing_shards:{sorted(expected_keys - seen_shards)}")
    if len(seen_cells) != EXPECTED_CELL_COUNT:
        raise AssertionError(f"surface_total_cell_count:{len(seen_cells)}:{EXPECTED_CELL_COUNT}")
    if evaluation_total != EXPECTED_SCENARIO_RACE_EVALUATIONS:
        raise AssertionError(
            f"surface_total_evaluations:{evaluation_total}:{EXPECTED_SCENARIO_RACE_EVALUATIONS}"
        )
    if overall["count"] != EXPECTED_CELL_COUNT:
        raise AssertionError("surface_overall_bucket_count_drift")

    canonical_cell_lines.sort()
    all_cells_sha256 = hashlib.sha256(
        ("\n".join(canonical_cell_lines) + "\n").encode("utf-8")
    ).hexdigest()

    overall_finished = _finish_bucket(overall)
    robustness = {}
    for model in MODELS:
        values = excess_values[model]
        robustness[model] = {
            "mean_excess_log_loss": sum(values) / len(values),
            "worst_case_excess_log_loss": max(values),
            "p90_excess_log_loss_nearest_rank": _nearest_rank_p90(values),
            "zero_regret_cell_count": sum(abs(x) <= 1e-15 for x in values),
            "mean_log_loss": model_metric_sums[model]["log_loss"] / EXPECTED_CELL_COUNT,
            "mean_kl": model_metric_sums[model]["kl"] / EXPECTED_CELL_COUNT,
            "mean_brier": model_metric_sums[model]["brier"] / EXPECTED_CELL_COUNT,
        }

    point_breakdown = {}
    for i in range(1, POINT_COUNT + 1):
        finished = _finish_bucket(by_point[str(i)])
        finished["truth_point"] = point_audit_record(i)
        point_breakdown[f"H{i:03d}"] = finished

    return {
        "record": "C0_C1_N1_CONTINUOUS_ASSUMPTION_SURFACE_AGGREGATE_v1",
        "status": "SYNTHETIC_ENGINEERING_BOUNDARY_MAPPING_ONLY",
        "terminal": "CONTINUOUS_ASSUMPTION_SURFACE_LOCKED_995328_PASS",
        "executed_head": executed_head,
        "seed": LOCKED_SEED,
        "canonical_64_point_surface_sha256": EXPECTED_CANONICAL_POINTS_SHA256,
        "all_cells_canonical_sha256": all_cells_sha256,
        "shard_count": len(seen_shards),
        "line_shape_count": len(TIER_A_LINE_SHAPES),
        "continuous_truth_point_count": POINT_COUNT,
        "scenario_world_cell_count": len(seen_cells),
        "total_scenario_race_evaluations": evaluation_total,
        "overall": overall_finished,
        "robustness": robustness,
        "breakdowns": {
            "by_line_shape": {k: _finish_bucket(v) for k, v in sorted(by_line.items())},
            "by_PRE_world": {k: _finish_bucket(v) for k, v in sorted(by_pre.items())},
            "by_bank": {k: _finish_bucket(v) for k, v in sorted(by_bank.items())},
            "by_wind": {k: _finish_bucket(v) for k, v in sorted(by_wind.items())},
            "by_rho": {k: _finish_bucket(v) for k, v in sorted(by_rho.items())},
            "by_truth_point": point_breakdown,
            "by_parameter_quartile": {
                name: {q: _finish_bucket(bucket) for q, bucket in sorted(groups.items())}
                for name, groups in by_parameter_quartile.items()
            },
            "relation_strength_quartile_x_rho": {
                k: _finish_bucket(v) for k, v in sorted(by_relation_q_rho.items())
            },
            "relation_strength_quartile_x_disruption_weight_quartile_x_rho": {
                k: _finish_bucket(v)
                for k, v in sorted(by_relation_q_disruption_q_rho.items())
            },
        },
        "interpretation_lock": {
            "negative_N1_minus_C0_delta_means_N1_lower_log_loss": True,
            "negative_C1_minus_C0_delta_means_C1_lower_log_loss": True,
            "surface_points_are_engineering_coverage_not_population_draws": True,
            "synthetic_count_does_not_upgrade_evidence_tier": True,
            "no_fitted_boundary_model_in_primary_receipt": True,
            "no_real_world_winner_claim": True,
        },
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
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--executed-head", required=True)
    args = parser.parse_args()
    result = aggregate(args.input_dir, args.executed_head)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
