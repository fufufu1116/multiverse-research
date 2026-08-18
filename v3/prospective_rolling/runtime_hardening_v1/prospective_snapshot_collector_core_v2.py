#!/usr/bin/env python3
"""
Multiverse v3 Prospective Snapshot Collector Core v2.
NETWORK DISABLED. Validates local snapshots only.
Requires Source Admission APPROVE, fresh NTP clock receipt, strict PRE/Price schema,
HOLDOUT membership-only collision guard, append-only snapshot file, and hash-chain manifest.
"""
import argparse, json, hashlib
from datetime import datetime
from pathlib import Path
from clock_receipt_verify_v1 import verify as verify_clock
from prospective_hash_chain_manifest_v1 import append as append_chain

VERSION = "prospective_snapshot_collector_core_v2_network_disabled"
REQ_PRE = ["race_id","race_date","scheduled_start","venue","car_no","rider_id","withdrawn",
           "score","win_rate","quinella_rate","trio_rate","B","S","style","class"]
REQ_MARKETS = ["2shatan","2shahuku","3rentan","3renhuku"]
FORBIDDEN = {"result","payout","finish_order","winning_ticket","dividend","払戻","着順"}
STYLE = {"逃","追","両"}
CLASS = {"SS","S1","S2","A1","A2","A3","L1"}

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def digest(b):
    return hashlib.sha256(b).hexdigest()

def keys(x):
    if isinstance(x,dict):
        for k,v in x.items():
            yield str(k).lower()
            yield from keys(v)
    elif isinstance(x,list):
        for v in x: yield from keys(v)

def aware(s):
    d=datetime.fromisoformat(s)
    if d.tzinfo is None: raise ValueError("timezone-aware datetime required")
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--source-admission",required=True)
    ap.add_argument("--clock-receipt",required=True)
    ap.add_argument("--collector-code-sha256",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--holdout-membership")
    a=ap.parse_args()

    adm_bytes=Path(a.source_admission).read_bytes()
    adm=json.loads(adm_bytes.decode())
    if adm.get("status")!="PASS" or adm.get("independent_audit")!="APPROVE":
        raise SystemExit("FAIL_CLOSED: source admission not PASS+APPROVE")

    raw=Path(a.input).read_bytes()
    s=json.loads(raw.decode())
    if any(k in FORBIDDEN for k in keys(s)):
        raise SystemExit("FAIL_CLOSED: forbidden RESULT/PAYOUT semantic key")

    pre=s.get("pre",{})
    price=s.get("price",{})
    for f in REQ_PRE:
        if f not in pre: raise SystemExit(f"FAIL_CLOSED: missing PRE {f}")
    for m in REQ_MARKETS:
        if m not in price: raise SystemExit(f"FAIL_CLOSED: missing market {m}")
    if pre["style"] not in STYLE: raise SystemExit("FAIL_CLOSED: unseen style")
    if pre["class"] not in CLASS: raise SystemExit("FAIL_CLOSED: unseen class")

    snapshot_at=aware(s["snapshot_at"]); cutoff_at=aware(s["cutoff_at"])
    if snapshot_at>=cutoff_at: raise SystemExit("FAIL_CLOSED: snapshot not before cutoff")

    clock_bytes=Path(a.clock_receipt).read_bytes()
    clock=json.loads(clock_bytes.decode())
    verify_clock(clock, s["snapshot_at"])

    if a.holdout_membership:
        rid=str(pre["race_id"])
        if rid in Path(a.holdout_membership).read_text(encoding="utf-8"):
            raise SystemExit("FAIL_CLOSED: HOLDOUT collision")

    normalized={
        "collector_version":VERSION,"source_id":s["source_id"],"snapshot_at":s["snapshot_at"],
        "cutoff_at":s["cutoff_at"],"pre":pre,"price":price,
        "raw_input_sha256":digest(raw),"clock_receipt_sha256":digest(clock_bytes),
        "source_admission_sha256":digest(adm_bytes)
    }
    norm_bytes=canon(normalized).encode()
    normalized["normalized_sha256"]=digest(norm_bytes)

    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    rid=str(pre["race_id"]); target=out/f"{rid}.snapshot.json"
    if target.exists(): raise SystemExit("FAIL_CLOSED: append-only overwrite")
    target.write_text(json.dumps(normalized,ensure_ascii=False,indent=2),encoding="utf-8")

    item={
        "race_id":rid,
        "snapshot_sha256":digest(target.read_bytes()),
        "clock_receipt_sha256":normalized["clock_receipt_sha256"],
        "source_admission_sha256":normalized["source_admission_sha256"],
        "collector_code_sha256":a.collector_code_sha256
    }
    entry=append_chain(Path(a.manifest), item)
    print(canon({"status":"PASS_LOCAL_AUDIT_ONLY","race_id":rid,"entry_hash":entry["entry_hash"]}))

if __name__=="__main__":
    main()
