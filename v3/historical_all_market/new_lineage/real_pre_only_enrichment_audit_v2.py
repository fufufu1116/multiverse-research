from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SOURCE_EXPECTED_SHA256 = "4fb0a2e9ede9aa343fa7828a65099beb2e4ce8ee76522c9952331ad536b0db84"
REPORT_EXPECTED_SHA256 = "331115704c98d0a1a7194c8f5d338d31c7036df9aec834fc07acc46e962b9d03"
TARGET_FIELDS = (
    "line_group_id",
    "line_position",
    "line_size",
    "bank_length_m",
    "wind_speed_mps",
)
FORBIDDEN_KEY_TERMS = (
    "result",
    "payout",
    "finish",
    "winner",
    "settlement",
    "odds",
    "price",
    "roi",
    "profit",
    "bankroll",
    "return",
)
KEY_RE = re.compile(rb'"((?:[^"\\]|\\.)+)"\s*:')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def lexical_keys_from_jsonl_gz(path: Path) -> set[str]:
    keys: set[str] = set()
    with gzip.open(path, "rb") as f:
        for line in f:
            for m in KEY_RE.finditer(line):
                try:
                    keys.add(json.loads(b'"' + m.group(1) + b'"'.decode("utf-8")))
                except Exception:
                    keys.add(m.group(1).decode("utf-8", errors="replace"))
    return keys


def lexical_keys_from_json(path: Path) -> set[str]:
    data = path.read_bytes()
    keys: set[str] = set()
    for m in KEY_RE.finditer(data):
        try:
            keys.add(json.loads(('"' + m.group(1).decode("utf-8") + '"')))
        except Exception:
            keys.add(m.group(1).decode("utf-8", errors="replace"))
    return keys


def forbidden_keys(keys: set[str]) -> list[str]:
    out = []
    for key in sorted(keys):
        lower = key.lower()
        if any(term in lower for term in FORBIDDEN_KEY_TERMS):
            out.append(key)
    return out


def walk(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            yield p, k, v
            yield from walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[]")


def audit_values(source: Path) -> dict[str, Any]:
    total_json_records = 0
    field = {
        name: {
            "occurrences": 0,
            "nulls": 0,
            "types": Counter(),
            "paths": Counter(),
            "numeric_min": None,
            "numeric_max": None,
            "distinct_sample": set(),
        }
        for name in TARGET_FIELDS
    }
    with gzip.open(source, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            total_json_records += 1
            for path, key, value in walk(obj):
                if key not in field:
                    continue
                s = field[key]
                s["occurrences"] += 1
                s["paths"][path] += 1
                if value is None:
                    s["nulls"] += 1
                    continue
                s["types"][type(value).__name__] += 1
                if len(s["distinct_sample"]) < 5000:
                    try:
                        s["distinct_sample"].add(json.dumps(value, ensure_ascii=False, sort_keys=True))
                    except Exception:
                        pass
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    s["numeric_min"] = value if s["numeric_min"] is None else min(s["numeric_min"], value)
                    s["numeric_max"] = value if s["numeric_max"] is None else max(s["numeric_max"], value)
    out = {"json_records": total_json_records, "fields": {}}
    for name, s in field.items():
        out["fields"][name] = {
            "available": s["occurrences"] > 0,
            "occurrences": s["occurrences"],
            "nulls": s["nulls"],
            "non_null_occurrences": s["occurrences"] - s["nulls"],
            "types": dict(s["types"]),
            "paths": dict(s["paths"]),
            "numeric_min": s["numeric_min"],
            "numeric_max": s["numeric_max"],
            "distinct_sample_count_capped_5000": len(s["distinct_sample"]),
        }
    return out


def main(source_path: str, report_path: str, out_path: str) -> int:
    source = Path(source_path)
    report = Path(report_path)
    out = Path(out_path)

    source_sha = sha256_file(source)
    report_sha = sha256_file(report)
    governance = {
        "source_sha256_expected": SOURCE_EXPECTED_SHA256,
        "source_sha256_actual": source_sha,
        "report_sha256_expected": REPORT_EXPECTED_SHA256,
        "report_sha256_actual": report_sha,
    }
    if source_sha != SOURCE_EXPECTED_SHA256 or report_sha != REPORT_EXPECTED_SHA256:
        payload = {"status": "STOP_IDENTITY_HASH_MISMATCH", "governance": governance}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 2

    source_keys = lexical_keys_from_jsonl_gz(source)
    report_keys = lexical_keys_from_json(report)
    source_forbidden = forbidden_keys(source_keys)
    report_forbidden = forbidden_keys(report_keys)
    if source_forbidden or report_forbidden:
        payload = {
            "status": "STOP_FORBIDDEN_KEY_DETECTED_BEFORE_VALUE_AUDIT",
            "governance": governance,
            "source_forbidden_keys": source_forbidden,
            "report_forbidden_keys": report_forbidden,
            "source_keys": sorted(source_keys),
            "report_keys": sorted(report_keys),
            "value_audit_performed": False,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 3

    report_obj = json.loads(report.read_text(encoding="utf-8"))
    pre_only_checks = {
        "result_accessed_false": report_obj.get("result_accessed") is False,
        "payout_accessed_false": report_obj.get("payout_accessed") is False,
        "market_odds_used_false": report_obj.get("market_odds_used") is False,
        "external_prediction_fields_used_false": report_obj.get("external_prediction_fields_used") is False,
    }
    if not all(pre_only_checks.values()):
        payload = {
            "status": "STOP_PRE_ONLY_CONFIRMATION_FAILED",
            "governance": governance,
            "pre_only_checks": pre_only_checks,
            "value_audit_performed": False,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 4

    value_audit = audit_values(source)
    payload = {
        "record": "KEIRIN_REAL_PRE_ONLY_ENRICHMENT_AUDIT_V2_RESULT",
        "status": "COMPLETE_PRE_ONLY_ENRICHMENT_SOURCE_AUDIT",
        "evidence_class": "REAL_PRE_ONLY_ENRICHMENT_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE",
        "governance": governance,
        "source_forbidden_keys": [],
        "report_forbidden_keys": [],
        "pre_only_checks": pre_only_checks,
        "target_fields": list(TARGET_FIELDS),
        "value_audit": value_audit,
        "predictive_performance_claim": False,
        "training_or_fit": False,
        "model_selection": False,
        "model_promotion": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "odds_price": "NOT_ACCESSED",
        "economics": "NOT_COMPUTED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "runtime": "OFF",
        "automatic_betting": False,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit_v2.py PRE_STRUCTURED.jsonl.gz DEV2000_PRE_COLLECTION_REPORT.json OUT.json")
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
