#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — All-Market Historical Economic Track
Stage-0 PRICE-only DEV2000 bulk recovery runner v2.

Routine-engineering hardening of v1; scientific semantics unchanged.
- PRICE / market availability only.
- No RESULT/PAYOUT/refund/settlement/probability/EV/ROI.
- No network race-data retrieval.
- One-pass Drive raw filename index (avoids repeated large-folder glob scans).
- Fatal errors are persisted to Drive with traceback instead of being hidden by
  an outer CalledProcessError.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
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
EXPECTED_APPROVE_RECEIPT_GIT_BLOB = "8643684cf7bf0165968ae667e17e546936a3611d"
EXPECTED_RACE_COUNT = 2000

MARKETS = ("3rentan", "2shatan", "3renhuku", "2shahuku", "2wakutan", "2wakuhuku", "wide")
PRICE_RECORD_ALLOWED_KEYS = {
    "race_id", "raw_sha256", "market_availability", "sold_markets",
    "active_car_numbers", "active_car_count", "closing_price_catalogs",
    "odds_timestamps", "frame_labels_raw", "price_type", "wide_price_semantics",
}
FORBIDDEN_PRICE_KEYS = {
    "refund", "refunds", "settlement", "settlements", "settlements_yen_per_100",
    "result", "results", "finishing_order", "finish_order", "places", "first_set",
    "second_set", "third_set", "payout", "payouts", "profit", "loss", "pnl",
    "ev", "roi", "return_yen", "hit", "hit_rate",
}
RAW_NAME_RE = re.compile(r"^([0-9a-f]{64}).*\.gz$")


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
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()


def json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
            if kl in FORBIDDEN_PRICE_KEYS:
                bad.append(f"{path}.{k}")
            bad.extend(forbidden_key_scan(v, f"{path}.{k}"))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            bad.extend(forbidden_key_scan(v, f"{path}[{i}]"))
    return bad


def import_bound_price_parser(repo_root: Path):
    p = repo_root / "v3" / "historical_all_market" / "kdreams_price_catalog_recovery_v1.py"
    if not p.exists():
        raise FailClosed(f"PRICE parser missing: {p}")
    observed = git_blob_sha1_bytes(p.read_bytes())
    if observed != EXPECTED_PRICE_PARSER_GIT_BLOB:
        raise FailClosed(f"PRICE parser blob mismatch expected={EXPECTED_PRICE_PARSER_GIT_BLOB} observed={observed}")
    spec = importlib.util.spec_from_file_location("multiverse_stage0_price_parser", p)
    if spec is None or spec.loader is None:
        raise FailClosed("cannot create PRICE parser import spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "parse_payload"):
        raise FailClosed("PRICE parser missing parse_payload")
    return mod, observed


def verify_approve_receipt(repo_root: Path) -> str:
    p = repo_root / "v3" / "historical_all_market" / "governance" / "INDEPENDENT_GEMINI_STAGE0_FINAL_APPROVE_RECEIPT_v1.json"
    if not p.exists():
        raise FailClosed(f"APPROVE receipt missing: {p}")
    blob = git_blob_sha1_bytes(p.read_bytes())
    if blob != EXPECTED_APPROVE_RECEIPT_GIT_BLOB:
        raise FailClosed(f"APPROVE receipt blob mismatch expected={EXPECTED_APPROVE_RECEIPT_GIT_BLOB} observed={blob}")
    x = json.loads(p.read_text(encoding="utf-8"))
    auth = x.get("authorization", {})
    if x.get("verdict") != "APPROVE":
        raise FailClosed("APPROVE receipt verdict is not APPROVE")
    if auth.get("price_only_stage0_bulk_2000") != "AUTHORIZED":
        raise FailClosed("PRICE bulk is not authorized by receipt")
    if auth.get("settlement_bulk_now") != "PROHIBITED":
        raise FailClosed("Settlement prohibition missing from receipt")
    return blob


def build_raw_index(raw_dir: Path) -> tuple[dict[str, Path], dict[str, list[str]]]:
    if not raw_dir.is_dir():
        raise FailClosed(f"archived raw directory missing: {raw_dir}")
    index: dict[str, Path] = {}
    duplicates: dict[str, list[str]] = {}
    scanned = 0
    for q in raw_dir.iterdir():
        if not q.is_file():
            continue
        m = RAW_NAME_RE.match(q.name)
        if not m:
            continue
        scanned += 1
        dig = m.group(1)
        if dig in index:
            duplicates.setdefault(dig, [index[dig].name]).append(q.name)
        else:
            index[dig] = q
    if scanned == 0:
        raise FailClosed(f"no SHA-addressed gzip raw files found in {raw_dir}")
    print(f"[RAW INDEX] scanned={scanned} unique_sha={len(index)} duplicate_sha={len(duplicates)}", flush=True)
    return index, duplicates


def resolve_raw_path(rid: str, prov: dict[str, Any], raw_index: dict[str, Path], duplicate_index: dict[str, list[str]]) -> Path:
    if prov.get("fallback_used") is not False:
        raise FailClosed(f"{rid}: fallback_used != false")
    dig = str(prov.get("raw_payload_sha256", "")).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", dig):
        raise FailClosed(f"{rid}: invalid/missing raw_payload_sha256")
    if dig in duplicate_index:
        raise FailClosed(f"{rid}: duplicate archived raw files for SHA={dig}: {duplicate_index[dig]}")
    q = raw_index.get(dig)
    if q is None:
        # Compatibility: explicit historical path may still be valid even if the
        # current directory index does not expose that item.
        explicit = prov.get("raw_quarantine_path")
        if explicit:
            e = Path(str(explicit))
            if e.is_file():
                q = e
    if q is None:
        raise FailClosed(f"{rid}: archived raw not found for SHA={dig}")
    return q


def read_verify_gzip(q: Path, expected_sha: str) -> bytes:
    try:
        with gzip.open(q, "rb") as f:
            b = f.read()
    except Exception as e:
        raise FailClosed(f"gzip read failed {q.name}: {e}") from e
    observed = sha256_bytes(b)
    if observed != expected_sha:
        raise FailClosed(f"raw SHA mismatch file={q.name} expected={expected_sha} observed={observed}")
    return b


def normalize_price_record(race_id: str, parsed: dict[str, Any]) -> dict[str, Any]:
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
        "wide_price_semantics": parsed.get("wide_price_semantics", "INTERVAL_LOW_HIGH_PRESERVED_NO_MIDPOINT"),
    }
    if set(rec) != PRICE_RECORD_ALLOWED_KEYS:
        raise FailClosed(f"{race_id}: PRICE output top-level schema mismatch")
    bad = forbidden_key_scan(rec)
    if bad:
        raise FailClosed(f"{race_id}: forbidden PRICE field(s): {bad[:10]}")
    return rec


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mydrive", default="/content/drive/MyDrive")
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--overwrite", action="store_true")
    return ap.parse_args()


