#!/usr/bin/env python3
"""Relaxed-time PRE-only finalizer for the locked 35-rider Keirin front.

Owner policy 2026-09-08:
- Exact pit/cutoff timestamp is NOT a blocking requirement.
- RESULT/PAYOUT/ODDS/human comments remain excluded from formal support.
- Final support still requires exact Day1 race assignment (race/car/class/style)
  from a racecard/schedule evidence page, not a result page.

This is a v2 candidate implementation. It does not mutate v1.
"""

from __future__ import annotations

from copy import deepcopy
from collections import Counter, defaultdict
from typing import Any
import re

import keirin_35_formal_support_finalizer_v1 as base

FORBIDDEN_SOURCE_TOKENS = (
    "result", "results", "払戻", "結果", "odds", "オッズ", "prediction", "予想"
)


def _safe_source_role(row: dict) -> bool:
    role = str(row.get("source_role") or "").upper()
    if role not in {"FINAL_DAY1_RACECARD", "OFFICIAL_DAY1_RACECARD", "CTC_DAY1_RACECARD"}:
        return False
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("source_url", "source_namespace", "source_title")
    ).lower()
    return not any(tok.lower() in blob for tok in FORBIDDEN_SOURCE_TOKENS)


def validate_future_pre_row_v2(cand: dict, matrix_row: dict, registry_entry: dict, row: dict):
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
        if base.circumference_bucket(row.get("circumference_m")) != str(future.get("circumference_bucket")):
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
        base.validate_sha256(str(row.get("source_sha256") or ""))
        base.parse_dt(str(row.get("captured_at_jst") or ""), "captured_at_jst")

        if not _safe_source_role(row):
            return False, "SOURCE_NOT_FINAL_DAY1_RACECARD_OR_FORBIDDEN_NAMESPACE"

        if registry_entry.get("closure_status") != "OPEN_PRE_CUTOFF_READINESS":
            return False, "REGISTRY_NOT_OPEN"
        if registry_entry.get("prospective_day1_pre_membership") != "PENDING_EXACT_POSITIVE_DAY1_RACECARD":
            return False, "REGISTRY_NOT_PENDING_FINAL_PRE"

        historical = matrix_row.get("historical_row") or {}
        if base.circumference_bucket(historical.get("circumference_m")) == base.circumference_bucket(row.get("circumference_m")):
            return False, "NOT_CROSS_CIRCUMFERENCE"
    except (ValueError, TypeError, base.FinalizerError) as exc:
        return False, f"INVALID_PRE_ROW:{type(exc).__name__}:{str(exc)[:120]}"
    return True, None


def build_receipt_v2(cand: dict, matrix_row: dict, row: dict) -> dict:
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
        "source_role": str(row["source_role"]),
        "source_url": str(row["source_url"]),
        "source_sha256": str(row["source_sha256"]),
        "captured_at_jst": str(row["captured_at_jst"]),
        "registration_number": reg,
        "valid_pre_row_for_support": True,
        "pre_evidence_role": "FINAL_DAY1_PRE_SAME_RACE_WITNESS",
        "exact_cutoff_timestamp_required": False,
    }

    return {
        "record": f"KEIRIN_CROSS_CIRCUMFERENCE_SUPPORT_RECEIPT_{reg}_v2",
        "status": "CONFIRMED_ONE_RIDER_CROSS_CIRCUMFERENCE_SUPPORT_PRE_ONLY_RELAXED_TIME_PROVENANCE",
        "scope": "RESEARCH_PRE_ONLY_SUPPORT_ACCOUNTING_NO_RESULT_NO_MODEL_FIT",
        "support_definition": "One official registration number with at least one valid PRE race in each of the 333/333.33m and 400m buckets.",
        "rider": {
            "name": str(cand["rider_name"]),
            "official_registration_number": reg,
            "identity_key_status": "DETERMINISTIC_OFFICIAL_REGISTRATION_NUMBER",
        },
        "supported_rows": {"historical": historical, "future": future_row},
        "support_decision": {
            "same_official_registration_number_across_333_and_400": True,
            "both_rows_valid_pre": True,
            "final_day1_same_race_assignment_observed": True,
            "exact_pit_cutoff_timestamp_required": False,
            "result_page_used": False,
            "cross_circumference_supported_rider": True,
            "confirmed_unique_rider_increment_now": 1,
            "confirmed_supported_rider_race_rows_increment_now": 2,
            "result_needed_for_support_decision": False,
        },
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "human_forecast_accessed": False,
        "result_join_authorized": False,
        "formula_fit_authorized": False,
        "runtime": False,
    }


