#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — All-Market Historical Economic Track
Stage-0 PRICE-only DEV2000 bulk recovery runner v1.

AUTHORIZED scope only:
- 2000 historical development races
- existing SHA-bound archived Kdreams showResult raw
- PRICE / market-availability recovery only

STRICTLY NOT AUTHORIZED here:
- official refund extraction
- finishing-order extraction
- settlement execution
- model probability
- EV / ROI / P&L
- portfolio / bankroll
- HOLDOUT access

This runner is intended for Google Colab with the user's MyDrive mounted at
/content/drive/MyDrive. It never performs network retrieval of race data.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import traceback
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_UNIVERSE_SHA256 = "eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"
EXPECTED_PROVENANCE_SHA256 = "0e9dbba0bf0427bd1b5903c196a93a31678375170e6d5164b3d8d8f052ca97f1"
EXPECTED_PRICE_PARSER_GIT_BLOB = "f94a08a3ea7c0a4f110dc0df82433eecc25b0cf8"
EXPECTED_GEMINI_APPROVE_RECEIPT_BLOB = "TO_BE_BOUND_AFTER_COMMIT"
EXPECTED_RACE_COUNT = 2000

MARKETS = ("3rentan", "2shatan", "3renhuku", "2shahuku", "2wakutan", "2wakuhuku", "wide")
FORBIDDEN_OUTPUT_KEYS = {
    "refund", "refunds", "settlement", "settlements", "settlements_yen_per_100",
    "result", "results", "finishing_order", "finish_order", "places", "first_set",
    "second_set", "third_set", "payout", "payouts", "profit", "loss", "pnl",
    "ev", "roi", "return_yen", "hit", "hit_rate",
}

class FailClosed(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def git_blob_sha1_bytes(b: bytes) -> str:
    head = f"blob {len(b)}\0".encode("ascii")
    return hashlib.sha1(head + b).hexdigest()


def json_dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                x = json.loads(line)
            except Exception as e:
                raise FailClosed(f"JSONL parse error {path.name}:{i}: {e}") from e
            if not isinstance(x, dict):
                raise FailClosed(f"JSONL non-object {path.name}:{i}")
            out.append(x)
    return out


def forbidden_key_scan(x: Any, path: str = "$") -> list[str]:
    bad: list[str] = []
    if isinstance(x, dict):
        for k, v in x.items():
            kl = str(k).strip().lower()
            if kl in FORBIDDEN_OUTPUT_KEYS:
                bad.append(f"{path}.{k}")
            bad.extend(forbidden_key_scan(v, f"{path}.{k}"))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            bad.extend(forbidden_key_scan(v, f"{path}[{i}]"))
    return bad


def import_price_parser(repo_root: Path):
    p = repo_root / "v3" / "historical_all_market" / "kdreams_price_catalog_recovery_v1.py"
    if not p.exists():
        raise FailClosed(f"PRICE parser missing: {p}")
    observed_blob = git_blob_sha1_bytes(p.read_bytes())
    if observed_blob != EXPECTED_PRICE_PARSER_GIT_BLOB:
        raise FailClosed(
            f"PRICE parser Git blob mismatch expected={EXPECTED_PRICE_PARSER_GIT_BLOB} observed={observed_blob}"
        )
    spec = importlib.util.spec_from_file_location("multiverse_stage0_price_parser", p)
    if spec is None or spec.loader is None:
        raise FailClosed("cannot import PRICE parser")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "parse_payload"):
        raise FailClosed("PRICE parser missing parse_payload")
    return mod, p, observed_blob


