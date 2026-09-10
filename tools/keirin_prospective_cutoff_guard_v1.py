#!/usr/bin/env python3
"""Date-agnostic prospective cutoff guard for KEIRIN PRE evidence.

No network access. No calendar discovery. No hard-coded event date.
It only verifies that an already-captured PRE evidence envelope was captured
at or before its own target cutoff and that no outcome/result information was
accessed or used to backfill missing PRE.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED = {
    "target_event_id",
    "capture_time",
    "target_cutoff",
    "outcome_accessed",
    "post_cutoff_backfill",
    "post_result_reconstruction",
    "missing_pre_policy",
}
FORBIDDEN_RESULT_KEYS = {
    "result",
    "results",
    "finish",
    "finish_order",
    "payout",
    "settlement",
    "winning_ticket",
    "outcome",
}


def parse_ts(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("FAIL_CLOSED:missing_timestamp")
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("FAIL_CLOSED:invalid_timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("FAIL_CLOSED:timezone_required")
    return dt


def find_forbidden_result_keys(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in FORBIDDEN_RESULT_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(find_forbidden_result_keys(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(find_forbidden_result_keys(value, f"{path}[{i}]"))
    return hits


def validate(envelope: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED - set(envelope))
    if missing:
        raise ValueError("FAIL_CLOSED:missing_required_fields=" + ",".join(missing))

    capture = parse_ts(envelope["capture_time"])
    cutoff = parse_ts(envelope["target_cutoff"])
    if capture > cutoff:
        raise ValueError("FAIL_CLOSED:capture_after_target_cutoff")

    if envelope["outcome_accessed"] is not False:
        raise ValueError("FAIL_CLOSED:outcome_accessed")
    if envelope["post_cutoff_backfill"] is not False:
        raise ValueError("FAIL_CLOSED:post_cutoff_backfill")
    if envelope["post_result_reconstruction"] is not False:
        raise ValueError("FAIL_CLOSED:post_result_reconstruction")
    if envelope["missing_pre_policy"] not in {"PERMANENT_MISSING", "SKIP"}:
        raise ValueError("FAIL_CLOSED:missing_pre_policy")

    hits = find_forbidden_result_keys(envelope.get("pre_payload", {}))
    if hits:
        raise ValueError("FAIL_CLOSED:result_key_in_pre_payload=" + ",".join(hits))

    return {
        "status": "PASS_PRE_CUTOFF_SELF_CONTAINED",
        "target_event_id": str(envelope["target_event_id"]),
        "capture_time": capture.isoformat(),
        "target_cutoff": cutoff.isoformat(),
        "later_calendar_information_required": False,
        "specific_future_date_required": False,
        "outcome_accessed": False,
        "post_cutoff_backfill": False,
        "post_result_reconstruction": False,
        "missing_pre_policy": envelope["missing_pre_policy"],
        "network_access": False,
    }


def selftest() -> dict[str, Any]:
    base = {
        "target_event_id": "TEST_EVENT",
        "capture_time": "2026-09-11T10:00:00+09:00",
        "target_cutoff": "2026-09-11T10:05:00+09:00",
        "outcome_accessed": False,
        "post_cutoff_backfill": False,
        "post_result_reconstruction": False,
        "missing_pre_policy": "SKIP",
        "pre_payload": {"race_number": 1, "car_number": 1, "competition_score": 88.5},
    }
    tests: dict[str, bool] = {}
    tests["valid_pre_cutoff_passes"] = validate(dict(base))["status"] == "PASS_PRE_CUTOFF_SELF_CONTAINED"

    bad = dict(base)
    bad["capture_time"] = "2026-09-11T10:06:00+09:00"
    try:
        validate(bad)
        tests["post_cutoff_capture_rejected"] = False
    except ValueError:
        tests["post_cutoff_capture_rejected"] = True

    bad = dict(base)
    bad["outcome_accessed"] = True
    try:
        validate(bad)
        tests["outcome_access_rejected"] = False
    except ValueError:
        tests["outcome_access_rejected"] = True

    bad = dict(base)
    bad["pre_payload"] = {"result": "1-2-3"}
    try:
        validate(bad)
        tests["result_key_rejected"] = False
    except ValueError:
        tests["result_key_rejected"] = True

    bad = dict(base)
    bad["post_result_reconstruction"] = True
    try:
        validate(bad)
        tests["post_result_reconstruction_rejected"] = False
    except ValueError:
        tests["post_result_reconstruction_rejected"] = True

    bad = dict(base)
    bad["capture_time"] = "2026-09-11T10:00:00"
    try:
        validate(bad)
        tests["naive_timestamp_rejected"] = False
    except ValueError:
        tests["naive_timestamp_rejected"] = True

    return {
        "record": "KEIRIN_PROSPECTIVE_CUTOFF_GUARD_SELFTEST_v1",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "network_access": False,
        "hardcoded_target_date": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    check = sub.add_parser("check")
    check.add_argument("--input", required=True)
    args = parser.parse_args()

    if args.cmd == "selftest":
        out = selftest()
        print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if out["status"] == "PASS" else 2

    envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
    try:
        out = validate(envelope)
    except ValueError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 3
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
