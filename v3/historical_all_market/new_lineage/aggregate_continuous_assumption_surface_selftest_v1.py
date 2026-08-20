from __future__ import annotations

from pathlib import Path

import aggregate_continuous_assumption_surface_v1 as agg
from c0_c1_n1_broad_assumption_range_stress_v1 import (
    BANKS,
    PRE_WORLDS,
    RHOS,
    TIER_A_LINE_SHAPES,
    WINDS,
)
from c0_c1_n1_continuous_assumption_surface_v1 import (
    HALTON_BLOCK_COUNT,
    LOCKED_RACES_PER_CONTEXT,
    LOCKED_SEED,
    point_indices_for_block,
)
from continuous_assumption_surface_v1 import (
    EXPECTED_CANONICAL_POINTS_SHA256,
    point_audit_record,
)

HEAD = "a" * 40


def fake_cell(pre_world, bank, wind, rho, point_index):
    return {
        "pre_world": pre_world,
        "bank": bank,
        "wind": wind,
        "rho": rho,
        "point_index": point_index,
        "scenario_id": f"H{point_index:03d}",
        "winner": "N1",
        "models": {
            "C0": {"log_loss": 1.00, "kl": 0.20, "brier": 0.10},
            "C1": {"log_loss": 1.02, "kl": 0.22, "brier": 0.11},
            "N1": {"log_loss": 0.99, "kl": 0.19, "brier": 0.09},
        },
        "excess_log_loss": {"C0": 0.01, "C1": 0.03, "N1": 0.0},
    }


def fake_shards():
    out = []
    for line_id, shape in TIER_A_LINE_SHAPES.items():
        for block in range(HALTON_BLOCK_COUNT):
            point_indices = point_indices_for_block(block)
            cells = [
                fake_cell(pre_world, bank, wind, rho, point_index)
                for pre_world in PRE_WORLDS
                for bank in BANKS
                for wind in WINDS
                for rho in RHOS
                for point_index in point_indices
            ]
            out.append({
                "record": "C0_C1_N1_CONTINUOUS_ASSUMPTION_SURFACE_SHARD_v1",
                "status": "SYNTHETIC_ENGINEERING_BOUNDARY_MAPPING_ONLY",
                "executed_head": HEAD,
                "seed": LOCKED_SEED,
                "races_per_structural_context_per_truth_point": LOCKED_RACES_PER_CONTEXT,
                "line_id": line_id,
                "line_shape": list(shape),
                "halton_block_index": block,
                "point_indices": list(point_indices),
                "truth_points": [point_audit_record(i) for i in point_indices],
                "canonical_64_point_surface_sha256": EXPECTED_CANONICAL_POINTS_SHA256,
                "cell_count": len(cells),
                "scenario_race_evaluations": len(cells) * LOCKED_RACES_PER_CONTEXT,
                "cells": cells,
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
            })
    return out


def main() -> None:
    shards = fake_shards()
    assert len(shards) == 48

    original_loader = agg._load_shards
    try:
        agg._load_shards = lambda _: shards
        result = agg.aggregate(Path("."), HEAD)
        assert result["terminal"] == "CONTINUOUS_ASSUMPTION_SURFACE_LOCKED_995328_PASS"
        assert result["shard_count"] == 48
        assert result["scenario_world_cell_count"] == 41472
        assert result["total_scenario_race_evaluations"] == 995328
        assert result["overall"]["winner_counts"] == {"C0": 0, "C1": 0, "N1": 41472}
        assert abs(result["overall"]["mean_signed_N1_minus_C0_log_loss"] + 0.01) < 1e-12
        assert abs(result["overall"]["mean_signed_C1_minus_C0_log_loss"] - 0.02) < 1e-12
        assert len(result["all_cells_canonical_sha256"]) == 64

        agg._load_shards = lambda _: shards[:-1]
        try:
            agg.aggregate(Path("."), HEAD)
            raise AssertionError("missing_surface_shard_not_rejected")
        except AssertionError as exc:
            assert "continuous_surface_shard_count" in str(exc)
    finally:
        agg._load_shards = original_loader

    print("AGGREGATE_CONTINUOUS_ASSUMPTION_SURFACE_SELFTEST_PASS")


if __name__ == "__main__":
    main()
