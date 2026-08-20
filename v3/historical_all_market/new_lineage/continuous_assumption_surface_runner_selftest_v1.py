from __future__ import annotations

from dataclasses import replace

from broad_stress_fast_kernel_v1 import stress_truth_array
from c0_c1_n1_broad_assumption_range_stress_v1 import (
    BANKS,
    PRE_WORLDS,
    RHOS,
    TIER_A_LINE_SHAPES,
    WINDS,
    _apply_exact_rho,
    _cached_predictions,
    _line_race,
)
from c0_c1_n1_continuous_assumption_surface_v1 import (
    HALTON_BLOCK_COUNT,
    POINTS_PER_BLOCK,
    point_indices_for_block,
)
from continuous_assumption_surface_v1 import POINT_COUNT, stress_assumptions, validate_surface
from digital_twin_v1 import pre_view


def _visible_nontruth_view(race) -> tuple:
    pre = pre_view(race)
    return (
        pre["race_band"],
        tuple(
            (
                r["car_no"], r["class"], r["score"], r["style"],
                r["line_id"], r["line_position"], r["line_size"],
                r["H"], r["B"], r["S"], r["nige"], r["makuri"], r["sashi"], r["mark"],
            )
            for r in pre["riders"]
        ),
    )


def main() -> None:
    validate_surface()

    all_indices = []
    for block in range(HALTON_BLOCK_COUNT):
        ids = point_indices_for_block(block)
        assert len(ids) == POINTS_PER_BLOCK
        all_indices.extend(ids)
    assert all_indices == list(range(1, POINT_COUNT + 1))
    assert len(set(all_indices)) == POINT_COUNT

    try:
        point_indices_for_block(HALTON_BLOCK_COUNT)
        raise AssertionError("out_of_lock_halton_block_not_rejected")
    except ValueError:
        pass

    assert set(TIER_A_LINE_SHAPES) == {"L43", "L421", "L4111", "L331", "L322", "L2221"}
    assert PRE_WORLDS == ("R0_CURRENT_SYNTHETIC", "R1_EMPIRICAL_MARGINAL", "R2_EMPIRICAL_JOINT")
    assert BANKS == (333, 400, 500)
    assert WINDS == (0.0, 1.5, 3.0, 5.0)
    assert RHOS == (0.55, 0.75, 0.90)

    pre_world = "R2_EMPIRICAL_JOINT"
    line_id = "L43"
    seed = 20260820
    race_index = 4
    base = _line_race(pre_world, line_id, seed, race_index)
    visible_before = _visible_nontruth_view(base)
    predictions = _cached_predictions(pre_world, line_id, seed, race_index)
    prediction_snapshot = {m: p.copy() for m, p in predictions.items()}

    for rho in RHOS:
        rho_race = _apply_exact_rho(base, seed, race_index, rho)
        assert _visible_nontruth_view(rho_race) == visible_before
        for bank in (333, 500):
            for wind in (0.0, 5.0):
                race = replace(rho_race, bank_length_m=bank, wind_speed_mps=wind)
                for point_index in (1, 32, 64):
                    cfg = stress_assumptions(point_index)
                    truth = stress_truth_array(race, cfg)
                    assert abs(float(truth.sum()) - 1.0) < 1e-10
                    assert (truth >= 0.0).all()
                    assert _visible_nontruth_view(race) == visible_before
                    for model, pred in _cached_predictions(pre_world, line_id, seed, race_index).items():
                        assert (pred == prediction_snapshot[model]).all()

    print("CONTINUOUS_ASSUMPTION_SURFACE_RUNNER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
