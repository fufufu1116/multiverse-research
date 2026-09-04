#!/usr/bin/env python3
"""Research-only KDreamS prospective PRE capture orchestrator v1.

Given one exact, positively observed Day1 racecard URL, this orchestrator runs:
  1) PIT cutoff extraction,
  2) positive racedetail manifest construction,
  3) strict prospective PRE acquisition.

All three child tools are blob-pinned. Mixed HTML remains in child-process memory
only. The orchestrator never performs identity mapping, support authorization,
RESULT joining, model fitting, payout/odds use, or runtime/main mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone

CHILDREN = {
    "pit": (
        pathlib.Path("tools/keirin_kdreams_pit_cutoff_extractor_v2.py"),
        "d11d32432fbb09c54f2456c69e99a586da0ffc84",
    ),
    "manifest": (
        pathlib.Path("tools/keirin_kdreams_positive_day1_manifest_builder_v1.py"),
        "6093791c1f5439fced0128aaea64910c952efd50",
    ),
    "acquire": (
        pathlib.Path("tools/keirin_kdreams_prospective_pre_acquire_v1.py"),
        "ee50af4c37ea6e951df3bcc7212c92e8f184f153",
    ),
}


def git_blob(path: pathlib.Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def load_child(name: str):
    path, expected = CHILDREN[name]
    got = git_blob(path)
    if got != expected:
        raise ValueError(f"FAIL_CLOSED_CHILD_BLOB_{name}_{got}")
    spec = importlib.util.spec_from_file_location(f"precapture_{name}", path)
    if not spec or not spec.loader:
        raise ValueError(f"FAIL_CLOSED_CHILD_IMPORT_{name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, got


def safe_prefix(x: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", x):
        raise ValueError("FAIL_CLOSED_OUTPUT_PREFIX")
    return x


def write_json(path: pathlib.Path, obj: dict) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_utc(x: str) -> datetime:
    d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("FAIL_CLOSED_CUTOFF_TZ_REQUIRED")
    return d.astimezone(timezone.utc)


def capture(
    racecard_url: str,
    expected_venue: str,
    expected_date: str,
    circumference_m: float,
    out_dir: pathlib.Path,
    prefix: str,
    timeout: int = 25,
) -> dict:
    prefix = safe_prefix(prefix)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "pit": out_dir / f"{prefix}_PIT_CUTOFF.json",
        "manifest": out_dir / f"{prefix}_DAY1_MANIFEST.json",
        "pre_csv": out_dir / f"{prefix}_PRE_ROWS.csv",
        "acquire_receipt": out_dir / f"{prefix}_PRE_ACQUIRE_RECEIPT.json",
        "orchestrator": out_dir / f"{prefix}_ORCHESTRATOR_RECEIPT.json",
    }
    completed: list[str] = []
    child_blobs: dict[str, str] = {}

    try:
        pit, child_blobs["pit"] = load_child("pit")
        manifest_mod, child_blobs["manifest"] = load_child("manifest")
        acquire_mod, child_blobs["acquire"] = load_child("acquire")

        pit_rec = pit.extract(
            racecard_url,
            expected_venue,
            expected_date,
            timeout,
        )
        if pit_rec.get("status") != "POSITIVE_RACECARD_TO_RACEPROGRAM_PIT_CUTOFF_CAPTURED_PRE_ONLY":
            raise ValueError("FAIL_CLOSED_PIT_STATUS")
        if pit_rec.get("captured_before_first_race_pit_cutoff") is not True:
            raise ValueError("FAIL_CLOSED_PIT_NOT_PRE")
        cutoff_utc = pit_rec.get("first_race_pit_cutoff_utc")
        cutoff = parse_utc(cutoff_utc)
        if datetime.now(timezone.utc) >= cutoff:
            raise ValueError("FAIL_CLOSED_AFTER_PIT_STAGE")
        write_json(paths["pit"], pit_rec)
        completed.append("PIT_CUTOFF")

        manifest = manifest_mod.build_manifest(
            racecard_url,
            expected_venue,
            expected_date,
            circumference_m,
            cutoff_utc,
            timeout,
        )
        if manifest.get("status") != "POSITIVE_DAY1_RACEDETAIL_HREF_MANIFEST_CAPTURED_PRE_ONLY":
            raise ValueError("FAIL_CLOSED_MANIFEST_STATUS")
        if manifest.get("pit_cutoff_utc") != cutoff.isoformat():
            raise ValueError("FAIL_CLOSED_CUTOFF_HANDOFF_MISMATCH")
        if manifest.get("day1_confirmed") is not True:
            raise ValueError("FAIL_CLOSED_MANIFEST_DAY1")
        if datetime.now(timezone.utc) >= cutoff:
            raise ValueError("FAIL_CLOSED_AFTER_MANIFEST_STAGE")
        write_json(paths["manifest"], manifest)
        completed.append("DAY1_MANIFEST")

        rows, acq_rec = acquire_mod.acquire(manifest, timeout)
        if acq_rec.get("status") != "WHOLE_DAY_DAY1_PRE_CAPTURED_FAIL_CLOSED_READY_FOR_IDENTITY":
            raise ValueError("FAIL_CLOSED_ACQUIRE_STATUS")
        if acq_rec.get("pit_cutoff_utc") != cutoff.isoformat():
            raise ValueError("FAIL_CLOSED_ACQUIRE_CUTOFF_MISMATCH")
        if acq_rec.get("successful_races") != len(manifest.get("detail_urls") or []):
            raise ValueError("FAIL_CLOSED_RACE_COUNT_HANDOFF_MISMATCH")
        if acq_rec.get("captured_before_pit_cutoff") is not True:
            raise ValueError("FAIL_CLOSED_ACQUIRE_NOT_PRE")

        acquire_mod.write_csv(rows, paths["pre_csv"])
        write_json(paths["acquire_receipt"], acq_rec)
        completed.append("STRICT_PRE_ACQUIRE")

        forbidden_truth = {
            "result_join_authorized": False,
            "model_fit_authorized": False,
            "support_increment_authorized_now": 0,
            "identity_mapping_performed": False,
            "same_race_assignment_performed": False,
            "main_or_runtime_mutation": False,
        }
        receipt = {
            "record": "KEIRIN_KDREAMS_PROSPECTIVE_PRECAPTURE_ORCHESTRATOR_RECEIPT_v1",
            "status": "WHOLE_DAY_DAY1_PRE_CAPTURE_CHAIN_COMPLETED_READY_FOR_IDENTITY_ONLY",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "event": {
                "race_date": expected_date,
                "venue": expected_venue,
                "circumference_m": float(circumference_m),
                "day": "Day1",
            },
            "source_racecard_url": racecard_url,
            "first_race_pit_cutoff_utc": cutoff.isoformat(),
            "completed_stages": completed,
            "child_git_blobs": child_blobs,
            "successful_races": acq_rec["successful_races"],
            "pre_rows": acq_rec["pre_rows"],
            "outputs": {
                "pit_cutoff": str(paths["pit"]),
                "day1_manifest": str(paths["manifest"]),
                "pre_rows_csv": str(paths["pre_csv"]),
                "pre_acquire_receipt": str(paths["acquire_receipt"]),
            },
            "output_sha256": {
                "pit_cutoff": sha256_file(paths["pit"]),
                "day1_manifest": sha256_file(paths["manifest"]),
                "pre_rows_csv": sha256_file(paths["pre_csv"]),
                "pre_acquire_receipt": sha256_file(paths["acquire_receipt"]),
            },
            "raw_html_persisted": False,
            "raw_html_printed": False,
            "result_accessed": False,
            "payout_accessed": False,
            "odds_accessed": False,
            "forecast_accessed": False,
            "race_id_guessed": False,
            **forbidden_truth,
        }
        write_json(paths["orchestrator"], receipt)
        return receipt

    except Exception as exc:
        fail = {
            "record": "KEIRIN_KDREAMS_PROSPECTIVE_PRECAPTURE_ORCHESTRATOR_RECEIPT_v1",
            "status": "FAIL_CLOSED_PROSPECTIVE_PRECAPTURE_CHAIN_INCOMPLETE",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "event": {
                "race_date": expected_date,
                "venue": expected_venue,
                "circumference_m": float(circumference_m),
                "day": "Day1",
            },
            "source_racecard_url": racecard_url,
            "completed_stages": completed,
            "child_git_blobs": child_blobs,
            "fatal_error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "partial_sanitized_outputs_may_exist": bool(completed),
            "raw_html_persisted": False,
            "raw_html_printed": False,
            "result_accessed": False,
            "payout_accessed": False,
            "odds_accessed": False,
            "forecast_accessed": False,
            "race_id_guessed": False,
            "support_increment_authorized_now": 0,
            "identity_mapping_performed": False,
            "same_race_assignment_performed": False,
            "result_join_authorized": False,
            "model_fit_authorized": False,
            "main_or_runtime_mutation": False,
        }
        write_json(paths["orchestrator"], fail)
        raise


def selftest() -> dict:
    pit, pit_blob = load_child("pit")
    manifest_mod, manifest_blob = load_child("manifest")
    acquire_mod, acquire_blob = load_child("acquire")

    pit_self = pit.selftest()
    manifest_self = manifest_mod.selftest()
    acquire_self = acquire_mod.selftest()

    handoff = {
        "record": "synthetic",
        "day1_confirmed": True,
        "pit_cutoff_utc": "2099-01-01T00:00:00+00:00",
        "event": {
            "race_date": "2098-12-31",
            "venue": "川崎",
            "circumference_m": 400.0,
            "day": "Day1",
        },
        "detail_urls": [
            f"https://keirin.kdreams.jp/kawasaki/racedetail/{1000+i}/"
            for i in range(1, 6)
        ],
    }
    e, cutoff, urls = acquire_mod.validate_manifest(handoff)

    tests = {
        "pit_blob_pinned": pit_blob == CHILDREN["pit"][1],
        "manifest_blob_pinned": manifest_blob == CHILDREN["manifest"][1],
        "acquire_blob_pinned": acquire_blob == CHILDREN["acquire"][1],
        "pit_child_selftest_pass": pit_self.get("status") == "PASS",
        "manifest_child_selftest_pass": manifest_self.get("status") == "PASS",
        "acquire_child_selftest_pass": acquire_self.get("status") == "PASS",
        "handoff_event_preserved": e["venue"] == "川崎" and e["race_date"] == "2098-12-31",
        "handoff_cutoff_timezone_preserved": cutoff.isoformat() == "2099-01-01T00:00:00+00:00",
        "handoff_five_unique_detail_urls": len(urls) == 5 and len(set(urls)) == 5,
        "safe_prefix_accepts_versioned_name": safe_prefix("KEIRIN_NARA_SEP10_v1") == "KEIRIN_NARA_SEP10_v1",
    }
    try:
        safe_prefix("../escape")
        tests["unsafe_prefix_rejected"] = False
    except ValueError:
        tests["unsafe_prefix_rejected"] = True

    return {
        "record": "KEIRIN_KDREAMS_PROSPECTIVE_PRECAPTURE_ORCHESTRATOR_SELFTEST_v1",
        "status": "PASS" if all(tests.values()) else "FAIL",
        "tests": tests,
        "network_access": False,
        "live_pre_validation": False,
        "identity_mapping_performed": False,
        "support_increment_authorized_now": 0,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "race_id_guessing": False,
        "result_join_authorized": False,
        "model_fit_authorized": False,
        "main_or_runtime_mutation": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("capture")
    p.add_argument("--racecard-url", required=True)
    p.add_argument("--expected-venue", required=True)
    p.add_argument("--expected-date", required=True)
    p.add_argument("--circumference-m", required=True, type=float)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--timeout", type=int, default=25)
    a = ap.parse_args()

    if a.cmd == "selftest":
        out = selftest()
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 0 if out["status"] == "PASS" else 2

    try:
        out = capture(
            a.racecard_url,
            a.expected_venue,
            a.expected_date,
            a.circumference_m,
            pathlib.Path(a.out_dir),
            a.prefix,
            a.timeout,
        )
        print(json.dumps({
            "record": out["record"],
            "status": out["status"],
            "successful_races": out["successful_races"],
            "pre_rows": out["pre_rows"],
            "result_join_authorized": False,
            "support_increment_authorized_now": 0,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "record": "KEIRIN_KDREAMS_PROSPECTIVE_PRECAPTURE_ORCHESTRATOR_RECEIPT_v1",
            "status": "FAIL_CLOSED_PROSPECTIVE_PRECAPTURE_CHAIN_INCOMPLETE",
            "fatal_error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "result_accessed": False,
            "support_increment_authorized_now": 0,
            "result_join_authorized": False,
            "model_fit_authorized": False,
            "main_or_runtime_mutation": False,
        }, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
