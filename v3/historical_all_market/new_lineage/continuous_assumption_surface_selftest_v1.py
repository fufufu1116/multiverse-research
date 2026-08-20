from __future__ import annotations

import math

from continuous_assumption_surface_v1 import (
    BASES,
    DIMENSION_RANGES,
    EXPECTED_CANONICAL_POINTS_SHA256,
    POINT_COUNT,
    canonical_points_sha256,
    quartile_for_dimension,
    radical_inverse,
    stress_assumptions,
    surface_parameters,
    unit_coordinates,
    validate_surface,
)


def main() -> None:
    validate_surface()

    assert math.isclose(radical_inverse(1, 2), 0.5, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(radical_inverse(2, 2), 0.25, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(radical_inverse(3, 2), 0.75, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(radical_inverse(1, 3), 1.0 / 3.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(radical_inverse(2, 3), 2.0 / 3.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(radical_inverse(3, 3), 1.0 / 9.0, rel_tol=0.0, abs_tol=1e-15)

    try:
        radical_inverse(0, 2)
        raise AssertionError("zero_halton_index_not_rejected")
    except ValueError:
        pass
    try:
        unit_coordinates(POINT_COUNT + 1)
        raise AssertionError("out_of_lock_surface_index_not_rejected")
    except ValueError:
        pass

    assert len(BASES) == 8
    assert len(DIMENSION_RANGES) == 8
    assert canonical_points_sha256() == EXPECTED_CANONICAL_POINTS_SHA256

    scenario_ids = set()
    coords = set()
    for point_index in range(1, POINT_COUNT + 1):
        cfg = stress_assumptions(point_index)
        assert cfg.assurance == "ASSUMPTION_RANGE_ONLY"
        assert cfg.world_family == "CONTINUOUS_SURFACE"
        assert cfg.scenario_id == f"H{point_index:03d}"
        scenario_ids.add(cfg.scenario_id)
        u = unit_coordinates(point_index)
        coords.add(u)
        params = surface_parameters(point_index)
        for name, low, high in DIMENSION_RANGES:
            assert low < params[name] < high, (point_index, name, params[name])
            q = quartile_for_dimension(point_index, name)
            assert q in {1, 2, 3, 4}

    assert len(scenario_ids) == POINT_COUNT
    assert len(coords) == POINT_COUNT

    for name, _, _ in DIMENSION_RANGES:
        occupied = {quartile_for_dimension(i, name) for i in range(1, POINT_COUNT + 1)}
        assert occupied == {1, 2, 3, 4}, (name, occupied)

    print("CONTINUOUS_ASSUMPTION_SURFACE_SELFTEST_PASS")
    print("canonical_points_sha256=", canonical_points_sha256())


if __name__ == "__main__":
    main()
