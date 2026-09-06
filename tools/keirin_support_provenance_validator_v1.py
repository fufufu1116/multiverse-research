#!/usr/bin/env python3
"""Research-only full provenance validator for cross-circumference support rows.

Validates PRE evidence + official same-race assignment evidence for one prospective
row and emits a support-row-ready provenance record. It never increments support,
never opens RESULT/payout/odds/forecast surfaces, and fails closed on any ambiguity.
"""
from __future__ import annotations

import argparse, hashlib, json, pathlib, re
from datetime import datetime, timezone

PRESPEC = pathlib.Path("v3/historical_all_market/research_candidates/KEIRIN_SUPPORT_RECEIPT_DUPLICATE_PROVENANCE_PRESPEC_20260906_v1.json")
PRESPEC_BLOB = "26a0fedd2a8b1a000b8bdba294c4e9a47f704e54"
FORBIDDEN_TRUE = {"result_accessed","target_result_accessed","payout_accessed","odds_accessed","human_forecast_accessed","forecast_accessed"}


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_utc(x: str) -> datetime:
    d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("FAIL_CLOSED_TZ_REQUIRED")
    return d.astimezone(timezone.utc)


def valid_sha256(x: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(x or "")))


def fail_on_forbidden_flags(obj: dict, label: str) -> None:
    bad = sorted(k for k in FORBIDDEN_TRUE if obj.get(k) is True)
    if bad:
        raise ValueError(f"FAIL_CLOSED_FORBIDDEN_{label}_FLAGS_{','.join(bad)}")


def validate(pre: dict, assignment: dict, expected_registration: str | None = None) -> dict:
    if git_blob(PRESPEC) != PRESPEC_BLOB:
        raise ValueError("FAIL_CLOSED_PRESPEC_BLOB_DRIFT")
    spec = load_json(PRESPEC)
    if spec.get("status") != "FROZEN_RESEARCH_PRE_ONLY_NO_RESULT_NO_SUPPORT_AUTO_AUTHORITY":
        raise ValueError("FAIL_CLOSED_PRESPEC_STATUS")

    fail_on_forbidden_flags(pre, "PRE")
    fail_on_forbidden_flags(assignment, "ASSIGNMENT")

    ev = pre.get("event") or {}
    if pre.get("day1_confirmed") is not True and ev.get("day") != "Day1":
        raise ValueError("FAIL_CLOSED_PRE_DAY1")
    race_date = str(ev.get("race_date") or pre.get("race_date") or "")
    venue = str(ev.get("venue") or pre.get("venue") or "")
    day = str(ev.get("day") or pre.get("day") or "")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", race_date) or not venue or day != "Day1":
        raise ValueError("FAIL_CLOSED_PRE_EVENT_BINDING")

    cutoff_raw = pre.get("first_race_pit_cutoff_utc") or pre.get("pit_cutoff_utc")
    captured_raw = pre.get("generated_utc") or pre.get("captured_utc")
    if not cutoff_raw or not captured_raw:
        raise ValueError("FAIL_CLOSED_PRE_CUTOFF_OR_CAPTURE_MISSING")
    cutoff = parse_utc(cutoff_raw)
    captured = parse_utc(captured_raw)
    if captured >= cutoff:
        raise ValueError("FAIL_CLOSED_PRE_NOT_BEFORE_CUTOFF")
    if pre.get("captured_before_pit_cutoff") is False or pre.get("captured_before_first_race_pit_cutoff") is False:
        raise ValueError("FAIL_CLOSED_PRE_CAPTURE_FLAG")

    a_status = assignment.get("status")
    if a_status not in {"EXACT_SINGLE_MATCH_EVENT_CORROBORATED", "EXACT_SINGLE_FRAGMENT_EVENT_CORROBORATED"}:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_STATUS")
    if assignment.get("captured_before_pit_cutoff") is not True:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_NOT_BEFORE_CUTOFF")
    if assignment.get("event_assignment_eligible_for_frozen_mapper") is not True:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_NOT_ELIGIBLE")

    expected = assignment.get("expected") or {}
    observed = assignment.get("observed_current_event") or {}
    for k, val in (("race_date", race_date), ("venue", venue), ("day", "Day1")):
        if str(expected.get(k)) != str(val):
            raise ValueError(f"FAIL_CLOSED_ASSIGNMENT_EXPECTED_{k}")
        if observed and str(observed.get(k)) != str(val):
            raise ValueError(f"FAIL_CLOSED_ASSIGNMENT_OBSERVED_{k}")
    if observed and observed.get("same_race_exact_match") is not True:
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_SAME_RACE")

    reg = str(expected.get("registration_number") or "")
    if not re.fullmatch(r"\d{6}", reg):
        raise ValueError("FAIL_CLOSED_REGISTRATION")
    if expected_registration is not None and reg != str(expected_registration):
        raise ValueError("FAIL_CLOSED_REGISTRATION_BINDING")

    assignment_cutoff = parse_utc(assignment.get("pit_cutoff_utc"))
    if assignment_cutoff != cutoff:
        raise ValueError("FAIL_CLOSED_CUTOFF_HANDOFF_MISMATCH")

    pre_sha = pre.get("source_file_sha256") or (pre.get("output_sha256") or {}).get("pre_rows_csv") or pre.get("source_racecard_sha256")
    if not valid_sha256(pre_sha):
        raise ValueError("FAIL_CLOSED_PRE_SOURCE_SHA256")
    assignment_sha = assignment.get("profile_raw_sha256") or assignment.get("current_race_section_sha256")
    if not valid_sha256(assignment_sha):
        raise ValueError("FAIL_CLOSED_ASSIGNMENT_SOURCE_SHA256")

    return {
        "record":"KEIRIN_SUPPORT_PROVENANCE_VALIDATION_v1",
        "status":"PASS_FULL_PROVENANCE_READY_FOR_DUPLICATE_SAFE_RECEIPT_GUARD",
        "event":{"race_date":race_date,"venue":venue,"day":"Day1"},
        "official_registration_number":reg,
        "pre_capture_before_pit_cutoff":True,
        "official_same_race_assignment_before_cutoff":True,
        "same_event_exact_match":True,
        "same_race_exact_match":True,
        "pre_source_sha256":pre_sha,
        "assignment_source_sha256":assignment_sha,
        "pit_cutoff_utc":cutoff.isoformat(),
        "result_accessed":False,
        "payout_accessed":False,
        "odds_accessed":False,
        "forecast_accessed":False,
        "support_increment_authorized_now":0,
        "result_join_authorized":False,
        "formula_fit_authorized":False,
        "main_or_runtime_mutation":False,
    }


