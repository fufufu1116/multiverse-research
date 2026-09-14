from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_EXPECTED_SHA256 = "86627fe4151074f2d20db637a7f5468e24ae3c6e878a82a33fde7b3218261b27"
REPORT_EXPECTED_SHA256 = "331115704c98d0a1a7194c8f5d338d31c7036df9aec834fc07acc46e962b9d03"
TARGET_FIELDS = ("line_group_id","line_position","line_size","bank_length_m","wind_speed_mps")
PRIMARY_FORBIDDEN_KEY_TERMS = ("result","payout","finish","winner","settlement","odds","price","roi","profit","bankroll","return")
REPORT_ALLOWED_KEYS = {"status","universe_sha256","universe_race_count","pre_successful_unique","missing_or_quarantined_unique","parser_version","transport","raw_html_persisted","payload_sha256_recorded","market_odds_used","external_prediction_fields_used","result_accessed","payout_accessed","race_substitution_performed","training_eligibility","next_gate"}
KEY_RE = re.compile(rb'"((?:[^"\\]|\\.)+)"\s*:')

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def keys_jsonl_gz(path: Path) -> set[str]:
    keys=set()
    with gzip.open(path,"rb") as f:
        for line in f:
            for m in KEY_RE.finditer(line):
                keys.add(m.group(1).decode("utf-8",errors="replace"))
    return keys

def keys_json(path: Path) -> set[str]:
    data=path.read_bytes()
    return {m.group(1).decode("utf-8",errors="replace") for m in KEY_RE.finditer(data)}

def walk(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        for k,v in obj.items():
            p=f"{path}.{k}"
            yield p,k,v
            yield from walk(v,p)
    elif isinstance(obj,list):
        for v in obj:
            yield from walk(v,f"{path}[]")

def audit_target_values(source: Path) -> dict[str, Any]:
    stats={f:{"occurrences":0,"nulls":0,"types":Counter(),"numeric_min":None,"numeric_max":None} for f in TARGET_FIELDS}
    records=0
    with gzip.open(source,"rt",encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            obj=json.loads(line); records+=1
            for _path,key,value in walk(obj):
                if key not in stats: continue
                s=stats[key]; s["occurrences"]+=1
                if value is None: s["nulls"]+=1; continue
                s["types"][type(value).__name__]+=1
                if isinstance(value,(int,float)) and not isinstance(value,bool):
                    s["numeric_min"] = value if s["numeric_min"] is None else min(s["numeric_min"],value)
                    s["numeric_max"] = value if s["numeric_max"] is None else max(s["numeric_max"],value)
    return {"json_records":records,"fields":{k:{**v,"types":dict(v["types"])} for k,v in stats.items()}}

def main(source_path: str, report_path: str, out_path: str) -> int:
    source=Path(source_path); report=Path(report_path); out=Path(out_path)
    identity={"source_sha256_expected":SOURCE_EXPECTED_SHA256,"source_sha256_actual":sha256_file(source),"report_sha256_expected":REPORT_EXPECTED_SHA256,"report_sha256_actual":sha256_file(report)}
    if identity["source_sha256_actual"]!=SOURCE_EXPECTED_SHA256 or identity["report_sha256_actual"]!=REPORT_EXPECTED_SHA256:
        out.write_text(json.dumps({"status":"STOP_IDENTITY_HASH_MISMATCH","identity":identity},indent=2)+"\n"); return 2
    sk=keys_jsonl_gz(source); rk=keys_json(report)
    forbidden=[k for k in sorted(sk) if any(t in k.lower() for t in PRIMARY_FORBIDDEN_KEY_TERMS)]
    unexpected=sorted(rk-REPORT_ALLOWED_KEYS)
    if forbidden or unexpected:
        payload={"status":"STOP_SCHEMA_SAFETY_CHECK_FAILED_BEFORE_VALUE_AUDIT","identity":identity,"source_forbidden_keys":forbidden,"unexpected_report_keys":unexpected,"source_keys":sorted(sk),"report_keys":sorted(rk),"source_values_parsed":False,"report_values_parsed":False}
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n"); return 3
    robj=json.loads(report.read_text(encoding="utf-8"))
    checks={"result_accessed_false":robj.get("result_accessed") is False,"payout_accessed_false":robj.get("payout_accessed") is False,"market_odds_used_false":robj.get("market_odds_used") is False,"external_prediction_fields_used_false":robj.get("external_prediction_fields_used") is False}
    if not all(checks.values()):
        out.write_text(json.dumps({"status":"STOP_PRE_ONLY_CONFIRMATION_FAILED","identity":identity,"pre_only_checks":checks,"source_values_parsed":False},ensure_ascii=False,indent=2)+"\n"); return 4
    present=[f for f in TARGET_FIELDS if f in sk]; missing=[f for f in TARGET_FIELDS if f not in sk]
    value_audit = audit_target_values(source) if present else None
    payload={"record":"KEIRIN_REAL_PRE_ONLY_ENRICHMENT_AUDIT_V2_2_PROVENANCE_RESULT","status":"COMPLETE_PRE_ONLY_PROVENANCE_SCHEMA_AUDIT","evidence_class":"REAL_PRE_ONLY_ENRICHMENT_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE","identity":identity,"source_keys":sorted(sk),"pre_only_checks":checks,"target_fields_present":present,"target_fields_missing":missing,"target_value_audit":value_audit,"source_non_target_values_interpreted":False,"predictive_performance_claim":False,"training_or_fit":False,"model_selection":False,"model_promotion":False,"RESULT_PAYOUT":"NOT_ACCESSED","odds_price":"NOT_ACCESSED","economics":"NOT_COMPUTED","ECON_HOLDOUT1000":"SEALED_NOT_ACCESSED","runtime":"OFF","automatic_betting":False}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return 0

if __name__=="__main__":
    import sys
    if len(sys.argv)!=4: raise SystemExit("usage: audit_v2_2.py PRE_PROVENANCE.jsonl.gz DEV2000_PRE_COLLECTION_REPORT.json OUT.json")
    raise SystemExit(main(sys.argv[1],sys.argv[2],sys.argv[3]))
