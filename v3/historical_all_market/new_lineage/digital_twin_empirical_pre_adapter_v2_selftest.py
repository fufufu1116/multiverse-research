from __future__ import annotations

from collections import Counter

from digital_twin_empirical_pre_adapter_v2 import (
    TACTICAL,
    _load_v2,
    generate_empirical_joint_v2_bundle,
    model_pre_view_v2,
    realistic_pre_view_v2,
)
from digital_twin_v1 import world_joint_distribution


def run() -> None:
    params = _load_v2()
    if len(params["cells"]) != 15:
        raise AssertionError("v2_cell_count_drift")
    if max(float(x["identity_shrinkage"]) for x in params["cells"].values()) != 0.0:
        raise AssertionError("unexpected_v2_copula_shrinkage")

    a = generate_empirical_joint_v2_bundle(20260820, 0)
    b = generate_empirical_joint_v2_bundle(20260820, 0)
    if a != b:
        raise AssertionError("v2_not_deterministic")

    audit = realistic_pre_view_v2(a)
    model = model_pre_view_v2(a)
    if audit["field_size"] != 7 or model["field_size"] != 7:
        raise AssertionError("v2_standard7_drift")
    if audit["calibration_status"] != "CANDIDATE_SENSOR_JOINT_V2_NOT_REALITY_ADMISSION":
        raise AssertionError("v2_source_boundary_lost")
    if "NOT_REALITY_TRUTH" not in audit["tactical_dependence_source"]:
        raise AssertionError("v2_tactical_source_boundary_lost")
    for rider in audit["riders"]:
        if "rider" in rider or "name" in rider:
            raise AssertionError("v2_raw_identity_leaked")
        if rider.get("H_source") != "ASSUMPTION_UNMEASURED":
            raise AssertionError("v2_H_boundary_lost")
        if rider.get("line_source_class") != "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED":
            raise AssertionError("v2_line_boundary_lost")

    for world in ("W0", "W1", "W2", "W3", "W4"):
        truth = world_joint_distribution(a.race, world)
        if len(truth) != 210:
            raise AssertionError(f"v2_top3_support:{world}:{len(truth)}")
        if abs(sum(truth.values()) - 1.0) > 1e-10:
            raise AssertionError(f"v2_truth_mass:{world}")
        if any(x < 0.0 for x in truth.values()):
            raise AssertionError(f"v2_negative_truth:{world}")

    n = 1000
    band = Counter()
    class_count = Counter()
    style_count = Counter()
    for i in range(n):
        bundle = generate_empirical_joint_v2_bundle(20260820, i)
        pre = model_pre_view_v2(bundle)
        if pre["field_size"] != 7:
            raise AssertionError("v2_batch_field_size_drift")
        band[pre["race_band"]] += 1
        for rider in pre["riders"]:
            class_count[rider["class"]] += 1
            style_count[rider["style"]] += 1
            for field in TACTICAL:
                value = float(rider[field])
                if not 0.0 <= value <= 1.0:
                    raise AssertionError(f"v2_tactical_range:{field}:{value}")

    if set(band) != {"S", "A12", "A3"}:
        raise AssertionError(f"v2_band_support:{band}")
    if set(class_count) != {"S1", "S2", "A1", "A2", "A3"}:
        raise AssertionError(f"v2_class_support:{class_count}")
    if set(style_count) != {"逃", "両", "追"}:
        raise AssertionError(f"v2_style_support:{style_count}")

    print("DIGITAL_TWIN_EMPIRICAL_PRE_ADAPTER_V2_SELFTEST_PASS")


if __name__ == "__main__":
    run()
