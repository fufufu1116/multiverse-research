#!/usr/bin/env python3
"""KEIRIN prospective cutoff/provenance guard v2.

Repository-only validator. No network access, no event discovery, no hard-coded date.
It validates that a PRE envelope:
1) was captured at/before its own target cutoff,
2) contains no result/outcome keys in PRE payload,
3) carries at least one trusted source receipt,
4) cryptographically matches immutable local source snapshots,
5) uses the exact frozen v54 decision bindings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
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
    "pre_payload",
    "source_receipts",
    "frozen_v54",
}
RECEIPT_REQUIRED = {
    "source_id",
    "source_locator",
    "trust_class",
    "retrieved_at",
    "http_status",
    "snapshot_path",
    "content_sha256",
}
TRUSTED_CLASSES = {"OFFICIAL", "PRIMARY"}
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
EXPECTED_V54 = {
    "b1a_mkt50_transform_git_blob": "6fb09aaba113cd1b4a8d9f4b0b68e5beaff18fff",
    "final_selector_git_blob": "34c4ae08bfd21240bdfec63de9427e1b5d277d6f",
    "validator_git_blob": "bbdcef51ce1d216fbda9e1bdf042ed9ef397876f",
    "pool_weight": 0.50,
    "competition_score_threshold": 0.40,
    "ticket_template": "SINGLE",
    "stake_policy": "FK10_R2",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def resolve_snapshot(repo_root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("FAIL_CLOSED:missing_snapshot_path")
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("FAIL_CLOSED:unsafe_snapshot_path")
    root = repo_root.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("FAIL_CLOSED:snapshot_outside_repo_root") from exc
    if not candidate.is_file():
        raise ValueError("FAIL_CLOSED:snapshot_missing")
    return candidate


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(envelope: dict[str, Any], repo_root: Path) -> dict[str, Any]:
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

    hits = find_forbidden_result_keys(envelope["pre_payload"])
    if hits:
        raise ValueError("FAIL_CLOSED:result_key_in_pre_payload=" + ",".join(hits))

    if envelope["frozen_v54"] != EXPECTED_V54:
        raise ValueError("FAIL_CLOSED:frozen_v54_binding_mismatch")

    receipts = envelope["source_receipts"]
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("FAIL_CLOSED:source_receipts_required")

    trusted = 0
    checked_receipts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ValueError(f"FAIL_CLOSED:receipt_not_object={index}")
        miss = sorted(RECEIPT_REQUIRED - set(receipt))
        if miss:
            raise ValueError(
                f"FAIL_CLOSED:receipt_missing_fields={index}:" + ",".join(miss)
            )
        source_id = str(receipt["source_id"]).strip()
        if not source_id or source_id in seen_ids:
            raise ValueError(f"FAIL_CLOSED:receipt_source_id_invalid_or_duplicate={index}")
        seen_ids.add(source_id)

        retrieved = parse_ts(receipt["retrieved_at"])
        if retrieved > capture:
            raise ValueError(f"FAIL_CLOSED:receipt_after_envelope_capture={index}")
        if retrieved > cutoff:
            raise ValueError(f"FAIL_CLOSED:receipt_after_target_cutoff={index}")
        if receipt["http_status"] != 200:
            raise ValueError(f"FAIL_CLOSED:receipt_http_status_not_200={index}")

        trust_class = str(receipt["trust_class"]).upper()
        if trust_class in TRUSTED_CLASSES:
            trusted += 1

        claimed = str(receipt["content_sha256"]).lower()
        if not SHA256_RE.fullmatch(claimed):
            raise ValueError(f"FAIL_CLOSED:receipt_sha256_invalid={index}")
        snapshot = resolve_snapshot(repo_root, receipt["snapshot_path"])
        actual = sha256_file(snapshot)
        if actual != claimed:
            raise ValueError(f"FAIL_CLOSED:receipt_sha256_mismatch={index}")

        checked_receipts.append(
            {
                "source_id": source_id,
                "trust_class": trust_class,
                "retrieved_at": retrieved.isoformat(),
                "snapshot_path": str(receipt["snapshot_path"]),
                "content_sha256": actual,
            }
        )

    if trusted < 1:
        raise ValueError("FAIL_CLOSED:no_trusted_official_or_primary_receipt")

    return {
        "status": "PASS_PRE_CUTOFF_PROVENANCE_BOUND",
        "target_event_id": str(envelope["target_event_id"]),
        "capture_time": capture.isoformat(),
        "target_cutoff": cutoff.isoformat(),
        "source_receipts_checked": len(checked_receipts),
        "trusted_receipts": trusted,
        "receipts": checked_receipts,
        "frozen_v54_exact_match": True,
        "later_calendar_information_required": False,
        "specific_future_date_required": False,
        "outcome_accessed": False,
        "post_cutoff_backfill": False,
        "post_result_reconstruction": False,
        "missing_pre_policy": envelope["missing_pre_policy"],
        "network_access": False,
    }


def selftest() -> dict[str, Any]:
    tests: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        snap = root / "evidence" / "source.json"
        snap.parent.mkdir(parents=True)
        snap.write_bytes(b'{"race_number":1,"car_number":1}')
        digest = sha256_file(snap)
        base = {
            "target_event_id": "TEST_EVENT",
            "capture_time": "2026-09-11T10:00:00+09:00",
            "target_cutoff": "2026-09-11T10:05:00+09:00",
            "outcome_accessed": False,
            "post_cutoff_backfill": False,
            "post_result_reconstruction": False,
            "missing_pre_policy": "SKIP",
            "pre_payload": {"race_number": 1, "car_number": 1, "competition_score": 88.5},
            "frozen_v54": dict(EXPECTED_V54),
            "source_receipts": [{
                "source_id": "official-test",
                "source_locator": "https://example.invalid/pre",
                "trust_class": "OFFICIAL",
                "retrieved_at": "2026-09-11T09:59:00+09:00",
                "http_status": 200,
                "snapshot_path": "evidence/source.json",
                "content_sha256": digest,
            }],
        }

        tests["valid_provenance_bound_pre_passes"] = (
            validate(json.loads(json.dumps(base)), root)["status"]
            == "PASS_PRE_CUTOFF_PROVENANCE_BOUND"
        )

        def mut_capture_after(x):
            x["capture_time"] = "2026-09-11T10:06:00+09:00"

        def mut_outcome(x):
            x["outcome_accessed"] = True

        def mut_result_key(x):
            x["pre_payload"] = {"result": "1-2-3"}

        def mut_naive(x):
            x["capture_time"] = "2026-09-11T10:00:00"

        def mut_no_receipts(x):
            x["source_receipts"] = []

        def mut_bad_hash(x):
            x["source_receipts"][0]["content_sha256"] = "0" * 64

        def mut_receipt_after_capture(x):
            x["source_receipts"][0]["retrieved_at"] = "2026-09-11T10:01:00+09:00"

        def mut_untrusted(x):
            x["source_receipts"][0]["trust_class"] = "SECONDARY"

        def mut_v54(x):
            x["frozen_v54"]["pool_weight"] = 0.51

        def mut_traversal(x):
            x["source_receipts"][0]["snapshot_path"] = "../source.json"

        cases = [
            ("post_cutoff_capture_rejected", mut_capture_after),
            ("outcome_access_rejected", mut_outcome),
            ("result_key_rejected", mut_result_key),
            ("naive_timestamp_rejected", mut_naive),
            ("missing_receipts_rejected", mut_no_receipts),
            ("snapshot_hash_mismatch_rejected", mut_bad_hash),
            ("receipt_after_capture_rejected", mut_receipt_after_capture),
            ("untrusted_only_rejected", mut_untrusted),
            ("v54_binding_drift_rejected", mut_v54),
            ("snapshot_path_traversal_rejected", mut_traversal),
        ]
        for name, mut in cases:
            bad = json.loads(json.dumps(base))
            mut(bad)
            try:
                validate(bad, root)
                tests[name] = False
            except ValueError:
                tests[name] = True

    return {
        "record": "KEIRIN_PROSPECTIVE_CUTOFF_GUARD_SELFTEST_v2",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "test_count": len(tests),
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
    check.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    if args.cmd == "selftest":
        out = selftest()
        print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if out["status"] == "PASS" else 2

    try:
        envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
        out = validate(envelope, Path(args.repo_root))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps(
            {"status": "FAIL_CLOSED", "reason": str(exc)},
            ensure_ascii=False,
            sort_keys=True,
        ))
        return 3
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
