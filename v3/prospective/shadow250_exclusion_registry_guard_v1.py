#!/usr/bin/env python3
import json, hashlib
from pathlib import Path

ZERO="0"*64

def canon(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def entry_hash(payload):
    return hashlib.sha256(canon(payload)).hexdigest()

def verify_chain(path):
    prev=ZERO
    count=0
    seen=set()
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip(): continue
        row=json.loads(raw)
        eh=row.pop("entry_hash")
        if row["prev_entry_hash"]!=prev: raise RuntimeError("HALT chain linkage")
        if entry_hash(row)!=eh: raise RuntimeError("HALT entry hash")
        if row["entry_type"]=="RACE":
            rid=str(row["race_id"])
            if rid in seen: raise RuntimeError("HALT duplicate race")
            seen.add(rid); count+=1
            if row["selected_count"]!=count: raise RuntimeError("HALT selected_count")
            if row["status"]!="PERMANENTLY_DISQUALIFIED_FROM_FINAL_PROSPECTIVE_V3":
                raise RuntimeError("HALT exclusion status")
        elif row["entry_type"]=="GENESIS":
            if count or row["selected_count"]!=0: raise RuntimeError("HALT genesis")
        else:
            raise RuntimeError("HALT unknown entry type")
        prev=eh
    return {"status":"PASS","selected_count":count,"tail_hash":prev}