def selftest() -> dict:
    future = "2099-01-01T00:00:00+00:00"
    pre = {
        "event":{"race_date":"2098-12-31","venue":"伊東","day":"Day1"},
        "day1_confirmed":True,"generated_utc":"2098-12-30T23:00:00+00:00",
        "first_race_pit_cutoff_utc":future,"captured_before_pit_cutoff":True,
        "source_file_sha256":"a"*64,"result_accessed":False,"payout_accessed":False,"odds_accessed":False,
    }
    assignment = {
        "status":"EXACT_SINGLE_MATCH_EVENT_CORROBORATED","captured_before_pit_cutoff":True,
        "event_assignment_eligible_for_frozen_mapper":True,"pit_cutoff_utc":future,
        "expected":{"registration_number":"015423","race_date":"2098-12-31","venue":"伊東","day":"Day1"},
        "observed_current_event":{"race_date":"2098-12-31","venue":"伊東","day":"Day1","same_race_exact_match":True},
        "profile_raw_sha256":"b"*64,"result_accessed":False,"payout_accessed":False,"odds_accessed":False,
    }
    tests = {}
    try:
        out = validate(pre, assignment, "015423")
        tests["valid_bundle_passes"] = out["status"].startswith("PASS_FULL_PROVENANCE")
    except Exception:
        tests["valid_bundle_passes"] = False
    bad = dict(assignment); bad["status"] = "FAIL_CLOSED_OFFICIAL_SAME_RACE_ASSIGNMENT_NOT_PROVEN"
    try:
        validate(pre, bad, "015423"); tests["unproven_assignment_rejected"] = False
    except ValueError:
        tests["unproven_assignment_rejected"] = True
    bad_pre = dict(pre); bad_pre["generated_utc"] = future
    try:
        validate(bad_pre, assignment, "015423"); tests["late_pre_rejected"] = False
    except ValueError:
        tests["late_pre_rejected"] = True
    return {"record":"KEIRIN_SUPPORT_PROVENANCE_VALIDATOR_SELFTEST_v1","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"network_access":False,"support_increment_authorized_now":0,"result_accessed":False}


def main() -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True); sub.add_parser("selftest")
    p = sub.add_parser("validate"); p.add_argument("--pre", required=True); p.add_argument("--assignment", required=True); p.add_argument("--registration-number"); p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "selftest":
        x = selftest(); print(json.dumps(x, ensure_ascii=False, sort_keys=True)); return 0 if x["status"] == "PASS" else 2
    try:
        out = validate(load_json(pathlib.Path(a.pre)), load_json(pathlib.Path(a.assignment)), a.registration_number)
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"record":out["record"],"status":out["status"],"support_increment_authorized_now":0}, ensure_ascii=False, sort_keys=True)); return 0
    except Exception as exc:
        out = {"record":"KEIRIN_SUPPORT_PROVENANCE_VALIDATION_v1","status":"FAIL_CLOSED_FULL_PROVENANCE_NOT_PROVEN","fatal_error":f"{type(exc).__name__}: {str(exc)[:500]}","support_increment_authorized_now":0,"result_accessed":False,"result_join_authorized":False,"formula_fit_authorized":False,"main_or_runtime_mutation":False}
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False, sort_keys=True)); return 3

if __name__ == "__main__":
    raise SystemExit(main())
