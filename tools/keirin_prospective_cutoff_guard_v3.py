#!/usr/bin/env python3
"""Add target-identity binding to KEIRIN prospective cutoff guard v2."""
from __future__ import annotations
import argparse, json, re, tempfile, unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from keirin_prospective_cutoff_guard_v2 import (
    EXPECTED_V54, TRUSTED_CLASSES, resolve_snapshot, sha256_file, validate as validate_v2,
)

IDENTITY_REQUIRED={"event_date","venue","race_number"}

def norm(x:str)->str:
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",x)).lower()

def event_date_tokens(value:str)->set[str]:
    try: d=date.fromisoformat(str(value).strip())
    except ValueError as exc: raise ValueError("FAIL_CLOSED:target_event_date_invalid") from exc
    y,m,day=d.year,d.month,d.day
    return {f"{y:04d}-{m:02d}-{day:02d}",f"{y:04d}/{m:02d}/{day:02d}",f"{y:04d}.{m:02d}.{day:02d}",f"{y:04d}年{m:02d}月{day:02d}日",f"{y:04d}年{m}月{day}日"}

def race_tokens(n:int)->set[str]:
    return {f"{n}R",f"第{n}R",f"第{n}レース",f"{n}レース",f"R{n}",f"race{n}",f"race#{n}"}

def identity_match(text:str, identity:dict[str,Any])->dict[str,bool]:
    missing=sorted(IDENTITY_REQUIRED-set(identity))
    if missing: raise ValueError("FAIL_CLOSED:target_identity_missing="+",".join(missing))
    venue=str(identity["venue"]).strip()
    if not venue: raise ValueError("FAIL_CLOSED:target_venue_invalid")
    try: rn=int(identity["race_number"])
    except (TypeError,ValueError) as exc: raise ValueError("FAIL_CLOSED:target_race_number_invalid") from exc
    if rn<1 or rn>20: raise ValueError("FAIL_CLOSED:target_race_number_invalid")
    body=norm(text)
    return {
        "event_date":any(norm(t) in body for t in event_date_tokens(identity["event_date"])),
        "venue":norm(venue) in body,
        "race_number":any(norm(t) in body for t in race_tokens(rn)),
    }

def validate(envelope:dict[str,Any], repo_root:Path)->dict[str,Any]:
    base=validate_v2(envelope,repo_root)
    identity=envelope.get("target_identity")
    if not isinstance(identity,dict): raise ValueError("FAIL_CLOSED:target_identity_required")
    checked=[]
    for i,r in enumerate(envelope["source_receipts"]):
        if str(r["trust_class"]).upper() not in TRUSTED_CLASSES: continue
        snap=resolve_snapshot(repo_root,r["snapshot_path"])
        try: text=snap.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc: raise ValueError(f"FAIL_CLOSED:trusted_snapshot_not_utf8_text={i}") from exc
        flags=identity_match(text,identity)
        if not all(flags.values()):
            absent=",".join(k for k,v in flags.items() if not v)
            raise ValueError(f"FAIL_CLOSED:trusted_snapshot_target_identity_mismatch={i}:{absent}")
        checked.append({"source_id":r["source_id"],"target_identity_match":flags})
    if not checked: raise ValueError("FAIL_CLOSED:no_trusted_target_identity_match")
    base["status"]="PASS_PRE_CUTOFF_PROVENANCE_AND_TARGET_IDENTITY_BOUND"
    base["target_identity"]={"event_date":str(identity["event_date"]),"venue":str(identity["venue"]),"race_number":int(identity["race_number"])}
    base["trusted_target_identity_checks"]=checked
    return base

def selftest()->dict[str,Any]:
    tests={}
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); p=root/'evidence'/'pre.txt'; p.parent.mkdir(); good='KEIRIN.JP 前橋 2026年9月11日 第9R 出走表'; p.write_text(good,encoding='utf-8')
        base={"target_event_id":"T","target_identity":{"event_date":"2026-09-11","venue":"前橋","race_number":9},"capture_time":"2026-09-11T10:00:00+09:00","target_cutoff":"2026-09-11T23:25:00+09:00","outcome_accessed":False,"post_cutoff_backfill":False,"post_result_reconstruction":False,"missing_pre_policy":"SKIP","pre_payload":{"race_number":9},"frozen_v54":dict(EXPECTED_V54),"source_receipts":[{"source_id":"official","source_locator":"https://www.keirin.jp/pre","trust_class":"OFFICIAL","retrieved_at":"2026-09-11T09:59:00+09:00","http_status":200,"snapshot_path":"evidence/pre.txt","content_sha256":sha256_file(p)}]}
        tests['valid']=validate(json.loads(json.dumps(base)),root)['status'].startswith('PASS_')
        for name,text in [('stale_date','KEIRIN.JP 前橋 2026年8月11日 第9R 出走表'),('wrong_venue','KEIRIN.JP 松山 2026年9月11日 第9R 出走表'),('wrong_race','KEIRIN.JP 前橋 2026年9月11日 第8R 出走表')]:
            p.write_text(text,encoding='utf-8'); x=json.loads(json.dumps(base)); x['source_receipts'][0]['content_sha256']=sha256_file(p)
            try: validate(x,root); tests[name]=False
            except ValueError: tests[name]=True
    return {"record":"KEIRIN_PROSPECTIVE_CUTOFF_GUARD_SELFTEST_v3","status":"PASS" if all(tests.values()) else "FAIL","test_count":len(tests),"tests":tests,"stale_official_snapshot_rejection":True,"network_access":False,"hardcoded_target_date":False}

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest'); c=sub.add_parser('check'); c.add_argument('--input',required=True); c.add_argument('--repo-root',default='.'); a=ap.parse_args()
    if a.cmd=='selftest': out=selftest()
    else:
        try: out=validate(json.loads(Path(a.input).read_text(encoding='utf-8')),Path(a.repo_root))
        except (OSError,json.JSONDecodeError,ValueError) as exc: print(json.dumps({"status":"FAIL_CLOSED","reason":str(exc)},ensure_ascii=False,sort_keys=True)); return 3
    print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)); return 0 if out['status'].startswith('PASS') else 2
if __name__=='__main__': raise SystemExit(main())
