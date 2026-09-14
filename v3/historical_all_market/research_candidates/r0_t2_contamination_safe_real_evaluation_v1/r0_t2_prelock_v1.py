#!/usr/bin/env python3
import argparse, hashlib, json, math
from pathlib import Path

TEMPERATURE = 2.0
ALLOWED_ENTRANTS = set(range(5, 10))

def softmax(xs):
    m=max(xs)
    zs=[math.exp(x-m) for x in xs]
    s=sum(zs)
    return [z/s for z in zs]

def r0_t2_probabilities(scores):
    return softmax([float(x)/TEMPERATURE for x in scores])

def canonical_sha(obj):
    raw=(json.dumps(obj, sort_keys=True, separators=(",",":"))+"\n").encode()
    return hashlib.sha256(raw).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--assignment-id", required=True)
    args=ap.parse_args()
    rows=[]
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row=json.loads(line)
        entrants=row["entrants"]
        n=len(entrants)
        if n not in ALLOWED_ENTRANTS:
            raise SystemExit(f"FAIL_CLOSED_ENTRANT_COUNT:{row.get('race_id')}:{n}")
        cars=[int(e["car_no"]) for e in entrants]
        scores=[float(e["score"]) for e in entrants]
        if len(set(cars)) != n or any(not math.isfinite(x) for x in scores):
            raise SystemExit(f"FAIL_CLOSED_INPUT:{row.get('race_id')}")
        p=r0_t2_probabilities(scores)
        order=sorted(range(n), key=lambda i:(p[i],-cars[i]), reverse=True)
        locked={
            "assignment_id":args.assignment_id,
            "meeting_id":row["meeting_id"],
            "race_id":row["race_id"],
            "scheduled_start_jst":row["scheduled_start_jst"],
            "source_url":row["source_url"],
            "source_sha256":row["source_sha256"],
            "entrants":[{"car_no":cars[i],"score":scores[i]} for i in range(n)],
            "r0_t2_temperature":TEMPERATURE,
            "p_win":[{"car_no":cars[i],"p":p[i]} for i in range(n)],
            "ordered_top3_car_no":[cars[i] for i in order[:3]]
        }
        locked["lock_sha256"]=canonical_sha(locked)
        rows.append(locked)
    rows.sort(key=lambda r:(r["scheduled_start_jst"],r["meeting_id"],r["race_id"]))
    Path(args.output).write_text("".join(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n" for r in rows),encoding="utf-8")
    print(json.dumps({"rows":len(rows),"output_sha256":hashlib.sha256(Path(args.output).read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__":
    main()
