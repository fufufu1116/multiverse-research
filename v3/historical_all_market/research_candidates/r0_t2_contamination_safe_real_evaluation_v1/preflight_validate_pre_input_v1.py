#!/usr/bin/env python3
import argparse, hashlib, json, math
from datetime import datetime
from pathlib import Path

ALLOWED_ASSIGNMENT = "R0T2-PROSPECTIVE-20260918-V1"
ALLOWED_MEETINGS = {"静岡", "富山", "松山"}

def fail(msg):
    raise SystemExit("FAIL_CLOSED_" + msg)

def parse_jst(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        fail("BAD_DATETIME:" + str(s))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--assignment-id", required=True)
    ap.add_argument("--now-jst", required=True, help="Trusted current JST ISO timestamp supplied by caller")
    args=ap.parse_args()
    if args.assignment_id != ALLOWED_ASSIGNMENT:
        fail("ASSIGNMENT_MISMATCH")
    now=parse_jst(args.now_jst)
    seen=set(); rows=0
    for raw in Path(args.input).read_text(encoding="utf-8").splitlines():
        if not raw.strip(): continue
        row=json.loads(raw); rows += 1
        required=("meeting_id","race_id","scheduled_start_jst","source_url","source_sha256","entrants")
        if any(k not in row for k in required): fail("MISSING_REQUIRED_FIELD")
        rid=str(row["race_id"])
        if rid in seen: fail("DUPLICATE_RACE_ID:"+rid)
        seen.add(rid)
        if str(row["meeting_id"]) not in ALLOWED_MEETINGS: fail("UNASSIGNED_MEETING:"+str(row["meeting_id"]))
        start=parse_jst(str(row["scheduled_start_jst"]))
        if now >= start: fail("NOT_PRE_START:"+rid)
        sha=str(row["source_sha256"])
        if len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha.lower()): fail("BAD_SOURCE_SHA256:"+rid)
        if not str(row["source_url"]).startswith("https://"): fail("BAD_SOURCE_URL:"+rid)
        entrants=row["entrants"]
        if not (5 <= len(entrants) <= 9): fail("ENTRANT_COUNT:"+rid)
        cars=[]
        for e in entrants:
            if "car_no" not in e or "score" not in e: fail("BAD_ENTRANT_SCHEMA:"+rid)
            cars.append(int(e["car_no"])); score=float(e["score"])
            if not math.isfinite(score): fail("NONFINITE_SCORE:"+rid)
        if len(set(cars)) != len(cars): fail("DUPLICATE_CAR_NO:"+rid)
    print(json.dumps({"status":"PASS_PRE_INPUT_PREFLIGHT","assignment_id":args.assignment_id,"rows":rows,"input_sha256":hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),"checked_now_jst":args.now_jst},sort_keys=True))

if __name__=="__main__": main()
