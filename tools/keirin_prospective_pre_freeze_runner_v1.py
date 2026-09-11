#!/usr/bin/env python3
"""One-shot fail-closed prospective PRE freeze runner.

Order:
1. validate cutoff/provenance/target identity via keirin_prospective_cutoff_guard_v3
2. require pre_payload identity to equal target_identity
3. apply exact frozen B1a_RECONSTITUTED_v1 winner predictor
4. emit one immutable PRE freeze receipt (no result/settlement access)
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
from keirin_prospective_cutoff_guard_v3 import validate as validate_guard
from keirin_b1a_prospective_winner_predictor_v1 import predict as predict_b1a

def sha256_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def canonical_bytes(obj:Any)->bytes:
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def run(envelope:dict[str,Any],repo_root:Path)->dict[str,Any]:
    guard=validate_guard(envelope,repo_root)
    identity=envelope["target_identity"]
    pre=envelope["pre_payload"]
    required=("event_date","venue","race_number")
    miss=[k for k in required if k not in pre]
    if miss: raise ValueError("FAIL_CLOSED:pre_payload_identity_missing="+",".join(miss))
    if str(pre["event_date"])!=str(identity["event_date"]):
        raise ValueError("FAIL_CLOSED:pre_payload_event_date_mismatch")
    if str(pre["venue"]).strip()!=str(identity["venue"]).strip():
        raise ValueError("FAIL_CLOSED:pre_payload_venue_mismatch")
    if int(pre["race_number"])!=int(identity["race_number"]):
        raise ValueError("FAIL_CLOSED:pre_payload_race_number_mismatch")
    pred=predict_b1a(pre)
    body={
        "record":"KEIRIN_PROSPECTIVE_PRE_FREEZE_RECEIPT_v1",
        "status":"PASS_PRE_FROZEN_BEFORE_OUTCOME",
        "target_event_id":str(envelope["target_event_id"]),
        "capture_time":guard["capture_time"],
        "target_cutoff":guard["target_cutoff"],
        "target_identity":guard["target_identity"],
        "provenance_guard_status":guard["status"],
        "source_receipts":guard["receipts"],
        "frozen_v54_exact_match":guard["frozen_v54_exact_match"],
        "winner_prediction":pred,
        "pre_payload_sha256":sha256_bytes(canonical_bytes(pre)),
        "outcome_accessed":False,
        "post_cutoff_backfill":False,
        "post_result_reconstruction":False,
        "retune":False,
        "runtime":"OFF",
        "automatic_betting":False,
        "scientific_trial_count":0,
    }
    body["freeze_receipt_sha256"]=sha256_bytes(canonical_bytes(body))
    return body

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    try:
        env=json.loads(Path(a.input).read_text(encoding="utf-8"))
        out=run(env,Path(a.repo_root))
        op=Path(a.output)
        if op.exists(): raise ValueError("FAIL_CLOSED:output_already_exists")
        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        print(json.dumps({"status":"FAIL_CLOSED","reason":str(exc)},ensure_ascii=False,sort_keys=True))
        return 3
    print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
