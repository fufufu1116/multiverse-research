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

MUST_NOT_BE_VERIFIED_NUMERIC = {
    "BANK_WIND_EFFECT_SIZE",
    "LINE_EFFECT_SIZE",
    "LINE_BREAK_RATE",
    "HEAVY_TAIL_SHOCK",
    "MARKET_STRENGTH_BIAS",
}

def fail(msg: str) -> None:
    raise SystemExit(f"CALIBRATION_REGISTRY_FAIL: {msg}")

def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    fw = data["scientific_firewall"]
    if fw["ECON_HOLDOUT1000"] != "SEALED":
        fail("ECON_HOLDOUT1000 must remain SEALED")
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
    required = set(data["batch1_decision"]["parameters_that_must_remain_ranges_now"])
    if set(names) != required:
        fail("parameter inventory drift")

    for p in params:
        c = p["classification"]
        if c not in ALLOWED:
            fail(f"unknown evidence class for {p['parameter']}: {c}")
        if p["parameter"] in MUST_NOT_BE_VERIFIED_NUMERIC and c == "VERIFIED_REALITY":
            fail(f"{p['parameter']} cannot be VERIFIED_REALITY in Batch1")
        if c in {"ASSUMPTION_RANGE_ONLY", "DEFERRED_RESULT_DEPENDENT"}:
            policy = p["current_safe_value_policy"].lower()
            if "range" not in policy and "synthetic" not in policy and "stress" not in policy:
                fail(f"{p['parameter']} lacks explicit range/synthetic/stress policy")

    if data["batch1_decision"]["no_result_data_needed_for_next_step"] is not True:
        fail("next step must not require result data")

    print("DIGITAL_TWIN_REALITY_CALIBRATION_REGISTRY_PASS")

if __name__ == "__main__":
    main()
