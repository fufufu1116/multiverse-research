#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

EXPECTED_RESULT_KEYS = {
    "first_set", "parser", "race_date", "race_id", "second_set", "status", "third_set"
}
RACE_ID_RE = re.compile(rb'"race_id"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"')

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_prediction_race_ids(path, expected_sha256=None):
    if expected_sha256:
        got = sha256_file(path)
        if got != expected_sha256:
            raise ValueError(f"PREDICTION_SHA_MISMATCH:{got}")
    race_ids = set()
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                raise ValueError(f"BLANK_PREDICTION_LINE:{lineno}")
            obj = json.loads(line)
            if not isinstance(obj, dict) or "race_id" not in obj:
                raise ValueError(f"BAD_PREDICTION_RECORD:{lineno}")
            rid = str(obj["race_id"])
            if not rid:
                raise ValueError(f"EMPTY_PREDICTION_RACE_ID:{lineno}")
            race_ids.add(rid)
    return race_ids

def raw_extract_race_id(line, lineno):
    matches = list(RACE_ID_RE.finditer(line))
    if len(matches) != 1:
        raise ValueError(f"RACE_ID_RAW_EXTRACTION_FAILED:{lineno}:{len(matches)}")
    quoted = b'"' + matches[0].group(1) + b'"'
    try:
        rid = json.loads(quoted.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"RACE_ID_RAW_DECODE_FAILED:{lineno}") from e
    if not isinstance(rid, str) or not rid:
        raise ValueError(f"RACE_ID_BAD_TYPE:{lineno}")
    return rid

def classify_set_value(v):
    if not isinstance(v, list):
        return ("non_list", None, False, False)
    int_like = all(isinstance(x, int) and not isinstance(x, bool) for x in v)
    unique = len(v) == len(set(v)) if int_like else False
    return ("list", len(v), int_like, unique)

def characterize(result_path, prediction_path, expected_result_sha256=None,
                 expected_prediction_sha256=None, expected_ab_count=1500,
                 expected_total_lines=2000):
    if expected_result_sha256:
        got = sha256_file(result_path)
        if got != expected_result_sha256:
            raise ValueError(f"RESULT_SHA_MISMATCH:{got}")
    ab_ids = load_prediction_race_ids(prediction_path, expected_prediction_sha256)
    if len(ab_ids) != expected_ab_count:
        raise ValueError(f"AB_ALLOWLIST_COUNT_MISMATCH:{len(ab_ids)}")

    total = 0
    ab_seen = set()
    duplicate_ab = []
    exact_schema_ab = 0
    type_hist = {k: Counter() for k in ("first_set", "second_set", "third_set")}
    len_hist = {k: Counter() for k in ("first_set", "second_set", "third_set")}
    all_int = {k: True for k in ("first_set", "second_set", "third_set")}
    all_unique = {k: True for k in ("first_set", "second_set", "third_set")}
    disjoint_all = True
    parser_hist = Counter()
    status_type_hist = Counter()
    race_date_type_hist = Counter()

    with open(result_path, "rb") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                raise ValueError(f"BLANK_RESULT_LINE:{lineno}")
            total += 1
            rid = raw_extract_race_id(line, lineno)
            if rid not in ab_ids:
                continue
            if rid in ab_seen:
                duplicate_ab.append(rid)
                continue
            ab_seen.add(rid)
            obj = json.loads(line.decode("utf-8"))
            if not isinstance(obj, dict):
                raise ValueError(f"AB_NOT_OBJECT:{lineno}")
            if set(obj.keys()) != EXPECTED_RESULT_KEYS:
                raise ValueError(f"AB_SCHEMA_MISMATCH:{lineno}:{sorted(obj.keys())}")
            exact_schema_ab += 1

            sets = []
            for key in ("first_set", "second_set", "third_set"):
                kind, ln, int_like, unique = classify_set_value(obj[key])
                type_hist[key][kind] += 1
                if ln is not None:
                    len_hist[key][ln] += 1
                all_int[key] = all_int[key] and int_like
                all_unique[key] = all_unique[key] and unique
                if kind == "list" and int_like:
                    sets.append(set(obj[key]))
                else:
                    sets.append(None)
            if all(s is not None for s in sets):
                if (sets[0] & sets[1]) or (sets[0] & sets[2]) or (sets[1] & sets[2]):
                    disjoint_all = False
            else:
                disjoint_all = False

            parser_hist[str(obj["parser"])] += 1
            status_type_hist[type(obj["status"]).__name__] += 1
            race_date_type_hist[type(obj["race_date"]).__name__] += 1

    if total != expected_total_lines:
        raise ValueError(f"TOTAL_LINE_COUNT_MISMATCH:{total}")
    missing = sorted(ab_ids - ab_seen)
    if duplicate_ab:
        raise ValueError(f"DUPLICATE_AB_RACE_ID_COUNT:{len(duplicate_ab)}")
    if missing:
        raise ValueError(f"MISSING_AB_RACE_ID_COUNT:{len(missing)}")
    if exact_schema_ab != expected_ab_count:
        raise ValueError(f"AB_SCHEMA_COUNT_MISMATCH:{exact_schema_ab}")

    report = {
        "record": "KEIRIN_SW0_RESULT_SCHEMA_CHARACTERIZATION_v1",
        "classification": "STRUCTURAL_CHARACTERIZATION_ONLY_NO_PREDICTIVE_EVALUATION",
        "result_sha256": sha256_file(result_path),
        "prediction_sha256": sha256_file(prediction_path),
        "total_jsonl_lines": total,
        "ab_allowlist_race_count": len(ab_ids),
        "ab_rows_characterized": exact_schema_ab,
        "non_ab_rows_outcome_values_deserialized": False,
        "set_field_type_histograms": {k: dict(sorted(v.items())) for k, v in type_hist.items()},
        "set_field_length_histograms": {
            k: {str(kk): vv for kk, vv in sorted(v.items())} for k, v in len_hist.items()
        },
        "set_fields_all_integer_elements": all_int,
        "set_fields_all_unique_within_rank": all_unique,
        "rank_sets_pairwise_disjoint_all_ab": disjoint_all,
        "parser_value_histogram": dict(sorted(parser_hist.items())),
        "status_type_histogram": dict(sorted(status_type_hist.items())),
        "race_date_type_histogram": dict(sorted(race_date_type_hist.items())),
        "outcome_values_emitted": False,
        "prediction_probabilities_read_for_scoring": False,
        "predictive_metrics_computed": False,
        "economics_fields_accessed": False,
    }
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--prediction", required=True)
    ap.add_argument("--result-sha256", required=True)
    ap.add_argument("--prediction-sha256", required=True)
    ap.add_argument("--expected-ab-count", type=int, default=1500)
    ap.add_argument("--expected-total-lines", type=int, default=2000)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    report = characterize(
        args.result, args.prediction,
        expected_result_sha256=args.result_sha256,
        expected_prediction_sha256=args.prediction_sha256,
        expected_ab_count=args.expected_ab_count,
        expected_total_lines=args.expected_total_lines,
    )
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")

if __name__ == "__main__":
    main()
