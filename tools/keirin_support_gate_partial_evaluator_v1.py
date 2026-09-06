#!/usr/bin/env python3
"""Research-only partial evaluator for the frozen Keirin support adequacy gate.

This evaluator deliberately does NOT invent the undefined calendar-block granularity.
It computes only unambiguous PRE-only gate dimensions from confirmed support receipts.
It may return FAIL when a known dimension fails, but it MUST NOT return PASS while
calendar-block evaluation remains undefined/UNKNOWN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections import Counter, defaultdict

PRESPEC = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_RIDER_CIRCUMFERENCE_SUPPORT_ADEQUACY_GATE_PRESPEC_20260903_v1.json")
PRESPEC_BLOB = "107bc07bbaca5b73351ae190ca368b9b57702077"
FORBIDDEN_TRUE = {
    "result_accessed", "target_result_accessed", "payout_accessed",
    "odds_accessed", "human_forecast_accessed"
}


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bucket(circ) -> str:
    x = float(circ)
    if abs(x - 333.0) < 1e-6 or abs(x - 333.33) < 0.02:
        return "333_OR_333_33"
    if abs(x - 400.0) < 1e-6:
        return "400"
    raise ValueError(f"FAIL_CLOSED_UNSUPPORTED_CIRCUMFERENCE_{x}")


def validate_prespec() -> dict:
    got = git_blob(PRESPEC)
    if got != PRESPEC_BLOB:
        raise ValueError(f"FAIL_CLOSED_GATE_PRESPEC_BLOB_DRIFT_{got}")
    spec = load_json(PRESPEC)
    if spec.get("status") != "PRE_RESULT_SUPPORT_GATE_FROZEN_NO_OUTCOME_ACCESS":
        raise ValueError("FAIL_CLOSED_GATE_PRESPEC_STATUS")
    return spec


def extract_receipt(receipt: dict) -> tuple[str, list[dict]]:
    for flag in FORBIDDEN_TRUE:
        if receipt.get(flag) is True:
            raise ValueError(f"FAIL_CLOSED_FORBIDDEN_{flag}")
    if receipt.get("result_join_authorized") is not False:
        raise ValueError("FAIL_CLOSED_RESULT_JOIN_AUTHORITY")
    if receipt.get("formula_fit_authorized") is not False:
        raise ValueError("FAIL_CLOSED_FORMULA_AUTHORITY")

    rider = receipt.get("rider") or {}
    reg = str(rider.get("official_registration_number") or "")
    if not re.fullmatch(r"\d{6}", reg):
        raise ValueError("FAIL_CLOSED_REGISTRATION")
    decision = receipt.get("support_decision") or {}
    if decision.get("cross_circumference_supported_rider") is not True:
        raise ValueError("FAIL_CLOSED_NOT_CONFIRMED_CROSS_CIRC_RECEIPT")
    if decision.get("result_needed_for_support_decision") is not False:
        raise ValueError("FAIL_CLOSED_RESULT_NEEDED")

    raw = receipt.get("supported_rows")
    rows = list(raw.values()) if isinstance(raw, dict) else raw
    if not isinstance(rows, list) or not rows:
        raise ValueError("FAIL_CLOSED_SUPPORTED_ROWS")

    out = []
    for r in rows:
        if not isinstance(r, dict) or r.get("valid_pre_row_for_support") is not True:
            raise ValueError("FAIL_CLOSED_INVALID_PRE_ROW")
        if str(r.get("registration_number") or "") != reg:
            raise ValueError("FAIL_CLOSED_ROW_REGISTRATION_BINDING")
        if r.get("day") != "Day1":
            raise ValueError("FAIL_CLOSED_NON_DAY1")
        date = str(r.get("race_date") or "")
        venue = str(r.get("venue") or "").strip()
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date) or not venue:
            raise ValueError("FAIL_CLOSED_EVENT_BINDING")
        rn, cn = int(r.get("race_no")), int(r.get("car_no"))
        if not (1 <= rn <= 12 and 1 <= cn <= 9):
            raise ValueError("FAIL_CLOSED_RACE_OR_CAR_NO")
        out.append({
            "registration_number": reg,
            "circumference_bucket": bucket(r.get("circumference_m")),
            "race_date": date,
            "venue": venue,
            "race_no": rn,
            "car_no": cn,
        })

    if {x["circumference_bucket"] for x in out} != {"333_OR_333_33", "400"}:
        raise ValueError("FAIL_CLOSED_RECEIPT_NOT_CROSS_CIRC")
    return reg, out


def evaluate(receipts: list[dict]) -> dict:
    spec = validate_prespec()
    minimum = spec["minimum_gate"]

    unique_rows: dict[tuple, dict] = {}
    qualified_regs = set()
    for receipt in receipts:
        reg, rows = extract_receipt(receipt)
        qualified_regs.add(reg)
        for r in rows:
            key = (r["registration_number"], r["circumference_bucket"], r["race_date"], r["venue"], r["race_no"], r["car_no"])
            unique_rows[key] = r

    rows = list(unique_rows.values())
    venue_counts = Counter(r["venue"] for r in rows)
    rider_counts = Counter(r["registration_number"] for r in rows)
    venues_by_bucket = defaultdict(set)
    for r in rows:
        venues_by_bucket[r["circumference_bucket"]].add(r["venue"])

    n_rows = len(rows)
    unique_riders = len(qualified_regs)
    max_venue_share = max(venue_counts.values()) / n_rows if n_rows else 0.0
    max_rider_share = max(rider_counts.values()) / n_rows if n_rows else 0.0
    mapping_rate = 1.0 if n_rows and all(re.fullmatch(r"\d{6}", r["registration_number"]) for r in rows) else 0.0

    checks = {
        "unique_cross_circumference_supported_riders": {
            "value": unique_riders,
            "threshold": minimum["unique_cross_circumference_supported_riders"],
            "status": "PASS" if unique_riders >= minimum["unique_cross_circumference_supported_riders"] else "FAIL",
        },
        "minimum_supported_rider_race_rows": {
            "value": n_rows,
            "threshold": minimum["minimum_supported_rider_race_rows"],
            "status": "PASS" if n_rows >= minimum["minimum_supported_rider_race_rows"] else "FAIL",
        },
        "distinct_333_or_333_33_venues": {
            "value": len(venues_by_bucket["333_OR_333_33"]),
            "threshold": minimum["minimum_distinct_development_venues_per_circumference"],
            "status": "PASS" if len(venues_by_bucket["333_OR_333_33"]) >= minimum["minimum_distinct_development_venues_per_circumference"] else "FAIL",
        },
        "distinct_400_venues": {
            "value": len(venues_by_bucket["400"]),
            "threshold": minimum["minimum_distinct_development_venues_per_circumference"],
            "status": "PASS" if len(venues_by_bucket["400"]) >= minimum["minimum_distinct_development_venues_per_circumference"] else "FAIL",
        },
        "max_single_venue_share": {
            "value": max_venue_share,
            "threshold": minimum["maximum_single_venue_share_of_supported_rows"],
            "status": "PASS" if max_venue_share <= minimum["maximum_single_venue_share_of_supported_rows"] else "FAIL",
        },
        "max_single_rider_share": {
            "value": max_rider_share,
            "threshold": minimum["maximum_single_rider_share_of_supported_rows"],
            "status": "PASS" if max_rider_share <= minimum["maximum_single_rider_share_of_supported_rows"] else "FAIL",
        },
        "official_registration_mapping_rate": {
            "value": mapping_rate,
            "threshold": minimum["official_registration_number_mapping_rate_for_supported_rows"],
            "status": "PASS" if mapping_rate == minimum["official_registration_number_mapping_rate_for_supported_rows"] else "FAIL",
        },
        "calendar_blocks_333_or_333_33": {
            "value": None,
            "threshold": minimum["minimum_distinct_calendar_blocks_per_circumference"],
            "status": "UNKNOWN_UNDEFINED_FROZEN_GRANULARITY",
        },
        "calendar_blocks_400": {
            "value": None,
            "threshold": minimum["minimum_distinct_calendar_blocks_per_circumference"],
            "status": "UNKNOWN_UNDEFINED_FROZEN_GRANULARITY",
        },
    }

    known_failures = sorted(k for k, v in checks.items() if v["status"] == "FAIL")
    unknowns = sorted(k for k, v in checks.items() if str(v["status"]).startswith("UNKNOWN"))
    if known_failures:
        overall = "FAIL_KNOWN_DIMENSION"
    else:
        overall = "INDETERMINATE_CALENDAR_BLOCK_GRANULARITY_UNDEFINED"

    return {
        "record": "KEIRIN_SUPPORT_GATE_PARTIAL_EVALUATION_v1",
        "status": overall,
        "scope": "RESEARCH_PRE_ONLY_PARTIAL_GATE_DIAGNOSTIC_NO_PASS_AUTHORITY",
        "confirmed_receipt_count": len(receipts),
        "unique_supported_rows_after_event_key_dedup": n_rows,
        "checks": checks,
        "known_failures": known_failures,
        "unknown_dimensions": unknowns,
        "calendar_block_policy": "DO_NOT_INVENT_GRANULARITY; FULL_GATE_PASS_PROHIBITED_WHILE_UNDEFINED",
        "full_gate_pass_authorized": False,
        "support_increment_authorized_now": 0,
        "result_accessed": False,
        "result_join_authorized": False,
        "formula_fit_authorized": False,
        "main_or_runtime_mutation": False,
    }


def selftest() -> dict:
    base = {
        "rider": {"name": "テスト", "official_registration_number": "012345"},
        "supported_rows": {
            "333m": {"race_date": "2099-01-01", "venue": "防府", "circumference_m": 333, "day": "Day1", "race_no": 1, "car_no": 1, "registration_number": "012345", "valid_pre_row_for_support": True},
            "400m": {"race_date": "2099-01-02", "venue": "川崎", "circumference_m": 400, "day": "Day1", "race_no": 2, "car_no": 2, "registration_number": "012345", "valid_pre_row_for_support": True},
        },
        "support_decision": {"cross_circumference_supported_rider": True, "result_needed_for_support_decision": False},
        "result_accessed": False, "target_result_accessed": False, "payout_accessed": False,
        "odds_accessed": False, "human_forecast_accessed": False,
        "result_join_authorized": False, "formula_fit_authorized": False,
    }
    out = evaluate([base])
    tests = {
        "one_rider_two_rows_known_fail": out["status"] == "FAIL_KNOWN_DIMENSION",
        "calendar_remains_unknown": len(out["unknown_dimensions"]) == 2,
        "never_authorizes_full_pass": out["full_gate_pass_authorized"] is False,
        "known_counts_exact": out["checks"]["unique_cross_circumference_supported_riders"]["value"] == 1 and out["checks"]["minimum_supported_rider_race_rows"]["value"] == 2,
    }
    return {"record": "KEIRIN_SUPPORT_GATE_PARTIAL_EVALUATOR_SELFTEST_v1", "status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "network_access": False, "result_accessed": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("evaluate")
    p.add_argument("receipts", nargs="+")
    p.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2
    try:
        out = evaluate([load_json(pathlib.Path(x)) for x in a.receipts])
        text = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if a.out:
            pathlib.Path(a.out).write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except Exception as exc:
        out = {"record": "KEIRIN_SUPPORT_GATE_PARTIAL_EVALUATION_v1", "status": "FAIL_CLOSED_EVALUATOR_ERROR", "fatal_error": f"{type(exc).__name__}: {str(exc)[:500]}", "full_gate_pass_authorized": False, "support_increment_authorized_now": 0, "result_accessed": False}
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