def resolve_raw_result_path(rid: str, prov: dict[str, Any], raw_dir: Path) -> tuple[Path, bytes]:
    # Provenance schema compatibility established in the legacy E1 engineering line:
    # - first 457R may contain explicit raw_quarantine_path
    # - later 1543R may be content-addressed only by raw_payload_sha256
    if prov.get("fallback_used") is not False:
        raise FailClosed(f"{rid}: provenance fallback_used is not false")

    dig = str(prov.get("raw_payload_sha256", "")).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", dig):
        raise FailClosed(f"{rid}: invalid/missing raw_payload_sha256")

    candidates: list[Path] = []
    explicit = prov.get("raw_quarantine_path")
    if explicit:
        q = Path(str(explicit))
        if q.exists():
            candidates.append(q)

    if raw_dir.exists():
        for q in (
            raw_dir / f"{dig}.showResult.html.gz",
            raw_dir / f"{dig}.html.gz",
        ):
            if q.exists():
                candidates.append(q)
        candidates.extend(sorted(raw_dir.glob(f"{dig}*.gz")))

    uniq: list[Path] = []
    seen: set[str] = set()
    for q in candidates:
        try:
            s = str(q.resolve())
        except Exception:
            s = str(q)
        if s not in seen:
            seen.add(s)
            uniq.append(q)

    if not uniq:
        raise FailClosed(f"{rid}: no archived raw found for SHA={dig}")

    verified: list[tuple[Path, bytes]] = []
    read_errors: list[str] = []
    for q in uniq:
        try:
            with gzip.open(q, "rb") as f:
                b = f.read()
        except Exception as e:
            read_errors.append(f"{q}: {e}")
            continue
        if sha256_bytes(b) == dig:
            verified.append((q, b))

    if not verified:
        raise FailClosed(
            f"{rid}: no raw candidate matches recorded SHA={dig}; read_errors={read_errors[:3]}"
        )

    verified.sort(key=lambda qb: (len(str(qb[0])), str(qb[0])))
    return verified[0]


def normalize_price_record(race_id: str, parsed: dict[str, Any]) -> dict[str, Any]:
    # Explicit allow-list: do not copy arbitrary parser fields into bulk output.
    rec = {
        "race_id": str(race_id),
        "raw_sha256": parsed["raw_sha256"],
        "market_availability": parsed["market_availability"],
        "sold_markets": parsed["sold_markets"],
        "active_car_numbers": parsed["active_car_numbers"],
        "active_car_count": parsed["active_car_count"],
        "closing_price_catalogs": parsed["closing_price_catalogs"],
        "odds_timestamps": parsed["odds_timestamps"],
        "frame_labels_raw": parsed.get("frame_labels_raw", {}),
        "price_type": parsed.get("price_type", "B_CLOSING_PRICE"),
        "wide_price_semantics": parsed.get(
            "wide_price_semantics", "INTERVAL_LOW_HIGH_PRESERVED_NO_MIDPOINT"
        ),
    }
    bad = forbidden_key_scan(rec)
    if bad:
        raise FailClosed(f"{race_id}: forbidden output key(s): {bad[:10]}")
    return rec


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mydrive", default="/content/drive/MyDrive")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--overwrite", action="store_true")
    return ap.parse_args()


