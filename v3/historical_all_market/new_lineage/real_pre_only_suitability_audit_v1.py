from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_SHA256 = "25303ed3a7bce2bbc1c681823cbe9d009e3d3c5f07ef669a43fd6cf1ea86af73"
EXPECTED_ROWS = 14255
EXPECTED_RACES = 2000

DIRECT_N2 = [
    "race_id", "car_no", "score", "class", "style", "line_group_id",
    "line_position", "line_size", "bank_length_m", "wind_speed_mps",
]
FULL_PRE_FLAT = [
    "race_id", "prediction_timestamp", "decision_timestamp", "decision_cutoff_rule_id",
    "race_regime", "race_regime_source", "race_regime_source_timestamp",
    "race_regime_raw_provenance_sha", "line_source", "line_snapshot_timestamp",
    "line_observation_type", "line_raw_provenance_sha", "num_lines", "car_no",
    "rider_id", "active", "line_group_id", "line_position", "line_size", "is_singleton",
]
NUMERIC = ["car_no", "score", "line_group_id", "line_position", "line_size", "bank_length_m", "wind_speed_mps"]
FORBIDDEN_TERMS = [
    "result", "payout", "odds", "price", "settlement", "finish", "winner", "refund",
    "return_amount", "profit", "roi", "結果", "払戻", "オッズ", "配当", "着順", "的中", "収益", "利益",
]
SUPPORTED = {
    "class": {"S1", "S2", "A1", "A2", "A3"},
    "style": {"逃", "両", "追"},
    "bank_length_m": {333.0, 400.0, 500.0},
    "line_position": {0.0, 1.0, 2.0},
    "line_size": {1.0, 2.0, 3.0},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_header(name: str) -> str:
    return name.strip().casefold().replace(" ", "_").replace("-", "_")


def forbidden_columns(header: list[str]) -> list[str]:
    bad = []
    for col in header:
        n = norm_header(col)
        if any(term in n for term in FORBIDDEN_TERMS):
            bad.append(col)
    return bad


def is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ""


def quantile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    x = q * (len(sorted_values) - 1)
    lo, hi = math.floor(x), math.ceil(x)
    if lo == hi:
        return sorted_values[lo]
    w = x - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def summary_numeric(values: list[float]) -> dict:
    vals = sorted(values)
    return {
        "n": len(vals),
        "min": vals[0] if vals else None,
        "q05": quantile(vals, 0.05),
        "median": quantile(vals, 0.50),
        "q95": quantile(vals, 0.95),
        "max": vals[-1] if vals else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    path = Path(args.csv_path)
    out = Path(args.out)

    result: dict = {
        "record": "KEIRIN_REAL_PRE_ONLY_SUITABILITY_AUDIT_RESULT_v1",
        "evidence_class": "REAL_PRE_ONLY_SUITABILITY_COMPATIBILITY_EVIDENCE_NOT_PREDICTIVE_PERFORMANCE",
        "target": path.name,
        "protected_boundaries": {
            "RESULT_PAYOUT": "NOT_ACCESSED",
            "outcome_metrics": "NOT_COMPUTED",
            "odds_price": "NOT_ACCESSED",
            "economics": "NOT_COMPUTED",
            "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
            "runtime": "OFF",
            "automatic_betting": False,
        },
    }

    digest = sha256(path)
    result["sha256"] = digest
    result["expected_sha256"] = EXPECTED_SHA256
    if digest != EXPECTED_SHA256:
        result["classification"] = "STOP_BYTE_IDENTITY_FAIL"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 10

    # Hash has passed. Decode only enough to inspect the header first.
    try:
        f = path.open("r", encoding="utf-8-sig", newline="")
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
    except UnicodeDecodeError:
        result["classification"] = "UNSUPPORTED_ENCODING_FAIL_CLOSED"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 11

    result["header"] = header
    bad = forbidden_columns(header)
    result["forbidden_columns_detected"] = bad
    if bad:
        result["classification"] = "FORBIDDEN_COLUMN_PRESENT_FAIL_CLOSED"
        f.close()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 12

    missing_direct = [c for c in DIRECT_N2 if c not in header]
    missing_full = [c for c in FULL_PRE_FLAT if c not in header]
    result["direct_n2_required_columns"] = DIRECT_N2
    result["missing_direct_n2_columns"] = missing_direct
    result["missing_full_pre_contract_flat_columns"] = missing_full

    if missing_direct:
        result["classification"] = "HEADER_MAPPING_REQUIRED_STOP_BEFORE_VALUE_READ"
        f.close()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 20

    # Only this branch is permitted to consume row values by the preregistration.
    missing = Counter()
    parse_fail = Counter()
    numeric_values: dict[str, list[float]] = defaultdict(list)
    categorical_counts = {k: Counter() for k in ("class", "style", "bank_length_m", "line_size")}
    races: dict[str, list[dict]] = defaultdict(list)
    row_count = 0

    for row in reader:
        row_count += 1
        for c in DIRECT_N2:
            if is_missing(row.get(c)):
                missing[c] += 1
        parsed = {}
        for c in NUMERIC:
            v = row.get(c)
            if is_missing(v):
                continue
            try:
                parsed[c] = float(v)
                numeric_values[c].append(parsed[c])
            except Exception:
                parse_fail[c] += 1
        categorical_counts["class"][str(row.get("class", "")).strip()] += 1
        categorical_counts["style"][str(row.get("style", "")).strip()] += 1
        categorical_counts["bank_length_m"][str(row.get("bank_length_m", "")).strip()] += 1
        categorical_counts["line_size"][str(row.get("line_size", "")).strip()] += 1
        races[str(row.get("race_id", "")).strip()].append({**row, "_parsed": parsed})
    f.close()

    result["row_count"] = row_count
    result["expected_rows"] = EXPECTED_ROWS
    result["row_count_match"] = row_count == EXPECTED_ROWS
    race_ids = [r for r in races.keys() if r]
    result["race_count"] = len(race_ids)
    result["expected_races"] = EXPECTED_RACES
    result["race_count_match"] = len(race_ids) == EXPECTED_RACES
    result["missing_counts"] = dict(missing)
    result["numeric_parse_failures"] = dict(parse_fail)

    race_size_counts = Counter(len(races[r]) for r in race_ids)
    result["race_size_counts"] = {str(k): v for k, v in sorted(race_size_counts.items())}
    mixed_event = any(k != 7 for k in race_size_counts)

    line_errors = Counter()
    for rid in race_ids:
        rows = races[rid]
        cars = []
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            p = row["_parsed"]
            car = p.get("car_no")
            if car is not None:
                cars.append(car)
            groups[str(row.get("line_group_id", "")).strip()].append(row)
        if len(cars) != len(set(cars)):
            line_errors["duplicate_car_no_within_race"] += 1
        for gid, members in groups.items():
            positions = [m["_parsed"].get("line_position") for m in members]
            sizes = [m["_parsed"].get("line_size") for m in members]
            if any(x is None for x in positions):
                line_errors["missing_or_unparsed_line_position_group"] += 1
            elif sorted(positions) != [float(i) for i in range(len(members))]:
                line_errors["noncontiguous_line_position_group"] += 1
            if any(x is None for x in sizes):
                line_errors["missing_or_unparsed_line_size_group"] += 1
            elif any(x != float(len(members)) for x in sizes):
                line_errors["line_size_membership_mismatch_group"] += 1
    result["line_structure_error_counts"] = dict(line_errors)

    result["distribution_summary"] = {
        "score": summary_numeric(numeric_values["score"]),
        "wind_speed_mps": summary_numeric(numeric_values["wind_speed_mps"]),
        "bank_length_m_counts": dict(categorical_counts["bank_length_m"]),
        "class_counts": dict(categorical_counts["class"]),
        "style_counts": dict(categorical_counts["style"]),
        "line_size_counts": dict(categorical_counts["line_size"]),
        "race_size_counts": result["race_size_counts"],
    }

    unsupported = {
        "class": sorted(k for k in categorical_counts["class"] if k and k not in SUPPORTED["class"]),
        "style": sorted(k for k in categorical_counts["style"] if k and k not in SUPPORTED["style"]),
        "bank_length_m": sorted({v for v in numeric_values["bank_length_m"] if v not in SUPPORTED["bank_length_m"]}),
        "line_position": sorted({v for v in numeric_values["line_position"] if v not in SUPPORTED["line_position"]}),
        "line_size": sorted({v for v in numeric_values["line_size"] if v not in SUPPORTED["line_size"]}),
    }
    result["outside_frozen_synthetic_categorical_support"] = unsupported

    strict_value_failure = bool(missing or parse_fail or line_errors)
    if strict_value_failure:
        classification = "DIRECT_N2_VALUE_OR_LINE_INVARIANT_FAILURE"
    elif mixed_event:
        classification = "MIXED_EVENT_FORMAT_REQUIRES_EXPLICIT_ROUTING"
    elif missing_full:
        classification = "DIRECT_N2_COLUMNS_PRESENT_FULL_PRE_CONTRACT_MISSING"
    else:
        classification = "DIRECT_N2_PRE_ONLY_INTERFACE_COMPATIBLE_FOR_AUDIT"
    result["classification"] = classification
    result["predictive_performance_claim"] = False
    result["model_promotion"] = False

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
