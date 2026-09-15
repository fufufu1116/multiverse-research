#!/usr/bin/env python3
import argparse, hashlib, json, math
from datetime import datetime, timedelta, timezone
from pathlib import Path

ASSIGNMENT = "R0T2-PROSPECTIVE-20260918-V1"
JST = timezone(timedelta(hours=9))
ALLOWED_VENUES = {"静岡", "富山", "松山"}
FORBIDDEN_KEYS = {"result", "results", "outcome", "payout", "odds", "price", "economics", "payoff", "dividend"}
REQUIRED = {"meeting_id", "race_id", "scheduled_start_jst", "source_url", "source_sha256", "entrants"}

def parse_jst(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() != timedelta(hours=9):
        raise ValueError("timestamp must be timezone-aware JST (+09:00)")
    return dt

def walk_keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k).lower()
            yield from walk_keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk_keys(v)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-jsonl", required=True)
    ap.add_argument("--source-map-json", required=True, help="JSON object race_id -> local exact source-byte path")
    ap.add_argument("--assignment-id", required=True)
    ap.add_argument("--now-jst", required=True)
    args = ap.parse_args()
    if args.assignment_id != ASSIGNMENT:
        raise SystemExit("FAIL assignment_id")
    now = parse_jst(args.now_jst)
    source_map = json.loads(Path(args.source_map_json).read_text(encoding="utf-8"))
    seen = set(); rows = []
    for lineno, line in enumerate(Path(args.input_jsonl).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        row = json.loads(line)
        missing = REQUIRED - set(row)
        if missing: raise SystemExit(f"FAIL line {lineno} missing {sorted(missing)}")
        forbidden = sorted(set(walk_keys(row)) & FORBIDDEN_KEYS)
        if forbidden: raise SystemExit(f"FAIL line {lineno} forbidden keys {forbidden}")
        ident = (str(row["meeting_id"]), str(row["race_id"]))
        if ident in seen: raise SystemExit(f"FAIL line {lineno} duplicate race identity")
        seen.add(ident)
        # Assignment v1 freezes venues/titles/dates but does not define a canonical meeting_id encoding.
        # Therefore do not guess that meeting_id == venue. Require a separate explicit venue field only if present.
        if "venue" in row and row["venue"] not in ALLOWED_VENUES:
            raise SystemExit(f"FAIL line {lineno} venue outside frozen assignment")
        start = parse_jst(str(row["scheduled_start_jst"]))
        if not now < start: raise SystemExit(f"FAIL line {lineno} not pre-start")
        if not str(row["source_url"]).startswith("https://"):
            raise SystemExit(f"FAIL line {lineno} non-HTTPS source")
        claimed = str(row["source_sha256"]).lower()
        if len(claimed) != 64 or any(c not in "0123456789abcdef" for c in claimed):
            raise SystemExit(f"FAIL line {lineno} bad source_sha256")
        rid = str(row["race_id"])
        if rid not in source_map: raise SystemExit(f"FAIL line {lineno} source bytes unmapped")
        actual = sha256_file(source_map[rid])
        if actual != claimed: raise SystemExit(f"FAIL line {lineno} source byte hash mismatch")
        entrants = row["entrants"]
        if not 5 <= len(entrants) <= 9: raise SystemExit(f"FAIL line {lineno} entrant count")
        cars = []
        for e in entrants:
            if set(e) < {"car_no", "score"}: raise SystemExit(f"FAIL line {lineno} entrant fields")
            cars.append(e["car_no"])
            if not math.isfinite(float(e["score"])): raise SystemExit(f"FAIL line {lineno} nonfinite score")
        if len(cars) != len(set(cars)): raise SystemExit(f"FAIL line {lineno} duplicate car_no")
        rows.append(row)
    if not rows: raise SystemExit("FAIL no rows")
    print(json.dumps({"status":"PASS","rows":len(rows),"input_sha256":sha256_file(args.input_jsonl)}, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__": main()
