from __future__ import annotations

import hashlib
import json
from typing import Dict, Tuple

from digital_twin_stress_grid_v1 import StressAssumptions

POINT_COUNT = 64
BASES: Tuple[int, ...] = (2, 3, 5, 7, 11, 13, 17, 19)
DIMENSION_RANGES: Tuple[Tuple[str, float, float], ...] = (
    ("line_static_scale", 0.0, 1.5),
    ("relation_strength", 0.0, 1.5),
    ("wind_effect_scale", 0.0, 1.5),
    ("bank_effect_scale", 0.0, 1.0),
    ("disruption_weight", 0.0, 0.55),
    ("shock_sigma", 0.0, 1.25),
    ("shock_temperature", 1.0, 1.9),
    ("disrupted_relation_strength", 0.0, 0.15),
)
EXPECTED_CANONICAL_POINTS_SHA256 = "fba866b7421a5d19cdf5408f736691b0e34321ee799d19a09666a47beba8485a"


def radical_inverse(index: int, base: int) -> float:
    if not isinstance(index, int) or isinstance(index, bool) or index <= 0:
        raise ValueError("halton_index_must_be_positive_integer")
    if not isinstance(base, int) or isinstance(base, bool) or base < 2:
        raise ValueError("halton_base_must_be_integer_at_least_two")
    n = index
    factor = 1.0
    value = 0.0
    while n > 0:
        factor /= base
        value += factor * (n % base)
        n //= base
    if not (0.0 < value < 1.0):
        raise AssertionError(f"halton_coordinate_not_interior:{index}:{base}:{value}")
    return value


def unit_coordinates(point_index: int) -> Tuple[float, ...]:
    if point_index < 1 or point_index > POINT_COUNT:
        raise ValueError(f"surface_point_index_out_of_lock:{point_index}")
    return tuple(radical_inverse(point_index, base) for base in BASES)


def surface_parameters(point_index: int) -> Dict[str, float]:
    coords = unit_coordinates(point_index)
    out: Dict[str, float] = {}
    for (name, low, high), u in zip(DIMENSION_RANGES, coords):
        value = low + (high - low) * u
        if not (low < value < high):
            raise AssertionError(f"surface_parameter_not_strictly_interior:{point_index}:{name}:{value}")
        out[name] = value
    return out


def stress_assumptions(point_index: int) -> StressAssumptions:
    p = surface_parameters(point_index)
    return StressAssumptions(
        scenario_id=f"H{point_index:03d}",
        world_family="CONTINUOUS_SURFACE",
        assurance="ASSUMPTION_RANGE_ONLY",
        line_static_scale=p["line_static_scale"],
        relation_strength=p["relation_strength"],
        wind_effect_scale=p["wind_effect_scale"],
        bank_effect_scale=p["bank_effect_scale"],
        disruption_weight=p["disruption_weight"],
        shock_sigma=p["shock_sigma"],
        shock_temperature=p["shock_temperature"],
        disrupted_relation_strength=p["disrupted_relation_strength"],
    )


def quartile_for_dimension(point_index: int, dimension_name: str) -> int:
    names = [name for name, _, _ in DIMENSION_RANGES]
    if dimension_name not in names:
        raise ValueError(f"unknown_surface_dimension:{dimension_name}")
    dimension = names.index(dimension_name)
    u = unit_coordinates(point_index)[dimension]
    return min(4, int(u * 4.0) + 1)


def point_audit_record(point_index: int) -> dict:
    return {
        "point_index": point_index,
        "unit_coordinates": list(unit_coordinates(point_index)),
        **surface_parameters(point_index),
    }


def all_point_audit_records() -> list[dict]:
    return [point_audit_record(i) for i in range(1, POINT_COUNT + 1)]


def canonical_points_sha256() -> str:
    raw = json.dumps(
        all_point_audit_records(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_surface() -> None:
    if len(BASES) != 8 or len(DIMENSION_RANGES) != 8:
        raise AssertionError("continuous_surface_dimension_count_drift")
    records = all_point_audit_records()
    if len(records) != POINT_COUNT:
        raise AssertionError("continuous_surface_point_count_drift")
    coord_tuples = {tuple(x["unit_coordinates"]) for x in records}
    if len(coord_tuples) != POINT_COUNT:
        raise AssertionError("continuous_surface_duplicate_point")
    ids = [stress_assumptions(i).scenario_id for i in range(1, POINT_COUNT + 1)]
    if len(ids) != len(set(ids)):
        raise AssertionError("continuous_surface_duplicate_scenario_id")
    if canonical_points_sha256() != EXPECTED_CANONICAL_POINTS_SHA256:
        raise AssertionError("continuous_surface_canonical_points_hash_drift")


if __name__ == "__main__":
    validate_surface()
    print(json.dumps({
        "record": "KEIRIN_DT_CONTINUOUS_ASSUMPTION_SURFACE_POINTS_v1",
        "status": "DETERMINISTIC_ASSUMPTION_RANGE_ONLY",
        "point_count": POINT_COUNT,
        "canonical_points_sha256": canonical_points_sha256(),
        "points": all_point_audit_records(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