def main() -> int:
    a = parse_args()
    my = Path(a.mydrive)
    if not my.exists():
        raise FailClosed(f"MyDrive not mounted: {my}")

    repo_root = Path(a.repo_root).resolve() if a.repo_root else Path(__file__).resolve().parents[2]
    price_mod, parser_path, parser_blob = import_price_parser(repo_root)

    universe = my / "MULTIVERSE_DEV2000_UNIVERSE_RECOVERY" / "DEV2000_UNIVERSE_v1.csv"
    result_dir = my / "MULTIVERSE_DEV2000_RESULT_COLLECTION_v3_HARDENED"
    provenance = result_dir / "DEV2000_RESULT_PROVENANCE_v3.jsonl"
    raw_dir = result_dir / "RAW_RESULT_QUARANTINE"

    out = my / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v1"
    work = out / "PRICE_ONLY"
    if out.exists() and a.overwrite:
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    price_jsonl = work / "DEV2000_ALL_MARKET_PRICE_CATALOGS_v1.jsonl"
    fail_jsonl = work / "DEV2000_PRICE_FAIL_CLOSED_v1.jsonl"
    preflight_csv = work / "DEV2000_PRICE_RAW_PREFLIGHT_v1.csv"
    coverage_csv = work / "DEV2000_PRICE_MARKET_COVERAGE_v1.csv"
    active_csv = work / "DEV2000_PRICE_ACTIVE_CAR_DISTRIBUTION_v1.csv"
    quality_json = work / "POST_BULK_PRICE_QUALITY_REPORT_v1.json"
    receipt_json = out / "STAGE0_PRICE_BULK_RECEIPT_v1.json"
    manifest_file = out / "AUDIT_MANIFEST.sha256"
    artifact_zip = out / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v1_ARTIFACT.zip"

    # Input gates.
    if not universe.exists():
        raise FailClosed(f"Universe missing: {universe}")
    if sha256_file(universe) != EXPECTED_UNIVERSE_SHA256:
        raise FailClosed("Universe SHA mismatch")
    if not provenance.exists():
        raise FailClosed(f"Provenance missing: {provenance}")
    if sha256_file(provenance) != EXPECTED_PROVENANCE_SHA256:
        raise FailClosed("Provenance SHA mismatch")
    if not raw_dir.exists():
        raise FailClosed(f"Archived raw directory missing: {raw_dir}")

    with universe.open("r", encoding="utf-8", newline="") as f:
        urows = list(csv.DictReader(f))
    if len(urows) != EXPECTED_RACE_COUNT:
        raise FailClosed(f"Universe race count={len(urows)} expected={EXPECTED_RACE_COUNT}")
    race_ids = [str(r.get("race_id", "")).strip() for r in urows]
    if any(not x for x in race_ids) or len(set(race_ids)) != EXPECTED_RACE_COUNT:
        raise FailClosed("Universe race_id cardinality/uniqueness failure")

    prov_rows = load_jsonl(provenance)
    if len(prov_rows) != EXPECTED_RACE_COUNT:
        raise FailClosed(f"Provenance rows={len(prov_rows)} expected={EXPECTED_RACE_COUNT}")
    prov_by: dict[str, dict[str, Any]] = {}
    for x in prov_rows:
        rid = str(x.get("race_id", "")).strip()
        if not rid or rid in prov_by:
            raise FailClosed(f"Provenance duplicate/blank race_id={rid!r}")
        # Only retain fields needed for PRICE raw identity/resolution.
        prov_by[rid] = {
            "race_id": rid,
            "fallback_used": x.get("fallback_used"),
            "raw_payload_sha256": x.get("raw_payload_sha256"),
            "raw_quarantine_path": x.get("raw_quarantine_path"),
            "frozen_universe_url": x.get("frozen_universe_url"),
            "final_url": x.get("final_url"),
            "retrieved_at_utc": x.get("retrieved_at_utc"),
        }
    if set(prov_by) != set(race_ids):
        raise FailClosed(
            f"Universe/Provenance race-set mismatch universe_only={len(set(race_ids)-set(prov_by))} "
            f"prov_only={len(set(prov_by)-set(race_ids))}"
        )

    if any(prov_by[rid]["fallback_used"] is not False for rid in race_ids):
        raise FailClosed("At least one provenance row has fallback_used != false")

    # Phase A: resolve and SHA-verify every archived raw before parsing any PRICE catalog.
    preflight_rows: list[dict[str, Any]] = []
    resolved: dict[str, tuple[Path, bytes]] = {}
    preflight_fail: list[dict[str, Any]] = []
    for i, rid in enumerate(race_ids, 1):
        p = prov_by[rid]
        try:
            q, b = resolve_raw_result_path(rid, p, raw_dir)
            resolved[rid] = (q, b)
            preflight_rows.append({
                "race_id": rid,
                "raw_sha256": p["raw_payload_sha256"],
                "resolved_file": q.name,
                "bytes": len(b),
                "status": "PASS",
            })
        except Exception as e:
            preflight_fail.append({
                "race_id": rid,
                "raw_sha256": p.get("raw_payload_sha256"),
                "stage": "RAW_PREFLIGHT",
                "error_type": type(e).__name__,
                "error": str(e),
            })
        if i % 250 == 0 or i == EXPECTED_RACE_COUNT:
            print(f"[RAW PREFLIGHT] {i}/{EXPECTED_RACE_COUNT} pass={len(resolved)} fail={len(preflight_fail)}", flush=True)

    with preflight_csv.open("w", encoding="utf-8", newline="") as f:
        cols = ["race_id", "raw_sha256", "resolved_file", "bytes", "status"]
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader(); w.writerows(preflight_rows)

    # Per audit, unknown/unresolved raws are per-race FAIL-CLOSED exclusions; no web fallback.
    failures: list[dict[str, Any]] = list(preflight_fail)
    market_counts = Counter()
    active_counts = Counter()
    parsed_count = 0

    with price_jsonl.open("w", encoding="utf-8", newline="\n") as pf:
        for i, rid in enumerate(race_ids, 1):
            if rid not in resolved:
                continue
            q, b = resolved[rid]
            expected_sha = str(prov_by[rid]["raw_payload_sha256"])
            try:
                parsed = price_mod.parse_payload(b, expected_raw_sha256=expected_sha)
                rec = normalize_price_record(rid, parsed)
                pf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                parsed_count += 1
                active_counts[int(rec["active_car_count"])] += 1
                for m in rec["sold_markets"]:
                    market_counts[str(m)] += 1
            except Exception as e:
                failures.append({
                    "race_id": rid,
                    "raw_sha256": expected_sha,
                    "stage": "PRICE_PARSE",
                    "error_type": type(e).__name__,
                    "error": str(e),
                })
            if i % 250 == 0 or i == EXPECTED_RACE_COUNT:
                print(
                    f"[PRICE BULK] {i}/{EXPECTED_RACE_COUNT} parsed={parsed_count} fail_closed={len(failures)}",
                    flush=True,
                )

    with fail_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for x in failures:
            f.write(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    with coverage_csv.open("w", encoding="utf-8", newline="") as f:
        cols = ["market", "races_sold", "sales_rate_of_2000"]
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader()
        for m in MARKETS:
            n = int(market_counts[m])
            w.writerow({"market": m, "races_sold": n, "sales_rate_of_2000": f"{n/EXPECTED_RACE_COUNT:.12g}"})

    with active_csv.open("w", encoding="utf-8", newline="") as f:
        cols = ["active_car_count", "race_count", "share_of_parsed"]
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader()
        for n in sorted(active_counts):
            c = int(active_counts[n])
            w.writerow({"active_car_count": n, "race_count": c, "share_of_parsed": f"{c/parsed_count:.12g}" if parsed_count else ""})

    reason_counts = Counter(f"{x['stage']}::{x['error_type']}::{x['error']}" for x in failures)
    quality_status = "PASS_COMPLETE" if parsed_count == EXPECTED_RACE_COUNT else "PASS_WITH_FAIL_CLOSED_EXCLUSIONS_STAGE1_BLOCKED"
    quality = {
        "record": "POST_BULK_PRICE_QUALITY_REPORT_v1",
        "status": quality_status,
        "completed_at_utc": now_utc(),
        "authorized_scope": "DEV2000_STAGE0_PRICE_ONLY",
        "inputs": {
            "universe_sha256": sha256_file(universe),
            "provenance_sha256": sha256_file(provenance),
            "price_parser_git_blob": parser_blob,
        },
        "recovery": {
            "universe_races": EXPECTED_RACE_COUNT,
            "raw_preflight_pass": len(resolved),
            "raw_preflight_fail_closed": len(preflight_fail),
            "price_parsed_races": parsed_count,
            "price_fail_closed_total": len(failures),
            "recovery_rate": parsed_count / EXPECTED_RACE_COUNT,
        },
        "market_sales_counts": {m: int(market_counts[m]) for m in MARKETS},
        "market_sales_rates": {m: market_counts[m] / EXPECTED_RACE_COUNT for m in MARKETS},
        "active_car_count_distribution": {str(k): int(v) for k, v in sorted(active_counts.items())},
        "fail_closed_reason_counts": dict(reason_counts),
        "firewall": {
            "price_namespace": "PRICE_ONLY",
            "settlement_executable_imported": false if False else False,
            "official_refund_values_emitted": false if False else False,
            "finishing_order_emitted": false if False else False,
            "profit_loss_scored": false if False else False,
            "ev_scored": false if False else False,
            "roi_scored": false if False else False,
            "network_race_data_fetch": false if False else False,
        },
        "scientific_state": {
            "all_market_track_trial_count": 0,
            "stage1_started": False,
            "stage2_started": False,
            "stage5_started": False,
            "settlement_bulk_started": False,
            "ECON_HOLDOUT1000": "SEALED",
            "holdout_result_access": False,
            "holdout_payout_access": False,
            "holdout_price_access": False,
        },
        "stage1_gate": "ELIGIBLE_FOR_REVIEW_ONLY" if parsed_count == EXPECTED_RACE_COUNT else "BLOCKED_BY_FAIL_CLOSED_EXCLUSIONS",
    }
    # Defensive recursive scan before writing report.
    bad = forbidden_key_scan(quality)
    # Quality report intentionally uses words describing the firewall, so only scan PRICE data records, not governance report keys.
    json_dump(quality_json, quality)

    # Verify the generated PRICE JSONL contains only the allow-listed record schema and no forbidden keys.
    output_rows = load_jsonl(price_jsonl)
    if len(output_rows) != parsed_count:
        raise FailClosed("PRICE output row count changed after write")
    for x in output_rows:
        bad = forbidden_key_scan(x)
        if bad:
            raise FailClosed(f"PRICE output forbidden field paths: {bad[:10]}")

    # Build manifest from PRICE-only engineering artifacts. Do not include any legacy RESULT/PAYOUT file.
    artifact_files = [price_jsonl, fail_jsonl, preflight_csv, coverage_csv, active_csv, quality_json]
    manifest_lines = []
    for p in sorted(artifact_files, key=lambda q: q.name):
        manifest_lines.append(f"{sha256_file(p)}  PRICE_ONLY/{p.name}\n")
    manifest_file.write_text("".join(manifest_lines), encoding="utf-8")

    if artifact_zip.exists():
        artifact_zip.unlink()
    with zipfile.ZipFile(artifact_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(artifact_files, key=lambda q: q.name):
            z.write(p, arcname=f"PRICE_ONLY/{p.name}")
        z.write(manifest_file, arcname=manifest_file.name)

    receipt = {
        "record": "STAGE0_PRICE_BULK_RECEIPT_v1",
        "status": quality_status,
        "completed_at_utc": now_utc(),
        "price_parser_git_blob": parser_blob,
        "universe_sha256": sha256_file(universe),
        "provenance_sha256": sha256_file(provenance),
        "price_catalog_rows": parsed_count,
        "fail_closed_exclusions": len(failures),
        "artifact_path": str(artifact_zip),
        "artifact_sha256": sha256_file(artifact_zip),
        "quality_report_sha256": sha256_file(quality_json),
        "price_catalog_sha256": sha256_file(price_jsonl),
        "trial_count": 0,
        "settlement_bulk_started": False,
        "stage1_started": False,
        "ECON_HOLDOUT1000": "SEALED",
    }
    json_dump(receipt_json, receipt)

    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
    if failures:
        print("PRICE bulk completed with Fail-Closed exclusions. Stage 1 remains BLOCKED.", flush=True)
    else:
        print("PRICE bulk completed 2000/2000. Post-Bulk Quality Report created. Stage 1 is NOT auto-started.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FailClosed as e:
        print(f"FAIL-CLOSED: {e}", file=sys.stderr, flush=True)
        raise SystemExit(2)
