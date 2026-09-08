#!/usr/bin/env python3
"""PRE-only formal support finalizer for the locked 35-rider Keirin conversion front.

Inputs are local JSON artifacts only. This tool performs no network access and
must never inspect RESULT, PAYOUT, ODDS, or human forecasts.

It validates final Day1 PRE rows against:
- the deterministic 1..35 conversion order,
- the prebuilt 35-rider conversion matrix,
- the central PRE-cutoff witness registry.

It then emits support receipts in frozen priority order, skips fail-closed
candidates, and stops immediately after 29 new riders PASS.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from collections import Counter, defaultdict
from typing import Any

TARGET_NEW_PASS = 29
BASELINE_RIDERS = 1
BASELINE_ROWS = 2
TARGET_RIDERS = 30
TARGET_ROWS = 60
REG_RE = re.compile(r"\d{6}$")


class FinalizerError(ValueError):
    pass


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path: str | Path, obj: Any) -> None:
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def parse_dt(value: str, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except Exception as exc:
        raise FinalizerError(f"invalid_{field}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise FinalizerError(f"timezone_required_{field}")
    return dt


def circumference_bucket(value: Any) -> str:
    x = float(value)
    if abs(x - 400.0) < 1e-6:
        return "400"
    if abs(x - 333.0) < 1.0 or abs(x - 333.33) < 1.0:
        return "333_OR_333_33"
    raise FinalizerError(f"unsupported_circumference:{value}")


def validate_sha256(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", str(value or "")):
        raise FinalizerError("invalid_source_sha256")


def candidate_key(reg: str, date: str, venue: str) -> tuple[str, str, str]:
    return str(reg), str(date), str(venue)


def index_locked_inputs(order: dict, matrix: dict, registry: dict) -> tuple[list[dict], dict, dict]:
    ordered = list(order.get("ordered_candidates") or [])
    if len(ordered) != 35:
        raise FinalizerError(f"expected_35_ordered_candidates_got_{len(ordered)}")
    priorities = [int(x.get("priority")) for x in ordered]
    if priorities != list(range(1, 36)):
        raise FinalizerError("priority_sequence_not_exact_1_35")

    matrix_rows = list(matrix.get("rows") or [])
    if len(matrix_rows) != 35:
        raise FinalizerError(f"expected_35_matrix_rows_got_{len(matrix_rows)}")
    by_reg_matrix = {}
    for row in matrix_rows:
        reg = str(row.get("official_registration_number") or "")
        if not REG_RE.fullmatch(reg) or reg in by_reg_matrix:
            raise FinalizerError("matrix_registration_invalid_or_duplicate")
        by_reg_matrix[reg] = row

    entries = list(registry.get("entries") or [])
    by_key_registry = {}
    for entry in entries:
        reg = str(entry.get("official_registration_number") or "")
        event = str(entry.get("event") or "")
        if not REG_RE.fullmatch(reg) or "_" not in event:
            continue
        venue, date = event.rsplit("_", 1)
        key = candidate_key(reg, date, venue)
        if key in by_key_registry:
            raise FinalizerError(f"duplicate_registry_candidate:{key}")
        by_key_registry[key] = entry

    for cand in ordered:
        reg = str(cand.get("registration") or "")
        if reg not in by_reg_matrix:
            raise FinalizerError(f"order_registration_missing_from_matrix:{reg}")
        future = cand.get("future") or {}
        key = candidate_key(reg, future.get("date"), future.get("venue"))
        entry = by_key_registry.get(key)
        if not entry:
            raise FinalizerError(f"prebuilt_registry_entry_missing:{key}")
        if entry.get("closure_status") != "OPEN_PRE_CUTOFF_READINESS":
            raise FinalizerError(f"prebuilt_registry_entry_not_open:{key}")

    return ordered, by_reg_matrix, by_key_registry


def validate_future_pre_row(
    cand: dict,
    matrix_row: dict,
    registry_entry: dict,
    row: dict,
) -> tuple[bool, str | None]:
    reg = str(cand["registration"])
    future = cand["future"]
    try:
        if str(row.get("official_registration_number") or "") != reg:
            return False, "REGISTRATION_MISMATCH"
        if str(row.get("rider_name") or "") != str(cand.get("rider_name") or ""):
            return False, "RIDER_NAME_MISMATCH"
        if str(row.get("race_date") or "") != str(future.get("date") or ""):
            return False, "DATE_MISMATCH"
        if str(row.get("venue") or "") != str(future.get("venue") or ""):
            return False, "VENUE_MISMATCH"
        if str(row.get("day") or "") != "Day1":
            return False, "NOT_DAY1"
        if circumference_bucket(row.get("circumference_m")) != str(future.get("circumference_bucket")):
            return False, "CIRCUMFERENCE_MISMATCH"
        race_no = int(row.get("race_no"))
        car_no = int(row.get("car_no"))
        if not (1 <= race_no <= 12):
            return False, "INVALID_RACE_NO"
        if not (1 <= car_no <= 9):
            return False, "INVALID_CAR_NO"
        if not str(row.get("class") or "").strip():
            return False, "MISSING_CLASS"
        if str(row.get("style") or "") not in {"逃", "追", "両"}:
            return False, "INVALID_STYLE"
        if not str(row.get("source_url") or "").startswith(("https://", "http://")):
            return False, "MISSING_SOURCE_URL"
        validate_sha256(str(row.get("source_sha256") or ""))
        captured = parse_dt(str(row.get("captured_at_jst") or ""), "captured_at_jst")
        cutoff = parse_dt(str(row.get("trusted_pit_cutoff_jst") or ""), "trusted_pit_cutoff_jst")
        if captured > cutoff:
            return False, "CAPTURE_AFTER_CUTOFF"
        if registry_entry.get("closure_status") != "OPEN_PRE_CUTOFF_READINESS":
            return False, "REGISTRY_NOT_OPEN"
        if registry_entry.get("prospective_day1_pre_membership") != "PENDING_EXACT_POSITIVE_DAY1_RACECARD":
            return False, "REGISTRY_NOT_PENDING_FINAL_PRE"
        historical = matrix_row.get("historical_row") or {}
        if circumference_bucket(historical.get("circumference_m")) == circumference_bucket(row.get("circumference_m")):
            return False, "NOT_CROSS_CIRCUMFERENCE"
    except (ValueError, TypeError, FinalizerError) as exc:
        return False, f"INVALID_PRE_ROW:{type(exc).__name__}:{str(exc)[:120]}"
    return True, None


def build_receipt(cand: dict, matrix_row: dict, row: dict) -> dict:
    reg = str(cand["registration"])
    historical = deepcopy(matrix_row["historical_row"])
    historical["registration_number"] = reg
    historical["valid_pre_row_for_support"] = True

    future_row = {
        "race_date": str(row["race_date"]),
        "venue": str(row["venue"]),
        "circumference_m": float(row["circumference_m"]),
        "day": "Day1",
        "race_no": int(row["race_no"]),
        "car_no": int(row["car_no"]),
        "class": str(row["class"]),
        "style": str(row["style"]),
        "source_url": str(row["source_url"]),
        "source_sha256": str(row["source_sha256"]),
        "captured_at_jst": str(row["captured_at_jst"]),
        "trusted_pit_cutoff_jst": str(row["trusted_pit_cutoff_jst"]),
        "registration_number": reg,
        "valid_pre_row_for_support": True,
        "pre_evidence_role": "FINAL_DAY1_PRE_SAME_RACE_WITNESS",
    }

    return {
        "record": f"KEIRIN_CROSS_CIRCUMFERENCE_SUPPORT_RECEIPT_{reg}",
        "status": "CONFIRMED_ONE_RIDER_CROSS_CIRCUMFERENCE_SUPPORT_PRE_ONLY",
        "scope": "RESEARCH_PRE_ONLY_SUPPORT_ACCOUNTING_NO_RESULT_NO_MODEL_FIT",
        "support_definition": "One official registration number with at least one valid PRE race in each of the 333/333.33m and 400m buckets.",
        "rider": {
            "name": str(cand["rider_name"]),
            "official_registration_number": reg,
            "identity_key_status": "DETERMINISTIC_OFFICIAL_REGISTRATION_NUMBER",
        },
        "supported_rows": {
            "historical": historical,
            "future": future_row,
        },
        "support_decision": {
            "same_official_registration_number_across_333_and_400": True,
            "both_rows_valid_pre": True,
            "prospective_same_race_assignment_observed_before_cutoff": True,
            "cross_circumference_supported_rider": True,
            "confirmed_unique_rider_increment_now": 1,
            "confirmed_supported_rider_race_rows_increment_now": 2,
            "result_needed_for_support_decision": False,
        },
        "result_accessed": False,
        "target_result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "human_forecast_accessed": False,
        "current_profile_nonidentity_fields_used_as_features": False,
        "result_join_authorized": False,
        "formula_fit_authorized": False,
        "s0_mutation": False,
        "main_or_runtime_mutation": False,
    }


def finalize(order: dict, matrix: dict, registry: dict, future_pre: dict) -> dict:
    ordered, by_reg_matrix, by_key_registry = index_locked_inputs(order, matrix, registry)
    future_rows = list(future_pre.get("rows") or [])
    by_key_pre = {}
    for row in future_rows:
        key = candidate_key(
            str(row.get("official_registration_number") or ""),
            str(row.get("race_date") or ""),
            str(row.get("venue") or ""),
        )
        if key in by_key_pre:
            raise FinalizerError(f"duplicate_future_pre_row:{key}")
        by_key_pre[key] = row

    updated_registry = deepcopy(registry)
    updated_entries = list(updated_registry.get("entries") or [])
    updated_by_key = {}
    for entry in updated_entries:
        event = str(entry.get("event") or "")
        reg = str(entry.get("official_registration_number") or "")
        if "_" in event and REG_RE.fullmatch(reg):
            venue, date = event.rsplit("_", 1)
            updated_by_key[candidate_key(reg, date, venue)] = entry

    receipts = []
    decisions = []
    venue_counts = Counter()
    rider_counts = Counter()
    venues_by_bucket = defaultdict(set)

    # Baseline known receipt contributes two rows but is not recreated here.
    baseline_rows = list(future_pre.get("baseline_supported_rows") or [])
    for row in baseline_rows:
        venue_counts[str(row["venue"])] += 1
        rider_counts[str(row["registration_number"])] += 1
        venues_by_bucket[circumference_bucket(row["circumference_m"])].add(str(row["venue"]))

    for cand in ordered:
        if len(receipts) >= TARGET_NEW_PASS:
            decisions.append({
                "priority": cand["priority"],
                "registration": cand["registration"],
                "rider_name": cand["rider_name"],
                "status": "NOT_PROCESSED_STOP_AFTER_29_NEW_PASS",
            })
            continue

        reg = str(cand["registration"])
        future = cand["future"]
        key = candidate_key(reg, future["date"], future["venue"])
        matrix_row = by_reg_matrix[reg]
        registry_entry = by_key_registry[key]
        row = by_key_pre.get(key)

        if row is None:
            decisions.append({
                "priority": cand["priority"],
                "registration": reg,
                "rider_name": cand["rider_name"],
                "status": "FAIL_CLOSED",
                "reason": "FINAL_DAY1_PRE_ROW_MISSING",
            })
            continue

        ok, reason = validate_future_pre_row(cand, matrix_row, registry_entry, row)
        if not ok:
            decisions.append({
                "priority": cand["priority"],
                "registration": reg,
                "rider_name": cand["rider_name"],
                "status": "FAIL_CLOSED",
                "reason": reason,
            })
            continue

        receipt = build_receipt(cand, matrix_row, row)
        receipts.append(receipt)
        decisions.append({
            "priority": cand["priority"],
            "registration": reg,
            "rider_name": cand["rider_name"],
            "status": "PASS_FORMAL_SUPPORT",
            "new_pass_index": len(receipts),
        })

        # Update prebuilt registry entry deterministically.
        u = updated_by_key[key]
        u.update({
            "race_no": int(row["race_no"]),
            "car_no": int(row["car_no"]),
            "source": str(row.get("source") or "FINAL_DAY1_PRE"),
            "source_url_or_artifact": str(row["source_url"]),
            "captured_at_jst": str(row["captured_at_jst"]),
            "trusted_pit_cutoff_jst": str(row["trusted_pit_cutoff_jst"]),
            "source_sha256": str(row["source_sha256"]),
            "prospective_day1_pre_membership": "PASS",
            "official_same_race_positive": "PASS",
            "provenance_status": "PASS",
            "closure_status": "CLOSED_POSITIVE_PRE_CUTOFF",
            "formal_support_increment": 1,
        })

        for support_row in receipt["supported_rows"].values():
            venue_counts[str(support_row["venue"])] += 1
            rider_counts[reg] += 1
            venues_by_bucket[circumference_bucket(support_row["circumference_m"])].add(str(support_row["venue"]))

    new_pass = len(receipts)
    cumulative_riders = BASELINE_RIDERS + new_pass
    cumulative_rows = BASELINE_ROWS + 2 * new_pass
    total_counted_rows = sum(venue_counts.values())
    max_venue_count = max(venue_counts.values(), default=0)
    max_rider_count = max(rider_counts.values(), default=0)
    max_venue_share = (max_venue_count / total_counted_rows) if total_counted_rows else None
    max_rider_share = (max_rider_count / total_counted_rows) if total_counted_rows else None

    return {
        "record": "KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v1",
        "status": (
            "TARGET_30R_60ROWS_REACHED_PRE_ONLY"
            if new_pass == TARGET_NEW_PASS
            else "TARGET_NOT_REACHED_FAIL_CLOSED"
        ),
        "new_pass_riders": new_pass,
        "cumulative_riders": cumulative_riders,
        "cumulative_rows": cumulative_rows,
        "target_riders": TARGET_RIDERS,
        "target_rows": TARGET_ROWS,
        "stopped_after_29_new_pass": new_pass == TARGET_NEW_PASS,
        "decisions": decisions,
        "receipts": receipts,
        "updated_witness_registry": updated_registry,
        "unambiguous_gate_diagnostics": {
            "max_single_venue_share_global": max_venue_share,
            "max_single_venue_share_threshold": 0.60,
            "max_single_venue_share_status": (
                "PASS" if max_venue_share is not None and max_venue_share <= 0.60 else "FAIL"
            ),
            "max_single_rider_share_global": max_rider_share,
            "max_single_rider_share_threshold": 0.10,
            "max_single_rider_share_status": (
                "PASS" if max_rider_share is not None and max_rider_share <= 0.10 else "FAIL"
            ),
            "distinct_venues_by_circumference": {
                k: sorted(v) for k, v in venues_by_bucket.items()
            },
            "calendar_blocks": "UNKNOWN_PENDING_ADOPTED_PR177_DEFINITION",
        },
        "hard_boundaries": {
            "result_accessed": False,
            "payout_accessed": False,
            "odds_accessed": False,
            "formula_fit_authorized": False,
            "runtime": False,
        },
    }


def selftest() -> dict:
    # Synthetic 35-candidate fixture. No real race or outcome data.
    ordered = []
    matrix_rows = []
    registry_entries = []
    future_rows = []
    baseline = [
        {"registration_number":"900001","venue":"V400_BASE","circumference_m":400},
        {"registration_number":"900001","venue":"V333_BASE","circumference_m":333},
    ]

    for i in range(1, 36):
        reg = f"{100000+i:06d}"
        venue_future = "F333_A" if i <= 18 else "F333_B"
        future_date = "2099-01-10"
        ordered.append({
            "priority": i,
            "rider_name": f"R{i}",
            "registration": reg,
            "historical": {
                "date":"2099-01-01","venue":("H400_A" if i % 2 else "H400_B"),
                "circumference_m":400,"race_no":1,"car_no":1,
            },
            "future": {
                "date": future_date,
                "venue": venue_future,
                "circumference_bucket":"333_OR_333_33",
            },
        })
        matrix_rows.append({
            "rider_name": f"R{i}",
            "official_registration_number": reg,
            "historical_row": {
                "race_date":"2099-01-01",
                "venue":("H400_A" if i % 2 else "H400_B"),
                "circumference_m":400,
                "day":"Day1","race_no":1,"car_no":1,
                "class":"S1","style":"追",
                "source_url":"https://example.invalid/historical",
            },
        })
        registry_entries.append({
            "event":f"{venue_future}_{future_date}",
            "rider":f"R{i}",
            "official_registration_number":reg,
            "race_no":None,"car_no":None,"source":None,
            "source_url_or_artifact":None,"captured_at_jst":None,
            "trusted_pit_cutoff_jst":None,"source_sha256":None,
            "prospective_day1_pre_membership":"PENDING_EXACT_POSITIVE_DAY1_RACECARD",
            "official_same_race_positive":"PENDING","provenance_status":"PENDING",
            "closure_status":"OPEN_PRE_CUTOFF_READINESS","formal_support_increment":0,
        })
        future_rows.append({
            "rider_name":f"R{i}","official_registration_number":reg,
            "race_date":future_date,"venue":venue_future,"circumference_m":333,
            "day":"Day1","race_no":1+(i%10),"car_no":1+(i%7),
            "class":"S1","style":"追",
            "source":"SYNTHETIC","source_url":"https://example.invalid/future",
            "captured_at_jst":"2099-01-09T12:00:00+09:00",
            "trusted_pit_cutoff_jst":"2099-01-10T08:00:00+09:00",
            "source_sha256":hashlib.sha256(f"row{i}".encode()).hexdigest(),
        })

    order = {"ordered_candidates":ordered}
    matrix = {"rows":matrix_rows}
    registry = {"entries":registry_entries}
    manifest = {"rows":future_rows, "baseline_supported_rows":baseline}

    all_pass = finalize(order,matrix,registry,manifest)
    if all_pass["new_pass_riders"] != 29 or not all_pass["stopped_after_29_new_pass"]:
        raise AssertionError("all-pass stop-after-29 failed")

    # First six fail: remaining 29 must still reach target.
    six_fail = deepcopy(manifest)
    six_fail["rows"] = [r for r in six_fail["rows"] if int(r["official_registration_number"]) > 100006]
    out6 = finalize(order,matrix,registry,six_fail)
    if out6["new_pass_riders"] != 29:
        raise AssertionError("six-failure margin failed")

    # First seven fail: only 28 remain, target must not be reached.
    seven_fail = deepcopy(manifest)
    seven_fail["rows"] = [r for r in seven_fail["rows"] if int(r["official_registration_number"]) > 100007]
    out7 = finalize(order,matrix,registry,seven_fail)
    if out7["new_pass_riders"] != 28 or out7["status"] != "TARGET_NOT_REACHED_FAIL_CLOSED":
        raise AssertionError("seven-failure shortfall failed")

    # Late capture must fail closed.
    late = deepcopy(manifest)
    late["rows"][0]["captured_at_jst"] = "2099-01-10T09:00:00+09:00"
    late_out = finalize(order,matrix,registry,late)
    if not any(d.get("reason") == "CAPTURE_AFTER_CUTOFF" for d in late_out["decisions"]):
        raise AssertionError("late capture did not fail closed")

    return {
        "record":"KEIRIN_35_FORMAL_SUPPORT_FINALIZER_SELFTEST_v1",
        "status":"PASS",
        "tests":{
            "35_all_valid_stops_after_exactly_29":True,
            "six_failures_still_reaches_29":True,
            "seven_failures_fails_at_28":True,
            "post_cutoff_capture_fails_closed":True,
        },
        "result_accessed":False,
        "network_access":False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    run = sub.add_parser("finalize")
    run.add_argument("--order", required=True)
    run.add_argument("--matrix", required=True)
    run.add_argument("--registry", required=True)
    run.add_argument("--future-pre", required=True)
    run.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "selftest":
        print(json.dumps(selftest(), ensure_ascii=False, indent=2))
        return 0

    out = finalize(
        load(args.order),
        load(args.matrix),
        load(args.registry),
        load(args.future_pre),
    )
    dump(args.out, out)
    print(json.dumps({
        "status":out["status"],
        "new_pass_riders":out["new_pass_riders"],
        "cumulative_riders":out["cumulative_riders"],
        "cumulative_rows":out["cumulative_rows"],
    }, ensure_ascii=False))
    return 0 if out["status"] == "TARGET_30R_60ROWS_REACHED_PRE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
