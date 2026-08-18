#!/usr/bin/env python3
"""Multiverse v3 prospective PRE/Price snapshot collector audit skeleton.
NETWORK ACCESS IS INTENTIONALLY DISABLED.
"""
import argparse, json, hashlib
from datetime import datetime
from pathlib import Path

VERSION = "prospective_snapshot_collector_audit_v1"
REQUIRED_PRE = ["race_id","race_date","scheduled_start","venue","car_no","rider_id","withdrawn","score","win_rate","quinella_rate","trio_rate","B","S","style","class"]
REQUIRED_MARKETS = ["2shatan","2shahuku","3rentan","3renhuku"]
FORBIDDEN_TOKENS = {"result","payout","finish_order","winning_ticket","dividend","払戻","着順"}

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()

def parse_dt(s):
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt

def recursive_keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k)
            yield from recursive_keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from recursive_keys(v)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--source-admission", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--holdout-membership")
    args = ap.parse_args()

    admission = json.loads(Path(args.source_admission).read_text(encoding="utf-8"))
    if admission.get("status") != "PASS" or admission.get("independent_audit") != "APPROVE":
        raise SystemExit("FAIL_CLOSED: source admission not PASS+APPROVE")

    raw = Path(args.input).read_bytes()
    snap = json.loads(raw.decode("utf-8"))
    keys = {k.lower() for k in recursive_keys(snap)}
    if any(tok in keys for tok in FORBIDDEN_TOKENS):
        raise SystemExit("FAIL_CLOSED: forbidden RESULT/PAYOUT semantic key present")

    for f in REQUIRED_PRE:
        if f not in snap.get("pre", {}):
            raise SystemExit(f"FAIL_CLOSED: missing PRE field {f}")
    for m in REQUIRED_MARKETS:
        if m not in snap.get("price", {}):
            raise SystemExit(f"FAIL_CLOSED: missing market {m}")

    snapshot_at = parse_dt(snap["snapshot_at"])
    cutoff_at = parse_dt(snap["cutoff_at"])
    if snapshot_at >= cutoff_at:
        raise SystemExit("FAIL_CLOSED: snapshot is not strictly before cutoff")

    if args.holdout_membership:
        membership = Path(args.holdout_membership).read_text(encoding="utf-8")
        race_id = str(snap["pre"]["race_id"])
        if race_id in membership:
            raise SystemExit("FAIL_CLOSED: race_id collides with HOLDOUT membership")

    normalized = {
        "collector_version": VERSION,
        "source_id": snap["source_id"],
        "snapshot_at": snap["snapshot_at"],
        "cutoff_at": snap["cutoff_at"],
        "pre": snap["pre"],
        "price": snap["price"],
        "raw_input_sha256": digest_bytes(raw),
    }
    norm_bytes = canonical(normalized).encode("utf-8")
    normalized["normalized_sha256"] = digest_bytes(norm_bytes)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    race_id = str(snap["pre"]["race_id"])
    target = out_dir / f"{race_id}.snapshot.json"
    if target.exists():
        raise SystemExit("FAIL_CLOSED: append-only violation")
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(canonical({"status":"PASS_LOCAL_AUDIT_ONLY","race_id":race_id,"normalized_sha256":normalized["normalized_sha256"]}))

if __name__ == "__main__":
    main()
