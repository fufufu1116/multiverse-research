from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from digital_twin_empirical_pre_adapter_v1 import (
    PARAMS_PATH,
    generate_empirical_candidate_bundle,
    model_pre_view,
    realistic_pre_view,
)
from digital_twin_v1 import world_joint_distribution


def _close(actual: float, expected: float, tol: float, label: str) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label}:actual={actual}:expected={expected}:tol={tol}")


def run() -> None:
    params = json.loads(Path(PARAMS_PATH).read_text(encoding="utf-8"))

    # Determinism and explicit source labeling.
    a = generate_empirical_candidate_bundle(20260820, 0)
    b = generate_empirical_candidate_bundle(20260820, 0)
    if a != b:
        raise AssertionError("empirical_adapter_not_deterministic")

    audit = realistic_pre_view(a)
    model = model_pre_view(a)
    if audit.get("calibration_status") != "CANDIDATE_SENSOR_ENVELOPE_NOT_REALITY_ADMISSION":
        raise AssertionError("sensor_only_status_lost")
    if model.get("score_semantics") != "BAND_SCALED_MODEL_Z_FROM_SENSOR_ONLY_RAW_SCORE":
        raise AssertionError("model_score_semantics_lost")
    if audit.get("bank_source_class") != "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED":
        raise AssertionError("bank_assumption_boundary_lost")
    if audit.get("wind_source_class") != "ASSUMPTION_RANGE_NOT_SENSOR_CALIBRATED":
        raise AssertionError("wind_assumption_boundary_lost")
    for rider in audit["riders"]:
        if "score_model_z" not in rider:
            raise AssertionError("missing_model_z_audit_bridge")
        if rider.get("H_source") != "ASSUMPTION_UNMEASURED":
            raise AssertionError("H_unmeasured_boundary_lost")
        if "rider" in rider or "name" in rider:
            raise AssertionError("raw_identity_leaked")

    # Existing synthetic truth plumbing must remain probability coherent.
    for world in ("W0", "W1", "W2", "W3", "W4"):
        truth = world_joint_distribution(a.race, world)
        if len(truth) != 210:
            raise AssertionError(f"unexpected_top3_support:{world}:{len(truth)}")
        if abs(sum(truth.values()) - 1.0) > 1e-10:
            raise AssertionError(f"truth_mass_failed:{world}")
        if any(x < 0.0 for x in truth.values()):
            raise AssertionError(f"negative_truth_probability:{world}")

    n_races = 3000
    band = Counter()
    class_by_band = defaultdict(Counter)
    style_by_band = defaultdict(Counter)
    score_sum_by_band = Counter()
    score_n_by_band = Counter()
    tactical_sum = defaultdict(Counter)
    tactical_n = Counter()

    for i in range(n_races):
        bundle = generate_empirical_candidate_bundle(20260820, i)
        audit_pre = realistic_pre_view(bundle)
        model_pre = model_pre_view(bundle)
        if audit_pre["field_size"] != 7 or model_pre["field_size"] != 7:
            raise AssertionError("standard7_field_size_drift")
        bnd = audit_pre["race_band"]
        band[bnd] += 1
        for audit_rider, model_rider in zip(audit_pre["riders"], model_pre["riders"]):
            class_by_band[bnd][audit_rider["class"]] += 1
            style = audit_rider["style"]
            style_by_band[bnd][style] += 1
            score_sum_by_band[bnd] += float(audit_rider["score"])
            score_n_by_band[bnd] += 1
            for field in ("B", "S", "nige", "makuri", "sashi", "mark"):
                value = float(model_rider[field])
                if not (0.0 <= value <= 1.0):
                    raise AssertionError(f"tactical_rate_out_of_range:{style}:{field}:{value}")
                tactical_sum[style][field] += value
            tactical_n[style] += 1

    for bnd, expected in params["band_probs"].items():
        _close(band[bnd] / n_races, float(expected), 0.03, f"band:{bnd}")

    for bnd, expected_classes in params["class_probs"].items():
        total = sum(class_by_band[bnd].values())
        for cls, expected in expected_classes.items():
            _close(class_by_band[bnd][cls] / total, float(expected), 0.03, f"class:{bnd}:{cls}")

    for bnd, expected_styles in params["style_probs"].items():
        total = sum(style_by_band[bnd].values())
        for style, expected in expected_styles.items():
            _close(style_by_band[bnd][style] / total, float(expected), 0.025, f"style:{bnd}:{style}")

    for bnd, score_spec in params["score_hierarchy"].items():
        observed = score_sum_by_band[bnd] / score_n_by_band[bnd]
        _close(observed, float(score_spec["race_mean_mu"]), 0.75, f"score_center:{bnd}")

    for style, fields in params["tactical_zero_inflated_beta"].items():
        for field, spec in fields.items():
            expected = (1.0 - float(spec["p0"])) * float(spec["alpha"]) / (
                float(spec["alpha"]) + float(spec["beta"])
            )
            observed = tactical_sum[style][field] / tactical_n[style]
            _close(observed, expected, 0.025, f"tactical:{style}:{field}")

    print("DIGITAL_TWIN_EMPIRICAL_PRE_ADAPTER_SELFTEST_PASS")


if __name__ == "__main__":
    run()
