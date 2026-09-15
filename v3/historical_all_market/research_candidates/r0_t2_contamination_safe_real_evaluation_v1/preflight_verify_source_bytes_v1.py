#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def fail(msg):
    raise SystemExit("FAIL_CLOSED_" + msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="PRE JSONL manifest")
    ap.add_argument("--source-dir", required=True, help="Directory containing exact captured PRE source bytes")
    args=ap.parse_args()
    root=Path(args.source_dir)
    seen=set(); checked=0
    for line in Path(args.manifest).read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        row=json.loads(line); rid=str(row.get("race_id",""))
        if not rid: fail("MISSING_RACE_ID")
        if rid in seen: fail("DUPLICATE_RACE_ID:"+rid)
        seen.add(rid)
        expected=str(row.get("source_sha256","" )).lower()
        if len(expected)!=64: fail("BAD_EXPECTED_SHA:"+rid)
        rel=row.get("source_capture_file")
        if not rel: fail("MISSING_SOURCE_CAPTURE_FILE:"+rid)
        p=(root/str(rel)).resolve()
        try: p.relative_to(root.resolve())
        except ValueError: fail("SOURCE_PATH_ESCAPE:"+rid)
        if not p.is_file(): fail("SOURCE_FILE_MISSING:"+rid)
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected: fail("SOURCE_HASH_MISMATCH:"+rid)
        checked += 1
    print(json.dumps({"status":"PASS_SOURCE_BYTE_HASH_BINDING","checked":checked,"manifest_sha256":hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()},sort_keys=True))

if __name__=="__main__": main()