def known_output_paths(out: Path) -> list[Path]:
    work = out / "PRICE_ONLY"
    return [
        work / "DEV2000_ALL_MARKET_PRICE_CATALOGS_v2.jsonl",
        work / "DEV2000_PRICE_FAIL_CLOSED_v2.jsonl",
        work / "DEV2000_PRICE_RAW_PREFLIGHT_v2.csv",
        work / "DEV2000_PRICE_MARKET_COVERAGE_v2.csv",
        work / "DEV2000_PRICE_ACTIVE_CAR_DISTRIBUTION_v2.csv",
        work / "POST_BULK_PRICE_QUALITY_REPORT_v2.json",
        out / "STAGE0_PRICE_BULK_RECEIPT_v2.json",
        out / "STAGE0_PRICE_BULK_FATAL_v2.json",
        out / "AUDIT_MANIFEST_v2.sha256",
        out / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v2_ARTIFACT.zip",
    ]


def run(a) -> int:
    my = Path(a.mydrive)
    repo_root = Path(a.repo_root).resolve()
    out = my / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v2"
    work = out / "PRICE_ONLY"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    if a.overwrite:
        for p in known_output_paths(out):
            try:
                if p.exists() and p.is_file():
                    p.unlink()
            except Exception as e:
                raise FailClosed(f"cannot clear prior output {p}: {e}") from e

    price_mod, parser_blob = import_bound_price_parser(repo_root)
    approve_blob = verify_approve_receipt(repo_root)

    universe = my / "MULTIVERSE_DEV2000_UNIVERSE_RECOVERY" / "DEV2000_UNIVERSE_v1.csv"
    result_dir = my / "MULTIVERSE_DEV2000_RESULT_COLLECTION_v3_HARDENED"
    provenance = result_dir / "DEV2000_RESULT_PROVENANCE_v3.jsonl"
    raw_dir = result_dir / "RAW_RESULT_QUARANTINE"

    if not universe.is_file():
        raise FailClosed(f"Universe missing: {universe}")
    universe_sha = sha256_file(universe)
    if universe_sha != EXPECTED_UNIVERSE_SHA256:
        raise FailClosed(f"Universe SHA mismatch expected={EXPECTED_UNIVERSE_SHA256} observed={universe_sha}")
    if not provenance.is_file():
        raise FailClosed(f"Provenance missing: {provenance}")
    provenance_sha = sha256_file(provenance)
    if provenance_sha != EXPECTED_PROVENANCE_SHA256:
        raise FailClosed(f"Provenance SHA mismatch expected={EXPECTED_PROVENANCE_SHA256} observed={provenance_sha}")

    print(f"[INPUT] universe_sha={universe_sha}", flush=True)
    print(f"[INPUT] provenance_sha={provenance_sha}", flush=True)
    print(f"[BINDING] price_parser_blob={parser_blob}", flush=True)
    print(f"[BINDING] approve_receipt_blob={approve_blob}", flush=True)

    with universe.open("r", encoding="utf-8", newline="") as f:
        urows = list(csv.DictReader(f))
    if len(urows) != EXPECTED_RACE_COUNT:
        raise FailClosed(f"Universe rows={len(urows)} expected={EXPECTED_RACE_COUNT}")
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
        prov_by[rid] = {
            "fallback_used": x.get("fallback_used"),
            "raw_payload_sha256": x.get("raw_payload_sha256"),
            "raw_quarantine_path": x.get("raw_quarantine_path"),
        }
    if set(prov_by) != set(race_ids):
        raise FailClosed(f"Universe/Provenance race-set mismatch universe_only={len(set(race_ids)-set(prov_by))} prov_only={len(set(prov_by)-set(race_ids))}")
    if any(prov_by[rid]["fallback_used"] is not False for rid in race_ids):
        raise FailClosed("At least one provenance row has fallback_used != false")

    raw_index, duplicate_index = build_raw_index(raw_dir)

    preflight_csv = work / "DEV2000_PRICE_RAW_PREFLIGHT_v2.csv"
    price_jsonl = work / "DEV2000_ALL_MARKET_PRICE_CATALOGS_v2.jsonl"
    fail_jsonl = work / "DEV2000_PRICE_FAIL_CLOSED_v2.jsonl"
    coverage_csv = work / "DEV2000_PRICE_MARKET_COVERAGE_v2.csv"
    active_csv = work / "DEV2000_PRICE_ACTIVE_CAR_DISTRIBUTION_v2.csv"
    quality_json = work / "POST_BULK_PRICE_QUALITY_REPORT_v2.json"
    receipt_json = out / "STAGE0_PRICE_BULK_RECEIPT_v2.json"
    manifest_file = out / "AUDIT_MANIFEST_v2.sha256"
    artifact_zip = out / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v2_ARTIFACT.zip"

    # Phase A: path + SHA preflight. Store paths only, not all decompressed bytes.
    resolved: dict[str, Path] = {}
    failures: list[dict[str, Any]] = []
    preflight_rows: list[dict[str, Any]] = []
    for i, rid in enumerate(race_ids, 1):
        p = prov_by[rid]
        dig = str(p.get("raw_payload_sha256", ""))
        try:
            q = resolve_raw_path(rid, p, raw_index, duplicate_index)
            b = read_verify_gzip(q, dig)
            resolved[rid] = q
            preflight_rows.append({"race_id": rid, "raw_sha256": dig, "resolved_file": q.name, "bytes": len(b), "status": "PASS"})
        except Exception as e:
            failures.append({"race_id": rid, "raw_sha256": dig, "stage": "RAW_PREFLIGHT", "error_type": type(e).__name__, "error": str(e)})
        if i % 250 == 0 or i == EXPECTED_RACE_COUNT:
            print(f"[RAW PREFLIGHT] {i}/{EXPECTED_RACE_COUNT} pass={len(resolved)} fail_closed={len(failures)}", flush=True)

    with preflight_csv.open("w", encoding="utf-8", newline="") as f:
        cols = ["race_id", "raw_sha256", "resolved_file", "bytes", "status"]
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader(); w.writerows(preflight_rows)

    market_counts = Counter()
    active_counts = Counter()
    parsed_count = 0
    with price_jsonl.open("w", encoding="utf-8", newline="\n") as pf:
        for i, rid in enumerate(race_ids, 1):
            q = resolved.get(rid)
            if q is None:
                continue
            dig = str(prov_by[rid]["raw_payload_sha256"])
            try:
                payload = read_verify_gzip(q, dig)
                parsed = price_mod.parse_payload(payload, expected_raw_sha256=dig)
                rec = normalize_price_record(rid, parsed)
                pf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                parsed_count += 1
                active_counts[int(rec["active_car_count"])] += 1
                for m in rec["sold_markets"]:
                    market_counts[str(m)] += 1
            except Exception as e:
                failures.append({"race_id": rid, "raw_sha256": dig, "stage": "PRICE_PARSE", "error_type": type(e).__name__, "error": str(e)})
            if i % 250 == 0 or i == EXPECTED_RACE_COUNT:
                print(f"[PRICE BULK] {i}/{EXPECTED_RACE_COUNT} parsed={parsed_count} fail_closed={len(failures)}", flush=True)

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
    complete = parsed_count == EXPECTED_RACE_COUNT and len(failures) == 0
    quality_status = "PASS_COMPLETE" if complete else "PASS_WITH_FAIL_CLOSED_EXCLUSIONS_STAGE1_BLOCKED"
    quality = {
        "record": "POST_BULK_PRICE_QUALITY_REPORT_v2",
        "status": quality_status,
        "completed_at_utc": now_utc(),
        "authorized_scope": "DEV2000_STAGE0_PRICE_ONLY",
        "inputs": {"universe_sha256": universe_sha, "provenance_sha256": provenance_sha, "price_parser_git_blob": parser_blob, "approve_receipt_git_blob": approve_blob},
        "recovery": {"universe_races": EXPECTED_RACE_COUNT, "raw_preflight_pass": len(resolved), "raw_preflight_fail_closed": sum(1 for x in failures if x["stage"] == "RAW_PREFLIGHT"), "price_parsed_races": parsed_count, "price_fail_closed_total": len(failures), "recovery_rate": parsed_count / EXPECTED_RACE_COUNT},
        "market_sales_counts": {m: int(market_counts[m]) for m in MARKETS},
        "market_sales_rates": {m: market_counts[m] / EXPECTED_RACE_COUNT for m in MARKETS},
        "active_car_count_distribution": {str(k): int(v) for k, v in sorted(active_counts.items())},
        "fail_closed_reason_counts": dict(reason_counts),
        "firewall": {"price_namespace": "PRICE_ONLY", "settlement_executable_imported": False, "official_refund_values_emitted": False, "finishing_order_emitted": False, "profit_loss_scored": False, "ev_scored": False, "roi_scored": False, "network_race_data_fetch": False},
        "scientific_state": {"all_market_track_trial_count": 0, "stage1_started": False, "stage2_started": False, "stage5_started": False, "settlement_bulk_started": False, "ECON_HOLDOUT1000": "SEALED", "holdout_result_access": False, "holdout_payout_access": False, "holdout_price_access": False},
        "stage1_gate": "ELIGIBLE_FOR_QUALITY_REVIEW" if complete else "BLOCKED_BY_FAIL_CLOSED_EXCLUSIONS",
    }
    json_dump(quality_json, quality)

    # Reload generated PRICE records and enforce the output firewall again.
    output_rows = load_jsonl(price_jsonl)
    if len(output_rows) != parsed_count:
        raise FailClosed("PRICE output row-count mismatch after write")
    for x in output_rows:
        if set(x) != PRICE_RECORD_ALLOWED_KEYS:
            raise FailClosed(f"PRICE record top-level schema drift race_id={x.get('race_id')}")
        bad = forbidden_key_scan(x)
        if bad:
            raise FailClosed(f"PRICE output forbidden field paths: {bad[:10]}")

    artifact_files = [price_jsonl, fail_jsonl, preflight_csv, coverage_csv, active_csv, quality_json]
    manifest_file.write_text("".join(f"{sha256_file(p)}  PRICE_ONLY/{p.name}\n" for p in sorted(artifact_files, key=lambda q: q.name)), encoding="utf-8")
    if artifact_zip.exists():
        artifact_zip.unlink()
    with zipfile.ZipFile(artifact_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(artifact_files, key=lambda q: q.name):
            z.write(p, arcname=f"PRICE_ONLY/{p.name}")
        z.write(manifest_file, arcname=manifest_file.name)

    receipt = {
        "record": "STAGE0_PRICE_BULK_RECEIPT_v2",
        "status": quality_status,
        "completed_at_utc": now_utc(),
        "price_parser_git_blob": parser_blob,
        "approve_receipt_git_blob": approve_blob,
        "universe_sha256": universe_sha,
        "provenance_sha256": provenance_sha,
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
    return 0


def main() -> int:
    a = parse_args()
    out = Path(a.mydrive) / "MULTIVERSE_ALL_MARKET_STAGE0_PRICE_RECOVERY_v2"
    try:
        return run(a)
    except Exception as e:
        tb = traceback.format_exc()
        fatal = {
            "record": "STAGE0_PRICE_BULK_FATAL_v2",
            "status": "FAIL_CLOSED_FATAL",
            "failed_at_utc": now_utc(),
            "error_type": type(e).__name__,
            "error": str(e),
            "traceback": tb,
            "trial_count": 0,
            "settlement_bulk_started": False,
            "stage1_started": False,
            "ECON_HOLDOUT1000": "SEALED",
        }
        try:
            json_dump(out / "STAGE0_PRICE_BULK_FATAL_v2.json", fatal)
        except Exception:
            pass
        print("FAIL-CLOSED-FATAL", file=sys.stderr, flush=True)
        print(tb, file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
