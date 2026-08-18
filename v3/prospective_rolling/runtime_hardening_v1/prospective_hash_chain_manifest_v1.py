#!/usr/bin/env python3
import argparse, hashlib, json, re
from pathlib import Path

ZERO = "0"*64
HEX64 = re.compile(r"^[0-9a-f]{64}$")

def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def h(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()

def read_chain(p):
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def verify(entries):
    prev = ZERO
    seen = set()
    for i, e in enumerate(entries, 1):
        if e.get("index") != i:
            raise ValueError("non-contiguous index")
        if e.get("race_id") in seen:
            raise ValueError("duplicate race_id")
        seen.add(e["race_id"])
        for k in ["snapshot_sha256","clock_receipt_sha256","source_admission_sha256","collector_code_sha256"]:
            if not HEX64.match(str(e.get(k,""))):
                raise ValueError(f"invalid {k}")
        if e.get("prev_entry_hash") != prev:
            raise ValueError("broken prev hash")
        core = {k:v for k,v in e.items() if k != "entry_hash"}
        expected = h(core)
        if e.get("entry_hash") != expected:
            raise ValueError("entry hash mismatch")
        prev = expected
    return prev

def append(path, item):
    entries = read_chain(path)
    head = verify(entries)
    if any(e["race_id"] == item["race_id"] for e in entries):
        raise ValueError("duplicate race_id")
    e = {
        "index": len(entries)+1,
        "race_id": item["race_id"],
        "snapshot_sha256": item["snapshot_sha256"],
        "clock_receipt_sha256": item["clock_receipt_sha256"],
        "source_admission_sha256": item["source_admission_sha256"],
        "collector_code_sha256": item["collector_code_sha256"],
        "prev_entry_hash": head if entries else ZERO
    }
    e["entry_hash"] = h(e)
    with path.open("a", encoding="utf-8") as f:
        f.write(canon(e)+"\n")
    verify(read_chain(path))
    return e

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--manifest", required=True)
    a = sub.add_parser("append"); a.add_argument("--manifest", required=True); a.add_argument("--item", required=True)
    args = ap.parse_args()
    p = Path(args.manifest)
    if args.cmd == "verify":
        entries = read_chain(p); head = verify(entries)
        print(json.dumps({"status":"PASS","entries":len(entries),"head":head}))
    else:
        item = json.loads(Path(args.item).read_text(encoding="utf-8"))
        e = append(p, item)
        print(json.dumps({"status":"PASS","entry":e}))
