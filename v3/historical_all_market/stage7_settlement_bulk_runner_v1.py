#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — DEV2000 Settlement bulk recovery for frozen Stage 7 only.

Outcome-sensitive boundary. This runner is intentionally narrow:
- exact DEV2000 universe + exact provenance + archived RAW_RESULT_QUARANTINE only
- exact audited settlement parser blob
- exact independent Stage-7 authorization receipt
- emits settlement-only A/B/C segment catalogs; no price, model probability, EV, ROI, selection, or bankroll logic
- ECON_HOLDOUT1000 is never referenced or scanned

The split catalogs are written separately so the Stage-7 evaluator can avoid opening Segment C
until FINAL_DEV2000_CONFIGURATION has been frozen.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_UNIVERSE_SHA256 = "eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"
EXPECTED_PROVENANCE_SHA256 = "0e9dbba0bf0427bd1b5903c196a93a31678375170e6d5164b3d8d8f052ca97f1"
EXPECTED_SETTLEMENT_PARSER_BLOB = "b8b8ab0e0904541bd6fc45e7fe415d323e63ec45"
EXPECTED_STAGE7_APPROVAL_BLOB = "71e87740ded33ea73c3f534d39830080ad8b43bb"
EXPECTED_AUDIT_SNAPSHOT = "a0360b1c5622b0664e8180186a40eca9827fc63e"
EXPECTED_RACES = 2000
MARKETS = ("3rentan", "2shatan", "3renhuku", "2shahuku", "2wakutan", "2wakuhuku", "wide")
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

def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

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

def import_bound_settlement_parser(repo_root: Path):
    p = repo_root / "v3" / "historical_all_market" / "kdreams_settlement_recovery_v1.py"
    if not p.is_file():
        raise FailClosed(f"settlement parser missing: {p}")
    blob = git_blob_sha1_bytes(p.read_bytes())
    if blob != EXPECTED_SETTLEMENT_PARSER_BLOB:
        raise FailClosed(f"settlement parser blob mismatch expected={EXPECTED_SETTLEMENT_PARSER_BLOB} observed={blob}")
    spec = importlib.util.spec_from_file_location("multiverse_stage7_settlement_parser", p)
    if spec is None or spec.loader is None:
        raise FailClosed("cannot import settlement parser")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "parse_payload"):
        raise FailClosed("settlement parser has no parse_payload")
    return mod, blob

def verify_stage7_approval(repo_root: Path) -> str:
    p = repo_root / "v3" / "historical_all_market" / "governance" / "INDEPENDENT_GOVERNANCE_STAGE7_SETTLEMENT_APPROVE_RECEIPT_v1.json"
    if not p.is_file():
        raise FailClosed(f"Stage7 approval receipt missing: {p}")
    blob = git_blob_sha1_bytes(p.read_bytes())
    if blob != EXPECTED_STAGE7_APPROVAL_BLOB:
        raise FailClosed(f"Stage7 approval blob mismatch expected={EXPECTED_STAGE7_APPROVAL_BLOB} observed={blob}")
    x = json.loads(p.read_text(encoding="utf-8"))
    if x.get("verdict") != "APPROVE":
        raise FailClosed("Stage7 approval verdict != APPROVE")
    if x.get("audit_snapshot_commit") != EXPECTED_AUDIT_SNAPSHOT:
        raise FailClosed("Stage7 approval audit snapshot mismatch")
    dec = x.get("explicit_decisions", {})
    if dec.get("DEV2000_SETTLEMENT_BULK") != "AUTHORIZED_FOR_FROZEN_STAGE7_ONLY":
        raise FailClosed("DEV2000 settlement bulk not authorized")
    if dec.get("ECON_HOLDOUT1000") != "SEALED":
        raise FailClosed("HOLDOUT sealed decision missing")
    if dec.get("STAGE7_REALIZED_SCIENTIFIC_TRIAL_COUNT_BEFORE_OPEN") != 0:
        raise FailClosed("pre-open trial count is not zero")
    return blob

