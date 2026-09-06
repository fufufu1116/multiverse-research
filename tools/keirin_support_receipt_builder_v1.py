#!/usr/bin/env python3
"""Research-only deterministic cross-circumference support receipt builder v1.

Builds a receipt-shaped object from one already-valid historical PRE row, one
prospective PRE row, and a PASS full-provenance record. The output is validated
through the pinned duplicate-safe receipt guard before being emitted.

This builder never authorizes support increments, never uses RESULT/payout/odds/
forecast evidence, and fails closed on registration, event, hash, bucket, or
provenance mismatches.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re

PRESPEC = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_SUPPORT_RECEIPT_DUPLICATE_PROVENANCE_PRESPEC_20260906_v1.json")
PRESPEC_BLOB = "26a0fedd2a8b1a000b8bdba294c4e9a47f704e54"
GUARD = pathlib.Path("tools/keirin_support_receipt_guard_v1.py")
GUARD_BLOB = "3105c38fb10f25846dbfa80fd2c6a952e6dd1425"
FORBIDDEN_TRUE = {"result_accessed","target_result_accessed","payout_accessed","odds_accessed","human_forecast_accessed","forecast_accessed"}


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reg6(value: str) -> str:
    s = str(value).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError("FAIL_CLOSED_REGISTRATION_NUMBER")
    return s


def load_guard():
    if git_blob(PRESPEC) != PRESPEC_BLOB:
        raise ValueError("FAIL_CLOSED_PRESPEC_BLOB_DRIFT")
    if git_blob(GUARD) != GUARD_BLOB:
        raise ValueError("FAIL_CLOSED_GUARD_BLOB_DRIFT")
    spec = importlib.util.spec_from_file_location("keirin_support_receipt_guard_v1", GUARD)
    if not spec or not spec.loader:
        raise ValueError("FAIL_CLOSED_GUARD_IMPORT")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail_on_forbidden(obj: dict, label: str) -> None:
    bad = sorted(k for k in FORBIDDEN_TRUE if obj.get(k) is True)
    if bad:
        raise ValueError(f"FAIL_CLOSED_FORBIDDEN_{label}_FLAGS_{','.join(bad)}")


def validate_provenance_for_row(provenance: dict, row: dict, reg: str) -> None:
    if provenance.get("record") != "KEIRIN_SUPPORT_PROVENANCE_VALIDATION_v1":
        raise ValueError("FAIL_CLOSED_PROVENANCE_RECORD")
    if provenance.get("status") != "PASS_FULL_PROVENANCE_READY_FOR_DUPLICATE_SAFE_RECEIPT_GUARD":
        raise ValueError("FAIL_CLOSED_PROVENANCE_STATUS")
    if reg6(provenance.get("official_registration_number")) != reg:
        raise ValueError("FAIL_CLOSED_PROVENANCE_REG_BINDING")
    ev = provenance.get("event") or {}
    for k in ("race_date","venue","day"):
        if str(ev.get(k)) != str(row.get(k)):
            raise ValueError(f"FAIL_CLOSED_PROVENANCE_EVENT_{k}")
    if provenance.get("pre_capture_before_pit_cutoff") is not True:
        raise ValueError("FAIL_CLOSED_PRE_CUTOFF_PROVENANCE")
    if provenance.get("official_same_race_assignment_before_cutoff") is not True:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_CUTOFF_PROVENANCE")
    if provenance.get("same_event_exact_match") is not True or provenance.get("same_race_exact_match") is not True:
        raise ValueError("FAIL_CLOSED_SAME_RACE_PROVENANCE")
    if str(provenance.get("pre_source_sha256") or "").lower() != str(row.get("source_file_sha256") or "").lower():
        raise ValueError("FAIL_CLOSED_PROVENANCE_PRE_HASH_BINDING")
    if not re.fullmatch(r"[0-9a-f]{64}", str(provenance.get("assignment_source_sha256") or "")):
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_HASH")
    fail_on_forbidden(provenance, "PROVENANCE")


def build(rider_name: str, registration_number: str, historical_row: dict, prospective_row: dict, provenance: dict) -> dict:
    guard = load_guard()
    reg = reg6(registration_number)
    if not str(rider_name or "").strip():
        raise ValueError("FAIL_CLOSED_RIDER_NAME")
    fail_on_forbidden(historical_row, "HISTORICAL_ROW")
    fail_on_forbidden(prospective_row, "PROSPECTIVE_ROW")

    # Use the guard's canonical row validation for both rows.
    historical_key = guard.row_key(reg, historical_row)
    prospective_key = guard.row_key(reg, prospective_row)
    if historical_key == prospective_key:
        raise ValueError("FAIL_CLOSED_IDENTICAL_CANONICAL_ROWS")
    if historical_key[1] == prospective_key[1]:
        raise ValueError("FAIL_CLOSED_NOT_CROSS_CIRCUMFERENCE")
    if {historical_key[1], prospective_key[1]} != {"333_OR_333_33", "400"}:
        raise ValueError("FAIL_CLOSED_BUCKET_PAIR")

    validate_provenance_for_row(provenance, prospective_row, reg)

    receipt = {
        "record":"KEIRIN_CROSS_CIRCUMFERENCE_SUPPORT_RECEIPT_BUILDER_OUTPUT_v1",
        "status":"RECEIPT_SHAPE_BUILT_AND_GUARD_VALIDATED_NO_ACCOUNTING_AUTHORITY",
        "scope":"RESEARCH_PRE_ONLY_SUPPORT_RECEIPT_CANDIDATE_NO_RESULT_NO_MODEL_FIT",
        "rider":{"name":rider_name,"official_registration_number":reg},
        "supported_rows":{"historical":historical_row,"prospective":prospective_row},
        "provenance_binding":{
            "prospective_provenance_record":provenance.get("record"),
            "prospective_provenance_status":provenance.get("status"),
            "pit_cutoff_utc":provenance.get("pit_cutoff_utc"),
            "assignment_source_sha256":provenance.get("assignment_source_sha256"),
            "pre_source_sha256":provenance.get("pre_source_sha256"),
        },
        "support_decision":{
            "same_official_registration_number_across_333_and_400":True,
            "both_rows_valid_pre":True,
            "cross_circumference_supported_rider":True,
            "confirmed_unique_rider_increment_now":0,
            "confirmed_supported_rider_race_rows_increment_now":0,
            "result_needed_for_support_decision":False,
        },
        "result_accessed":False,
        "target_result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "human_forecast_accessed":False,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "support_increment_authorized_now":0,
        "main_or_runtime_mutation":False,
    }
    guard_result = guard.validate_receipt(receipt)
    receipt["guard_validation"] = {
        "status":"PASS_DUPLICATE_SAFE_RECEIPT_SHAPE",
        "registration_number":guard_result["registration_number"],
        "cross_circumference_qualified":guard_result["cross_circumference_qualified"],
        "canonical_row_keys":guard_result["canonical_row_keys"],
    }
    return receipt


def selftest() -> dict:
    hist = {
        "race_date":"2098-12-30","venue":"川崎","circumference_m":400,"day":"Day1","race_no":1,"car_no":3,
        "pre_artifact":"hist.json","source_file_sha256":"a"*64,"registration_number":"015423","valid_pre_row_for_support":True,
    }
    prosp = {
        "race_date":"2098-12-31","venue":"伊東","circumference_m":333.33,"day":"Day1","race_no":3,"car_no":5,
        "pre_artifact":"prospective.json","source_file_sha256":"b"*64,"registration_number":"015423","valid_pre_row_for_support":True,
    }
    prov = {
        "record":"KEIRIN_SUPPORT_PROVENANCE_VALIDATION_v1",
        "status":"PASS_FULL_PROVENANCE_READY_FOR_DUPLICATE_SAFE_RECEIPT_GUARD",
        "event":{"race_date":"2098-12-31","venue":"伊東","day":"Day1"},
        "official_registration_number":"015423",
        "pre_capture_before_pit_cutoff":True,
        "official_same_race_assignment_before_cutoff":True,
        "same_event_exact_match":True,
        "same_race_exact_match":True,
        "pre_source_sha256":"b"*64,
        "assignment_source_sha256":"c"*64,
        "pit_cutoff_utc":"2098-12-31T00:00:00+00:00",
        "result_accessed":False,"payout_accessed":False,"odds_accessed":False,"forecast_accessed":False,
    }
    tests = {}
    try:
        out = build("上川 直紀", "015423", hist, prosp, prov)
        tests["valid_cross_circ_receipt_builds"] = out.get("guard_validation",{}).get("cross_circumference_qualified") is True
    except Exception:
        tests["valid_cross_circ_receipt_builds"] = False
    bad = json.loads(json.dumps(prov)); bad["pre_source_sha256"] = "d"*64
    try:
        build("上川 直紀", "015423", hist, prosp, bad); tests["provenance_hash_mismatch_rejected"] = False
    except ValueError:
        tests["provenance_hash_mismatch_rejected"] = True
    same = json.loads(json.dumps(prosp)); same["circumference_m"] = 400
    try:
        build("上川 直紀", "015423", hist, same, prov); tests["same_bucket_rejected"] = False
    except ValueError:
        tests["same_bucket_rejected"] = True
    return {
        "record":"KEIRIN_SUPPORT_RECEIPT_BUILDER_SELFTEST_v1",
        "status":"PASS" if all(tests.values()) else "FAIL",
        "tests":tests,
        "network_access":False,
        "support_increment_authorized_now":0,
        "result_accessed":False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True); sub.add_parser("selftest")
    p = sub.add_parser("build"); p.add_argument("--rider-name", required=True); p.add_argument("--registration-number", required=True); p.add_argument("--historical-row", required=True); p.add_argument("--prospective-row", required=True); p.add_argument("--provenance", required=True); p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "selftest":
        x = selftest(); print(json.dumps(x, ensure_ascii=False, sort_keys=True)); return 0 if x["status"] == "PASS" else 2
    try:
        out = build(a.rider_name, a.registration_number, load_json(pathlib.Path(a.historical_row)), load_json(pathlib.Path(a.prospective_row)), load_json(pathlib.Path(a.provenance)))
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"record":out["record"],"status":out["status"],"support_increment_authorized_now":0}, ensure_ascii=False, sort_keys=True)); return 0
    except Exception as exc:
        out = {"record":"KEIRIN_CROSS_CIRCUMFERENCE_SUPPORT_RECEIPT_BUILDER_OUTPUT_v1","status":"FAIL_CLOSED_RECEIPT_NOT_BUILT","fatal_error":f"{type(exc).__name__}: {str(exc)[:500]}","support_increment_authorized_now":0,"result_accessed":False,"result_join_authorized":False,"formula_fit_authorized":False,"main_or_runtime_mutation":False}
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False, sort_keys=True)); return 3

if __name__ == "__main__":
    raise SystemExit(main())
