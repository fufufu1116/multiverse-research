#!/usr/bin/env python3
"""Fail-closed conformance checks for the Digital Twin reality calibration registry.

This validates governance semantics only. It does not prove real-world predictive validity.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parent / "governance" / "DIGITAL_TWIN_REALITY_CALIBRATION_REGISTRY_v1.json"

ALLOWED = {
    "VERIFIED_REALITY",
    "VERIFIED_QUALITATIVE_ONLY",
    "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "MEASURABLE_SCHEDULE_NOT_YET_ESTIMATED",
    "ASSUMPTION_RANGE_ONLY",
    "DEFERRED_RESULT_DEPENDENT",
    "UNVERIFIED",
}

# Batch-1 classification is pinned parameter-by-parameter. A later reclassification is a
# deliberate governance change, not something this validator silently accepts.
EXPECTED_CLASSIFICATION = {
    "RACE_BAND_FREQUENCY": "MEASURABLE_SCHEDULE_NOT_YET_ESTIMATED",
    "WITHIN_BAND_CLASS_FREQUENCY": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "LINE_SHAPE_FREQUENCY": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "STYLE_BY_LINE_POSITION": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "B_H_S_DISTRIBUTION": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "NIGE_MAKURI_SASHI_MARK_DISTRIBUTION": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "BANK_LENGTH_FREQUENCY": "MEASURABLE_SCHEDULE_NOT_YET_ESTIMATED",
    "WIND_DISTRIBUTION": "MEASURABLE_PRE_NOT_YET_ESTIMATED",
    "BANK_WIND_EFFECT_SIZE": "ASSUMPTION_RANGE_ONLY",
    "LINE_EFFECT_SIZE": "ASSUMPTION_RANGE_ONLY",
    "LINE_BREAK_RATE": "DEFERRED_RESULT_DEPENDENT",
    "HEAVY_TAIL_SHOCK": "ASSUMPTION_RANGE_ONLY",
    "MARKET_STRENGTH_BIAS": "DEFERRED_RESULT_DEPENDENT",
}


def fail(msg: str) -> None:
    raise SystemExit(f"CALIBRATION_REGISTRY_FAIL: {msg}")


def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    fw = data["scientific_firewall"]
    if fw["ECON_HOLDOUT1000"] != "SEALED":
        fail("ECON_HOLDOUT1000 must remain SEALED")
    if fw["DEV2000_C_new_lineage_rescue"] != "PROHIBITED":
        fail("DEV2000 C new-lineage rescue must remain prohibited")
    if fw["same_lineage_B_C_rescue_tuning"] != "PROHIBITED":
        fail("same-lineage B/C rescue tuning must remain prohibited")
    if fw["scientific_segment_c_scoring_count"] != 0:
        fail("scientific segment C scoring count changed")
    if fw["new_untouched_validation_opened"] is not False:
        fail("untouched validation must remain unopened")
    if fw["result_payout_access_authorized"] is not False:
        fail("RESULT/PAYOUT access must remain unauthorized")

    params = data["parameters"]
    names = [p["parameter"] for p in params]
    if len(names) != len(set(names)):
        fail("duplicate parameter")

    expected_names = set(EXPECTED_CLASSIFICATION)
    if set(names) != expected_names:
        fail("parameter inventory drift")

    required = set(data["batch1_decision"]["parameters_that_must_remain_ranges_now"])
    if required != expected_names:
        fail("batch1 must-remain-ranges inventory drift")

    for p in params:
        name = p["parameter"]
        classification = p["classification"]
        if classification not in ALLOWED:
            fail(f"unknown evidence class for {name}: {classification}")
        expected = EXPECTED_CLASSIFICATION[name]
        if classification != expected:
            fail(
                f"classification drift for {name}: expected {expected}, got {classification}"
            )
        if classification in {"ASSUMPTION_RANGE_ONLY", "DEFERRED_RESULT_DEPENDENT"}:
            policy = p["current_safe_value_policy"].lower()
            if "range" not in policy and "synthetic" not in policy and "stress" not in policy:
                fail(f"{name} lacks explicit range/synthetic/stress policy")

    if data["batch1_decision"]["no_result_data_needed_for_next_step"] is not True:
        fail("next step must not require result data")

    print("DIGITAL_TWIN_REALITY_CALIBRATION_REGISTRY_PASS")


if __name__ == "__main__":
    main()
