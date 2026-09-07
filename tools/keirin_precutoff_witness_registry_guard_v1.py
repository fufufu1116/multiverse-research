#!/usr/bin/env python3
"""Research-only fail-closed guard for the Keirin pre-cutoff witness registry.

The registry is evidence/readiness state only. This guard never grants support,
never reads RESULT/payout/odds/predictions, and never performs network or runtime
mutation. It enforces unique event/rider bindings and blocks any "positive"
same-race witness whose capture is missing, late, or unbound to a trusted cutoff.
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, re

REQ_TOP = {"record", "status", "entries", "write_rule", "closure_rule"}
REQ_ENTRY = {
    "event", "rider", "official_registration_number", "race_no", "car_no",
    "source", "source_url_or_artifact", "captured_at_jst",
    "trusted_pit_cutoff_jst", "source_sha256",
    "prospective_day1_pre_membership", "official_same_race_positive",
    "provenance_status", "closure_status", "formal_support_increment",
}
POSITIVE = {"PASS", "POSITIVE", "TRUE"}
PERMANENT_PREFIX = "PERMANENT_"


def parse_iso(x: str) -> dt.datetime:
    if not isinstance(x, str) or not x.strip():
        raise ValueError("FAIL_CLOSED_TIMESTAMP_MISSING")
    try:
        y = dt.datetime.fromisoformat(x)
    except Exception as e:
        raise ValueError("FAIL_CLOSED_TIMESTAMP_PARSE") from e
    if y.tzinfo is None or y.utcoffset() is None:
        raise ValueError("FAIL_CLOSED_TIMESTAMP_NAIVE")
    return y


def reg6(x) -> str:
    s = str(x).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError("FAIL_CLOSED_REGISTRATION_NUMBER")
    return s


def status_positive(x) -> bool:
    return str(x).strip().upper() in POSITIVE


def validate_entry(e: dict) -> dict:
    missing = sorted(REQ_ENTRY - set(e))
    if missing:
        raise ValueError("FAIL_CLOSED_MISSING_ENTRY_FIELDS_" + ",".join(missing))
    if not str(e.get("event") or "").strip():
        raise ValueError("FAIL_CLOSED_EVENT")
    if not str(e.get("rider") or "").strip():
        raise ValueError("FAIL_CLOSED_RIDER")
    reg = reg6(e.get("official_registration_number"))

    inc = e.get("formal_support_increment")
    if inc != 0:
        raise ValueError("FAIL_CLOSED_WITNESS_REGISTRY_HAS_NO_SUPPORT_AUTHORITY")

    closed = str(e.get("closure_status") or "").startswith(PERMANENT_PREFIX)
    same_race = status_positive(e.get("official_same_race_positive"))

    if closed and same_race:
        raise ValueError("FAIL_CLOSED_PERMANENT_CLOSURE_CANNOT_BE_POSITIVE_WITNESS")

    if same_race:
        captured = parse_iso(e.get("captured_at_jst"))
        cutoff = parse_iso(e.get("trusted_pit_cutoff_jst"))
        if captured >= cutoff:
            raise ValueError("FAIL_CLOSED_WITNESS_NOT_PRE_CUTOFF")
        if not str(e.get("source") or "").strip() or not str(e.get("source_url_or_artifact") or "").strip():
            raise ValueError("FAIL_CLOSED_POSITIVE_WITNESS_SOURCE_MISSING")
        rn, cn = e.get("race_no"), e.get("car_no")
        if not isinstance(rn, int) or not 1 <= rn <= 12:
            raise ValueError("FAIL_CLOSED_POSITIVE_WITNESS_RACE_NO")
        if not isinstance(cn, int) or not 1 <= cn <= 9:
            raise ValueError("FAIL_CLOSED_POSITIVE_WITNESS_CAR_NO")

    h = e.get("source_sha256")
    if h is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", str(h)):
        raise ValueError("FAIL_CLOSED_SOURCE_SHA256")

    return {
        "event": e["event"],
        "registration_number": reg,
        "closed": closed,
        "same_race_positive": same_race,
    }


def validate_registry(registry: dict) -> dict:
    missing = sorted(REQ_TOP - set(registry))
    if missing:
        raise ValueError("FAIL_CLOSED_MISSING_TOP_FIELDS_" + ",".join(missing))
    if registry.get("record") != "KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_20260907_v1":
        raise ValueError("FAIL_CLOSED_REGISTRY_ID")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("FAIL_CLOSED_ENTRIES")

    seen = set()
    checked = []
    for e in entries:
        if not isinstance(e, dict):
            raise ValueError("FAIL_CLOSED_ENTRY_TYPE")
        v = validate_entry(e)
        key = (v["event"], v["registration_number"])
        if key in seen:
            raise ValueError("FAIL_CLOSED_DUPLICATE_EVENT_REGISTRATION")
        seen.add(key)
        checked.append(v)

    return {
        "record": "KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_GUARD_v1",
        "status": "PASS_FAIL_CLOSED_WITNESS_REGISTRY_SHAPE_AND_TIMING_VALIDATED",
        "entry_count": len(checked),
        "permanently_closed_entries": sum(1 for x in checked if x["closed"]),
        "positive_pre_cutoff_same_race_witnesses": sum(1 for x in checked if x["same_race_positive"]),
        "support_increment_authorized_now": 0,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "prediction_accessed": False,
        "network_access": False,
        "main_or_runtime_mutation": False,
    }


def selftest() -> dict:
    base = {
        "event": "TEST_2099-01-01", "rider": "テスト", "official_registration_number": "012345",
        "race_no": 1, "car_no": 2, "source": "official", "source_url_or_artifact": "artifact.json",
        "captured_at_jst": "2099-01-01T09:00:00+09:00", "trusted_pit_cutoff_jst": "2099-01-01T09:30:00+09:00",
        "source_sha256": "a"*64, "prospective_day1_pre_membership": "PASS",
        "official_same_race_positive": "PASS", "provenance_status": "PASS",
        "closure_status": "OPEN_PRE_CUTOFF_READINESS", "formal_support_increment": 0,
    }
    registry = {
        "record": "KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_20260907_v1",
        "status": "TEST", "entries": [base], "write_rule": "x", "closure_rule": "y",
    }
    tests = {}
    try:
        tests["positive_pre_cutoff_pass"] = validate_registry(registry)["positive_pre_cutoff_same_race_witnesses"] == 1
    except Exception:
        tests["positive_pre_cutoff_pass"] = False

    late = json.loads(json.dumps(registry))
    late["entries"][0]["captured_at_jst"] = "2099-01-01T09:30:00+09:00"
    try:
        validate_registry(late); tests["at_cutoff_fail_closed"] = False
    except ValueError:
        tests["at_cutoff_fail_closed"] = True

    dup = json.loads(json.dumps(registry)); dup["entries"].append(json.loads(json.dumps(base)))
    try:
        validate_registry(dup); tests["duplicate_fail_closed"] = False
    except ValueError:
        tests["duplicate_fail_closed"] = True

    authority = json.loads(json.dumps(registry)); authority["entries"][0]["formal_support_increment"] = 1
    try:
        validate_registry(authority); tests["no_support_authority"] = False
    except ValueError:
        tests["no_support_authority"] = True

    return {
        "record": "KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_GUARD_SELFTEST_v1",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "network_access": False,
        "support_increment_authorized_now": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("validate"); p.add_argument("registry")
    a = ap.parse_args()

    if a.cmd == "selftest":
        x = selftest()
        print(json.dumps(x, ensure_ascii=False, sort_keys=True))
        return 0 if x["status"] == "PASS" else 2

    try:
        registry = json.loads(pathlib.Path(a.registry).read_text(encoding="utf-8"))
        print(json.dumps(validate_registry(registry), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as e:
        print(json.dumps({
            "record": "KEIRIN_PRE_CUTOFF_WITNESS_REGISTRY_GUARD_v1",
            "status": "FAIL_CLOSED_WITNESS_REGISTRY_GUARD",
            "fatal_error": f"{type(e).__name__}: {str(e)[:400]}",
            "support_increment_authorized_now": 0,
            "result_accessed": False,
        }, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
