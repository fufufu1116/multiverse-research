#!/usr/bin/env python3
import argparse, hashlib, json, math
from datetime import datetime
from pathlib import Path

ALLOWED_ENTRANTS = set(range(5, 10))
ASSIGNMENT_ID = "R0T2-PROSPECTIVE-20260918-V1"
ALLOWED_MEETINGS = {
    "静岡 F1 2026-09-18..2026-09-20 オタクなリンカイ！と臥龍梅杯",
    "富山 G2 2026-09-18..2026-09-21 共同通信社杯競輪",
    "松山 F2 2026-09-19..2026-09-21 イー新聞杯×ウィンチケット杯",
}

def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

def parse_jst(s):
    # Require an explicit +09:00 offset so naive timestamps cannot pass silently.
    dt = datetime.fromisoformat(s)
    if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 9 * 3600:
        raise ValueError("scheduled_start_jst must carry +09:00")
    return dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="PRE-only JSONL manifest")
    ap.add_argument("--source-root", required=True, help="directory containing exact PRE source bytes")
    ap.add_argument("--checked-at-jst", required=True, help="explicit ISO timestamp with +09:00")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    checked_at = parse_jst(args.checked_at_jst)
    seen_races = set()
    validated = []
    source_root = Path(args.source_root)

    for line_no, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        required = {"assignment_id", "meeting_id", "race_id", "scheduled_start_jst", "source_file", "source_sha256", "entrants"}
        if set(row) != required:
            raise SystemExit(f"FAIL_CLOSED_SCHEMA:{line_no}")
        if row["assignment_id"] != ASSIGNMENT_ID:
            raise SystemExit(f"FAIL_CLOSED_ASSIGNMENT:{row['race_id']}")
        if row["meeting_id"] not in ALLOWED_MEETINGS:
            raise SystemExit(f"FAIL_CLOSED_MEETING:{row['race_id']}")
        race_id = str(row["race_id"])
        if race_id in seen_races:
            raise SystemExit(f"FAIL_CLOSED_DUPLICATE_RACE:{race_id}")
        seen_races.add(race_id)
        start = parse_jst(row["scheduled_start_jst"])
        if checked_at >= start:
            raise SystemExit(f"FAIL_CLOSED_NOT_PRESTART:{race_id}")
        source_file = Path(row["source_file"])
        if source_file.is_absolute() or ".." in source_file.parts:
            raise SystemExit(f"FAIL_CLOSED_SOURCE_PATH:{race_id}")
        raw = (source_root / source_file).read_bytes()
        if sha256_bytes(raw) != row["source_sha256"]:
            raise SystemExit(f"FAIL_CLOSED_SOURCE_HASH:{race_id}")
        entrants = row["entrants"]
        if len(entrants) not in ALLOWED_ENTRANTS:
            raise SystemExit(f"FAIL_CLOSED_ENTRANT_COUNT:{race_id}")
        cars = [int(e["car_no"]) for e in entrants]
        scores = [float(e["score"]) for e in entrants]
        if len(set(cars)) != len(cars) or any(not math.isfinite(x) for x in scores):
            raise SystemExit(f"FAIL_CLOSED_INPUT:{race_id}")
        validated.append({
            "meeting_id": row["meeting_id"], "race_id": race_id,
            "scheduled_start_jst": row["scheduled_start_jst"],
            "source_sha256": row["source_sha256"], "entrant_count": len(entrants)
        })

    validated.sort(key=lambda r: (r["scheduled_start_jst"], r["meeting_id"], r["race_id"]))
    receipt = {
        "record": "KEIRIN_R0_T2_PRELOCK_PREFLIGHT_RECEIPT_V1",
        "assignment_id": ASSIGNMENT_ID,
        "checked_at_jst": args.checked_at_jst,
        "validated_races": validated,
        "validated_count": len(validated),
        "result_access": False,
        "prediction_semantics_changed": False,
    }
    Path(args.output).write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"validated_count": len(validated), "receipt_sha256": sha256_bytes(Path(args.output).read_bytes())}, sort_keys=True))

if __name__ == "__main__":
    main()
