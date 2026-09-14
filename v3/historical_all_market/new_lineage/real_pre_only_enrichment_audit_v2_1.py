from __future__ import annotations

import gzip
import hashlib
import json
import re
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
PRIMARY_FORBIDDEN_KEY_TERMS = (
    "result", "payout", "finish", "winner", "settlement", "odds", "price",
    "roi", "profit", "bankroll", "return",
)
REPORT_ALLOWED_KEYS = {
    "status", "universe_sha256", "universe_race_count", "pre_successful_unique",
    "missing_or_quarantined_unique", "parser_version", "transport",
    "raw_html_persisted", "payload_sha256_recorded", "market_odds_used",
    "external_prediction_fields_used", "result_accessed", "payout_accessed",
    "race_substitution_performed", "training_eligibility", "next_gate",
}
KEY_RE = re.compile(rb'"((?:[^"\\]|\\.)+)"\s*:')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def keys_jsonl_gz(path: Path) -> set[str]:
    keys: set[str] = set()
    with gzip.open(path, "rb") as f:
        for line in f:
            for m in KEY_RE.finditer(line):
                keys.add(m.group(1).decode("utf-8", errors="replace"))
    return keys


def keys_json(path: Path) -> set[str]:
    keys: set[str] = set()
    data = path.read_bytes()
    for m in KEY_RE.finditer(data):
        keys.add(m.group(1).decode("utf-8", errors="replace"))
    return keys


def primary_forbidden(keys: set[str]) -> list[str]:
    return [
        k for k in sorted(keys)
        if any(term in k.lower() for term in PRIMARY_FORBIDDEN_KEY_TERMS)
    ]


def main(source_path: str, report_path: str, out_path: str) -> int:
    source = Path(source_path)
    report = Path(report_path)
    out = Path(out_path)

    source_sha = sha256_file(source)
    report_sha = sha256_file(report)
    identity = {
        "source_sha256_expected": SOURCE_EXPECTED_SHA256,
        "source_sha256_actual": source_sha,
        "report_sha256_expected": REPORT_EXPECTED_SHA256,
        "report_sha256_actual": report_sha,
    }
    if source_sha != SOURCE_EXPECTED_SHA256 or report_sha != REPORT_EXPECTED_SHA256:
        out.write_text(json.dumps({"status":"STOP_IDENTITY_HASH_MISMATCH","identity":identity}, indent=2)+"\n")
        return 2

    source_keys = keys_jsonl_gz(source)
    report_keys = keys_json(report)
    forbidden = primary_forbidden(source_keys)
    unexpected_report_keys = sorted(report_keys - REPORT_ALLOWED_KEYS)
    if forbidden or unexpected_report_keys:
        payload = {
            "status": "STOP_SCHEMA_SAFETY_CHECK_FAILED_BEFORE_VALUE_AUDIT",
            "identity": identity,
            "source_forbidden_keys": forbidden,
            "unexpected_report_keys": unexpected_report_keys,
            "source_keys": sorted(source_keys),
            "report_keys": sorted(report_keys),
            "source_value_rows_parsed": false,
            "report_values_parsed": false
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
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
            "identity": identity,
            "pre_only_checks": pre_only_checks,
            "source_value_rows_parsed": false
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return 4

    present = [f for f in TARGET_FIELDS if f in source_keys]
    missing = [f for f in TARGET_FIELDS if f not in source_keys]
    payload: dict[str, Any] = {
        "record": "KEIRIN_REAL_PRE_ONLY_ENRICHMENT_AUDIT_V2_1_RESULT",
        "status": "COMPLETE_SCHEMA_ONLY_NO_SOURCE_VALUE_READ",
        "evidence_class": "REAL_PRE_ONLY_ENRICHMENT_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE",
        "identity": identity,
        "source_keys": sorted(source_keys),
        "report_keys": sorted(report_keys),
        "pre_only_checks": pre_only_checks,
        "target_fields_present": present,
        "target_fields_missing": missing,
        "source_value_rows_parsed": false,
        "predictive_performance_claim": false,
        "training_or_fit": false,
        "model_selection": false,
        "model_promotion": false,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "odds_price": "NOT_ACCESSED",
        "economics": "NOT_COMPUTED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "runtime": "OFF",
        "automatic_betting": false
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit_v2_1.py PRE_STRUCTURED.jsonl.gz DEV2000_PRE_COLLECTION_REPORT.json OUT.json")
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
