#!/usr/bin/env python3
"""Build a cryptographically bound KEIRIN PRE source receipt from a local snapshot.

No network access, no calendar discovery, no outcome access. The caller must save the
source snapshot before invoking this tool. The tool only validates metadata and hashes
that immutable local file for use by keirin_prospective_cutoff_guard_v2.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

ALLOWED_TRUST_CLASSES = {"OFFICIAL", "PRIMARY", "SECONDARY"}


def parse_ts(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("FAIL_CLOSED:missing_retrieved_at")
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("FAIL_CLOSED:invalid_retrieved_at") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("FAIL_CLOSED:timezone_required")
    return dt.isoformat()


def resolve_snapshot(repo_root: Path, value: str) -> tuple[Path, str]:
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
    return candidate, rel.as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_receipt(
    *,
    repo_root: Path,
    source_id: str,
    source_locator: str,
    trust_class: str,
    retrieved_at: str,
    http_status: int,
    snapshot_path: str,
) -> dict[str, object]:
    source_id = str(source_id).strip()
    source_locator = str(source_locator).strip()
    trust_class = str(trust_class).upper().strip()
    if not source_id:
        raise ValueError("FAIL_CLOSED:source_id_required")
    if not source_locator:
        raise ValueError("FAIL_CLOSED:source_locator_required")
    if trust_class not in ALLOWED_TRUST_CLASSES:
        raise ValueError("FAIL_CLOSED:invalid_trust_class")
    if http_status != 200:
        raise ValueError("FAIL_CLOSED:http_status_not_200")
    ts = parse_ts(retrieved_at)
    snapshot, rel = resolve_snapshot(repo_root, snapshot_path)
    return {
        "source_id": source_id,
        "source_locator": source_locator,
        "trust_class": trust_class,
        "retrieved_at": ts,
        "http_status": 200,
        "snapshot_path": rel,
        "content_sha256": sha256_file(snapshot),
    }


def selftest() -> dict[str, object]:
    tests: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        snap = root / "evidence" / "racecard.json"
        snap.parent.mkdir(parents=True)
        snap.write_bytes(b'{"venue":"TEST","race":1}')
        receipt = build_receipt(
            repo_root=root,
            source_id="official-racecard",
            source_locator="https://example.invalid/racecard",
            trust_class="OFFICIAL",
            retrieved_at="2026-09-11T10:00:00+09:00",
            http_status=200,
            snapshot_path="evidence/racecard.json",
        )
        tests["valid_receipt_passes"] = (
            receipt["content_sha256"] == sha256_file(snap)
            and receipt["trust_class"] == "OFFICIAL"
        )

        for name, kwargs in [
            ("naive_timestamp_rejected", {"retrieved_at": "2026-09-11T10:00:00"}),
            ("non_200_rejected", {"http_status": 404}),
            ("path_traversal_rejected", {"snapshot_path": "../racecard.json"}),
            ("missing_snapshot_rejected", {"snapshot_path": "evidence/missing.json"}),
            ("invalid_trust_class_rejected", {"trust_class": "UNKNOWN"}),
        ]:
            base = dict(
                repo_root=root,
                source_id="official-racecard",
                source_locator="https://example.invalid/racecard",
                trust_class="OFFICIAL",
                retrieved_at="2026-09-11T10:00:00+09:00",
                http_status=200,
                snapshot_path="evidence/racecard.json",
            )
            base.update(kwargs)
            try:
                build_receipt(**base)
                tests[name] = False
            except ValueError:
                tests[name] = True

    return {
        "record": "KEIRIN_PRE_SOURCE_RECEIPT_BUILDER_SELFTEST_v1",
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
    build = sub.add_parser("build")
    build.add_argument("--repo-root", default=".")
    build.add_argument("--source-id", required=True)
    build.add_argument("--source-locator", required=True)
    build.add_argument("--trust-class", required=True, choices=sorted(ALLOWED_TRUST_CLASSES))
    build.add_argument("--retrieved-at", required=True)
    build.add_argument("--http-status", required=True, type=int)
    build.add_argument("--snapshot-path", required=True)
    args = parser.parse_args()

    if args.cmd == "selftest":
        out = selftest()
        print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if out["status"] == "PASS" else 2

    try:
        out = build_receipt(
            repo_root=Path(args.repo_root),
            source_id=args.source_id,
            source_locator=args.source_locator,
            trust_class=args.trust_class,
            retrieved_at=args.retrieved_at,
            http_status=args.http_status,
            snapshot_path=args.snapshot_path,
        )
    except (OSError, ValueError) as exc:
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