def build_raw_index(raw_dir: Path):
    if not raw_dir.is_dir():
        raise FailClosed(f"raw quarantine missing: {raw_dir}")
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
        raise FailClosed("no SHA-addressed gzip raw files")
    print(f"[RAW INDEX] scanned={scanned} unique_sha={len(index)} duplicate_sha={len(duplicates)}", flush=True)
    return index, duplicates

def resolve_raw_path(rid: str, prov: dict[str, Any], raw_index: dict[str, Path], duplicate_index: dict[str, list[str]]) -> Path:
    if prov.get("fallback_used") is not False:
        raise FailClosed(f"{rid}: fallback_used != false")
    dig = str(prov.get("raw_payload_sha256", "")).strip()
    if not re.fullmatch(r"[0-9a-f]{64}", dig):
        raise FailClosed(f"{rid}: invalid raw sha")
    if dig in duplicate_index:
        raise FailClosed(f"{rid}: duplicate raw files for {dig}")
    q = raw_index.get(dig)
    if q is None:
        explicit = prov.get("raw_quarantine_path")
        if explicit:
            e = Path(str(explicit))
            if e.is_file():
                q = e
    if q is None:
        raise FailClosed(f"{rid}: raw not found for sha={dig}")
    return q

def read_verify_gzip(q: Path, expected_sha: str) -> bytes:
    try:
        with gzip.open(q, "rb") as f:
            b = f.read()
    except Exception as e:
        raise FailClosed(f"gzip read failed {q.name}: {e}") from e
    obs = sha256_bytes(b)
    if obs != expected_sha:
        raise FailClosed(f"raw SHA mismatch {q.name}: {obs} != {expected_sha}")
    return b

def validate_settlement_record(rid: str, dev_index: int, parsed: dict[str, Any]) -> dict[str, Any]:
    if parsed.get("parser_id") != "KDREAMS_SETTLEMENT_RECOVERY_v1":
        raise FailClosed(f"{rid}: parser id drift")
    if parsed.get("price_fields_emitted") is not False:
        raise FailClosed(f"{rid}: price firewall failure")
    if parsed.get("result_order_fields_emitted") is not False:
        raise FailClosed(f"{rid}: result-order firewall failure")
    if parsed.get("model_probability_computed") is not False or parsed.get("ev_computed") is not False or parsed.get("roi_computed") is not False:
        raise FailClosed(f"{rid}: economic-computation firewall failure")
    if parsed.get("operational_stage") != "POST_RULE_FREEZE_SETTLEMENT_ONLY":
        raise FailClosed(f"{rid}: operational stage drift")
    sett = parsed.get("settlements_yen_per_100")
    presence = parsed.get("settled_market_presence")
    if not isinstance(sett, dict) or set(sett) != set(MARKETS):
        raise FailClosed(f"{rid}: settlement market schema mismatch")
    if not isinstance(presence, dict) or set(presence) != set(MARKETS):
        raise FailClosed(f"{rid}: market-presence schema mismatch")
    for m in MARKETS:
        if bool(sett[m]) != bool(presence[m]):
            raise FailClosed(f"{rid}/{m}: presence mismatch")
        if not isinstance(sett[m], dict):
            raise FailClosed(f"{rid}/{m}: settlement not object")
        for k, v in sett[m].items():
            if not isinstance(k, str) or not isinstance(v, int) or v <= 0:
                raise FailClosed(f"{rid}/{m}: malformed refund entry")
    seg = "A" if dev_index <= 1000 else ("B" if dev_index <= 1500 else "C")
    return {
        "race_id": rid,
        "dev_index": dev_index,
        "segment": seg,
        "raw_sha256": parsed["raw_sha256"],
        "settlements_yen_per_100": sett,
        "settled_market_presence": presence,
        "multi_refund_supported": parsed.get("multi_refund_supported") is True,
        "parser_id": parsed["parser_id"],
        "price_fields_emitted": False,
        "result_order_fields_emitted": False,
        "model_probability_computed": False,
        "ev_computed": False,
        "roi_computed": False,
    }

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mydrive", default="/content/drive/MyDrive")
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--overwrite", action="store_true")
    return ap.parse_args()

