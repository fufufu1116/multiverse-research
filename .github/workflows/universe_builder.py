from __future__ import annotations
import argparse, csv, hashlib, json, sys
from datetime import datetime
from pathlib import Path

SIM100_DATES = {"2026-08-11", "2026-08-12"}

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="candidate races CSV")
    ap.add_argument("--output", required=True)
    ap.add_argument("--min-races", type=int, default=3000)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args=ap.parse_args()

    src=Path(args.input)
    rows=list(csv.DictReader(src.read_text(encoding="utf-8").splitlines()))
    required={"race_id","race_date","venue_code","grade","url"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"FAIL-CLOSED: required columns missing: {required}")

    start=datetime.fromisoformat(args.start).date()
    end=datetime.fromisoformat(args.end).date()
    out=[]
    seen=set()
    for r in rows:
        d=datetime.fromisoformat(r["race_date"]).date()
        if not (start <= d <= end): continue
        if r["race_date"] in SIM100_DATES:
            raise SystemExit("FAIL-CLOSED: SIM100 diagnostic dates detected in NEXTGEN universe")
        rid=r["race_id"]
        if rid in seen:
            raise SystemExit(f"FAIL-CLOSED: duplicate race_id {rid}")
        seen.add(rid); out.append(r)

    out.sort(key=lambda r:(r["race_date"], r["venue_code"], r["race_id"]))
    if len(out) < args.min_races:
        raise SystemExit(f"FAIL-CLOSED: universe too small {len(out)} < {args.min_races}")

    dest=Path(args.output); dest.parent.mkdir(parents=True,exist_ok=True)
    with open(dest,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator="\n")
        w.writeheader(); w.writerows(out)
    receipt={
        "status":"LOCKED",
        "race_count":len(out),
        "start":args.start,"end":args.end,
        "dataset_sha256":sha(dest),
        "source_sha256":sha(src),
        "sim100_policy":"diagnostic_only_excluded"
    }
    Path(str(dest)+".lock.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
