#!/usr/bin/env python3
import argparse, json
from datetime import datetime
from pathlib import Path

MAX_ABS_OFFSET_MS = 100.0
MAX_AGE_SECONDS = 60

def dt(s):
    x = datetime.fromisoformat(s)
    if x.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    return x

def verify(receipt, snapshot_at):
    required = ["checked_at","host_time_utc","reference_time_utc","offset_ms",
                "synchronized","reference_source","reference_source_count"]
    for k in required:
        if k not in receipt:
            raise ValueError(f"missing clock field: {k}")
    if receipt["synchronized"] is not True:
        raise ValueError("clock not synchronized")
    if abs(float(receipt["offset_ms"])) >= MAX_ABS_OFFSET_MS:
        raise ValueError("clock drift is not <100ms")
    if int(receipt["reference_source_count"]) < 1:
        raise ValueError("no trusted time reference")
    checked = dt(receipt["checked_at"])
    snap = dt(snapshot_at)
    age = (snap - checked).total_seconds()
    if age < 0 or age > MAX_AGE_SECONDS:
        raise ValueError("clock receipt is stale or from the future")
    return True

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--snapshot-at", required=True)
    a = ap.parse_args()
    r = json.loads(Path(a.receipt).read_text(encoding="utf-8"))
    verify(r, a.snapshot_at)
    print(json.dumps({"status":"PASS","max_abs_offset_ms":MAX_ABS_OFFSET_MS,"max_age_seconds":MAX_AGE_SECONDS}))