def output_paths(out: Path):
    return {
        "A": out / "SETTLEMENT_ONLY" / "DEV2000_SETTLEMENT_A_v1.jsonl",
        "B": out / "SETTLEMENT_ONLY" / "DEV2000_SETTLEMENT_B_v1.jsonl",
        "C": out / "SETTLEMENT_ONLY" / "DEV2000_SETTLEMENT_C_UNTOUCHED_v1.jsonl",
        "receipt": out / "STAGE7_SETTLEMENT_BULK_RECEIPT_v1.json",
        "quality": out / "SETTLEMENT_ONLY" / "STAGE7_SETTLEMENT_BULK_QUALITY_v1.json",
        "fatal": out / "STAGE7_SETTLEMENT_BULK_FATAL_v1.json",
    }

def run(a) -> int:
    my = Path(a.mydrive)
    repo = Path(a.repo_root).resolve()
    out = my / "MULTIVERSE_ALL_MARKET_STAGE7_SETTLEMENT_EVAL_v1"
    paths = output_paths(out)
    out.mkdir(parents=True, exist_ok=True)
    paths["A"].parent.mkdir(parents=True, exist_ok=True)

    if a.overwrite:
        for p in paths.values():
            if p.exists() and p.is_file():
                p.unlink()
    elif paths["receipt"].exists():
        rec = json.loads(paths["receipt"].read_text(encoding="utf-8"))
        if rec.get("status") == "PASS_COMPLETE":
            for key in ("A", "B", "C", "quality"):
                if not paths[key].is_file():
                    raise FailClosed(f"existing PASS receipt but missing {key}")
            print("[ALREADY PASS] settlement bulk exists; no re-open required", flush=True)
            return 0

    mod, parser_blob = import_bound_settlement_parser(repo)
    approval_blob = verify_stage7_approval(repo)

    universe = my / "MULTIVERSE_DEV2000_UNIVERSE_RECOVERY" / "DEV2000_UNIVERSE_v1.csv"
    result_dir = my / "MULTIVERSE_DEV2000_RESULT_COLLECTION_v3_HARDENED"
    provenance = result_dir / "DEV2000_RESULT_PROVENANCE_v3.jsonl"
    raw_dir = result_dir / "RAW_RESULT_QUARANTINE"

    if not universe.is_file() or sha256_file(universe) != EXPECTED_UNIVERSE_SHA256:
        raise FailClosed("DEV2000 universe missing/SHA mismatch")
    if not provenance.is_file() or sha256_file(provenance) != EXPECTED_PROVENANCE_SHA256:
        raise FailClosed("DEV2000 provenance missing/SHA mismatch")

    with universe.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_RACES:
        raise FailClosed(f"universe rows={len(rows)}")
    by_idx: dict[int, str] = {}
    for r in rows:
        try:
            idx = int(r["dev_index"])
        except Exception as e:
            raise FailClosed("invalid dev_index") from e
        rid = str(r["race_id"]).strip()
        if idx in by_idx or not rid:
            raise FailClosed("duplicate dev_index / blank race_id")
        by_idx[idx] = rid
    if set(by_idx) != set(range(1, 2001)) or len(set(by_idx.values())) != 2000:
        raise FailClosed("dev_index/race_id cardinality failure")

    prov_rows = load_jsonl(provenance)
    if len(prov_rows) != 2000:
        raise FailClosed("provenance cardinality")
    prov_by = {}
    for x in prov_rows:
        rid = str(x.get("race_id", "")).strip()
        if not rid or rid in prov_by:
            raise FailClosed("provenance duplicate/blank race")
        prov_by[rid] = {
            "fallback_used": x.get("fallback_used"),
            "raw_payload_sha256": x.get("raw_payload_sha256"),
            "raw_quarantine_path": x.get("raw_quarantine_path"),
        }
    if set(prov_by) != set(by_idx.values()):
        raise FailClosed("universe/provenance race-set mismatch")

    raw_index, duplicate_index = build_raw_index(raw_dir)
    tmp_paths = {s: paths[s].with_suffix(paths[s].suffix + ".tmp") for s in ("A", "B", "C")}
    handles = {s: tmp_paths[s].open("w", encoding="utf-8") for s in ("A", "B", "C")}
    counts = Counter()
    market_presence = Counter()
    multi_refund_races = 0
    try:
        for idx in range(1, 2001):
            rid = by_idx[idx]
            prov = prov_by[rid]
            q = resolve_raw_path(rid, prov, raw_index, duplicate_index)
            payload = read_verify_gzip(q, str(prov["raw_payload_sha256"]))
            parsed = mod.parse_payload(payload, str(prov["raw_payload_sha256"]))
            rec = validate_settlement_record(rid, idx, parsed)
            seg = rec["segment"]
            handles[seg].write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            counts[seg] += 1
            winners = 0
            for m in MARKETS:
                if rec["settled_market_presence"][m]:
                    market_presence[m] += 1
                winners += len(rec["settlements_yen_per_100"][m])
            if winners > sum(1 for m in MARKETS if rec["settled_market_presence"][m]):
                multi_refund_races += 1
            if idx % 100 == 0:
                print(f"[SETTLEMENT BULK] {idx}/2000 A={counts['A']} B={counts['B']} C={counts['C']}", flush=True)
    finally:
        for h in handles.values():
            h.close()

    if counts != Counter({"A": 1000, "B": 500, "C": 500}):
        raise FailClosed(f"segment counts mismatch: {dict(counts)}")
    for s in ("A", "B", "C"):
        tmp_paths[s].replace(paths[s])

    hashes = {s: sha256_file(paths[s]) for s in ("A", "B", "C")}
    quality = {
        "record": "STAGE7_SETTLEMENT_BULK_QUALITY_v1",
        "status": "PASS_COMPLETE",
        "races": 2000,
        "segment_rows": {"A": 1000, "B": 500, "C": 500},
        "market_settlement_presence_races": {m: market_presence[m] for m in MARKETS},
        "multi_refund_races": multi_refund_races,
        "segment_sha256": hashes,
        "universe_sha256": EXPECTED_UNIVERSE_SHA256,
        "provenance_sha256": EXPECTED_PROVENANCE_SHA256,
        "settlement_parser_git_blob": parser_blob,
        "stage7_approval_git_blob": approval_blob,
        "audit_snapshot_commit": EXPECTED_AUDIT_SNAPSHOT,
        "price_fields_emitted": False,
        "model_probability_computed": False,
        "ev_computed": False,
        "roi_computed": False,
        "configuration_selection_performed": False,
        "ECON_HOLDOUT1000": "SEALED",
    }
    dump_json(paths["quality"], quality)
    receipt = {
        "record": "STAGE7_SETTLEMENT_BULK_RECEIPT_v1",
        "status": "PASS_COMPLETE",
        "completed_at_utc": now_utc(),
        "audit_snapshot_commit": EXPECTED_AUDIT_SNAPSHOT,
        "settlement_parser_git_blob": parser_blob,
        "stage7_approval_git_blob": approval_blob,
        "universe_sha256": EXPECTED_UNIVERSE_SHA256,
        "provenance_sha256": EXPECTED_PROVENANCE_SHA256,
        "segment_sha256": hashes,
        "quality_sha256": sha256_file(paths["quality"]),
        "segment_c_scored": False,
        "stage7_selection_started": False,
        "scientific_trial_count_before_open": 0,
        "ECON_HOLDOUT1000": "SEALED",
    }
    dump_json(paths["receipt"], receipt)
    if paths["fatal"].exists():
        paths["fatal"].unlink()
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
    return 0

def main() -> int:
    a = parse_args()
    try:
        return run(a)
    except Exception as e:
        my = Path(a.mydrive)
        out = my / "MULTIVERSE_ALL_MARKET_STAGE7_SETTLEMENT_EVAL_v1"
        out.mkdir(parents=True, exist_ok=True)
        fatal = output_paths(out)["fatal"]
        dump_json(fatal, {
            "record": "STAGE7_SETTLEMENT_BULK_FATAL_v1",
            "status": "FAIL_CLOSED",
            "failed_at_utc": now_utc(),
            "error_type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "ECON_HOLDOUT1000": "SEALED",
        })
        print(f"FAIL-CLOSED: {type(e).__name__}: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