def finalize(order: dict, matrix: dict, registry: dict, future_pre: dict) -> dict:
    ordered, by_reg_matrix, by_key_registry = base.index_locked_inputs(order, matrix, registry)
    future_rows = list(future_pre.get("rows") or [])
    by_key_pre = {}
    for row in future_rows:
        key = base.candidate_key(
            str(row.get("official_registration_number") or ""),
            str(row.get("race_date") or ""),
            str(row.get("venue") or ""),
        )
        if key in by_key_pre:
            raise base.FinalizerError(f"duplicate_future_pre_row:{key}")
        by_key_pre[key] = row

    updated_registry = deepcopy(registry)
    updated_by_key = {}
    for entry in list(updated_registry.get("entries") or []):
        event = str(entry.get("event") or "")
        reg = str(entry.get("official_registration_number") or "")
        if "_" in event and re.fullmatch(r"\d{6}", reg):
            venue, date = event.rsplit("_", 1)
            updated_by_key[base.candidate_key(reg, date, venue)] = entry

    receipts, decisions = [], []
    venue_counts, rider_counts = Counter(), Counter()
    venues_by_bucket = defaultdict(set)

    baseline_rows = list(future_pre.get("baseline_supported_rows") or [])
    for row in baseline_rows:
        venue_counts[str(row["venue"])] += 1
        rider_counts[str(row["registration_number"])] += 1
        venues_by_bucket[base.circumference_bucket(row["circumference_m"])].add(str(row["venue"]))

    for cand in ordered:
        if len(receipts) >= base.TARGET_NEW_PASS:
            decisions.append({
                "priority": cand["priority"], "registration": cand["registration"],
                "rider_name": cand["rider_name"], "status": "NOT_PROCESSED_STOP_AFTER_29_NEW_PASS",
            })
            continue

        reg = str(cand["registration"])
        future = cand["future"]
        key = base.candidate_key(reg, future["date"], future["venue"])
        row = by_key_pre.get(key)
        if row is None:
            decisions.append({
                "priority": cand["priority"], "registration": reg,
                "rider_name": cand["rider_name"], "status": "FAIL_CLOSED",
                "reason": "FINAL_DAY1_PRE_ROW_MISSING",
            })
            continue

        ok, reason = validate_future_pre_row_v2(cand, by_reg_matrix[reg], by_key_registry[key], row)
        if not ok:
            decisions.append({
                "priority": cand["priority"], "registration": reg,
                "rider_name": cand["rider_name"], "status": "FAIL_CLOSED", "reason": reason,
            })
            continue

        receipt = build_receipt_v2(cand, by_reg_matrix[reg], row)
        receipts.append(receipt)
        decisions.append({
            "priority": cand["priority"], "registration": reg,
            "rider_name": cand["rider_name"], "status": "PASS_FORMAL_SUPPORT",
            "new_pass_index": len(receipts),
        })

        u = updated_by_key[key]
        u.update({
            "race_no": int(row["race_no"]),
            "car_no": int(row["car_no"]),
            "source": str(row.get("source") or "FINAL_DAY1_RACECARD"),
            "source_url_or_artifact": str(row["source_url"]),
            "captured_at_jst": str(row["captured_at_jst"]),
            "trusted_pit_cutoff_jst": None,
            "source_sha256": str(row["source_sha256"]),
            "prospective_day1_pre_membership": "PASS",
            "official_same_race_positive": "PASS",
            "provenance_status": "PASS_RELAXED_TIME_EXACT_RACECARD",
            "closure_status": "CLOSED_POSITIVE_DAY1_RACECARD",
            "formal_support_increment": 1,
        })

        for support_row in receipt["supported_rows"].values():
            venue_counts[str(support_row["venue"])] += 1
            rider_counts[reg] += 1
            venues_by_bucket[base.circumference_bucket(support_row["circumference_m"])].add(str(support_row["venue"]))

    new_pass = len(receipts)
    cumulative_riders = base.BASELINE_RIDERS + new_pass
    cumulative_rows = base.BASELINE_ROWS + 2 * new_pass
    total = sum(venue_counts.values())
    max_venue = max(venue_counts.values(), default=0)
    max_rider = max(rider_counts.values(), default=0)

    return {
        "record": "KEIRIN_35_FORMAL_SUPPORT_FINALIZATION_OUTPUT_v2",
        "status": "TARGET_30R_60ROWS_REACHED_PRE_ONLY" if new_pass == base.TARGET_NEW_PASS else "TARGET_NOT_REACHED_FAIL_CLOSED",
        "time_provenance_policy": "RELAXED_NO_EXACT_CUTOFF_REQUIRED_FINAL_DAY1_RACECARD_ONLY",
        "new_pass_riders": new_pass,
        "cumulative_riders": cumulative_riders,
        "cumulative_rows": cumulative_rows,
        "target_riders": base.TARGET_RIDERS,
        "target_rows": base.TARGET_ROWS,
        "stopped_after_29_new_pass": new_pass == base.TARGET_NEW_PASS,
        "decisions": decisions,
        "receipts": receipts,
        "updated_witness_registry": updated_registry,
        "unambiguous_gate_diagnostics": {
            "max_single_venue_share_global": (max_venue / total) if total else None,
            "max_single_venue_share_threshold": 0.60,
            "max_single_rider_share_global": (max_rider / total) if total else None,
            "max_single_rider_share_threshold": 0.10,
            "distinct_venues_by_circumference": {k: sorted(v) for k, v in venues_by_bucket.items()},
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
