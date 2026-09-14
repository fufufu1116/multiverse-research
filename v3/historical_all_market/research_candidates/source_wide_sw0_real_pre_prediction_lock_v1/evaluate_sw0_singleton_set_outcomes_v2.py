#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_RESULT_KEYS = {
    "first_set", "parser", "race_date", "race_id", "second_set", "status", "third_set"
}
EXPECTED_PARSER = "result-v4.1-tie-aware"
RACE_ID_RE = re.compile(rb'"race_id"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"')

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def raw_extract_race_id(line, lineno):
    matches = list(RACE_ID_RE.finditer(line))
    if len(matches) != 1:
        raise SystemExit(f"FAIL_CLOSED:RACE_ID_RAW_EXTRACTION:{lineno}:{len(matches)}")
    quoted = b'"' + matches[0].group(1) + b'"'
    try:
        rid = json.loads(quoted.decode("utf-8"))
    except Exception:
        raise SystemExit(f"FAIL_CLOSED:RACE_ID_RAW_DECODE:{lineno}")
    if not isinstance(rid, str) or not rid:
        raise SystemExit(f"FAIL_CLOSED:RACE_ID_BAD_TYPE:{lineno}")
    return rid

def load_predictions(path, expected_sha, expected_count=1500):
    if sha256_file(path) != expected_sha:
        raise SystemExit("FAIL_CLOSED:PREDICTION_SHA_MISMATCH")
    rows = []
    seen = set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                raise SystemExit(f"FAIL_CLOSED:BLANK_PREDICTION_LINE:{lineno}")
            x = json.loads(line)
            if set(x.keys()) != {"race_id", "dev_index", "ordered_top3_probabilities"}:
                raise SystemExit(f"FAIL_CLOSED:PREDICTION_SCHEMA:{lineno}")
            rid = str(x["race_id"])
            if rid in seen:
                raise SystemExit("FAIL_CLOSED:DUPLICATE_PREDICTION_RACE")
            seen.add(rid)
            probs = x["ordered_top3_probabilities"]
            if not probs:
                raise SystemExit("FAIL_CLOSED:EMPTY_PROBABILITY_TABLE")
            mass = sum(float(t[3]) for t in probs)
            if not math.isfinite(mass) or abs(mass - 1.0) > 1e-8:
                raise SystemExit("FAIL_CLOSED:PROBABILITY_MASS")
            rows.append(x)
    if len(rows) != expected_count:
        raise SystemExit(f"FAIL_CLOSED:PREDICTION_COUNT:{len(rows)}")
    if expected_count == 1500 and sorted(r["dev_index"] for r in rows) != list(range(1, 1501)):
        raise SystemExit("FAIL_CLOSED:PREDICTION_UNIVERSE")
    return rows

def validate_rank_set(v, key, lineno):
    if not isinstance(v, list):
        raise SystemExit(f"FAIL_CLOSED:{key.upper()}_NOT_LIST:{lineno}")
    if any(not isinstance(x, int) or isinstance(x, bool) for x in v):
        raise SystemExit(f"FAIL_CLOSED:{key.upper()}_NON_INTEGER:{lineno}")
    if len(v) != len(set(v)):
        raise SystemExit(f"FAIL_CLOSED:{key.upper()}_DUPLICATE_MEMBER:{lineno}")
    return v

def load_strict_singleton_outcomes(path, expected_sha, ab_ids, expected_total_lines=2000,
                                   expected_ab_count=1500, min_strict_count=1487):
    if sha256_file(path) != expected_sha:
        raise SystemExit("FAIL_CLOSED:OUTCOME_SHA_MISMATCH")
    total = 0
    seen = set()
    strict = {}
    excluded_shapes = Counter()
    with open(path, "rb") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                raise SystemExit(f"FAIL_CLOSED:BLANK_RESULT_LINE:{lineno}")
            total += 1
            rid = raw_extract_race_id(line, lineno)
            if rid not in ab_ids:
                continue
            if rid in seen:
                raise SystemExit("FAIL_CLOSED:DUPLICATE_AB_RESULT_RACE")
            seen.add(rid)
            obj = json.loads(line.decode("utf-8"))
            if not isinstance(obj, dict) or set(obj.keys()) != EXPECTED_RESULT_KEYS:
                raise SystemExit(f"FAIL_CLOSED:AB_RESULT_SCHEMA:{lineno}")
            if obj["parser"] != EXPECTED_PARSER:
                raise SystemExit(f"FAIL_CLOSED:PARSER_DRIFT:{lineno}")
            if not isinstance(obj["status"], str):
                raise SystemExit(f"FAIL_CLOSED:STATUS_TYPE:{lineno}")
            if not isinstance(obj["race_date"], str):
                raise SystemExit(f"FAIL_CLOSED:RACE_DATE_TYPE:{lineno}")
            fs = validate_rank_set(obj["first_set"], "first_set", lineno)
            ss = validate_rank_set(obj["second_set"], "second_set", lineno)
            ts = validate_rank_set(obj["third_set"], "third_set", lineno)
            if (set(fs) & set(ss)) or (set(fs) & set(ts)) or (set(ss) & set(ts)):
                raise SystemExit(f"FAIL_CLOSED:RANK_SET_OVERLAP:{lineno}")
            shape = (len(fs), len(ss), len(ts))
            if shape == (1, 1, 1):
                outcome = (fs[0], ss[0], ts[0])
                if len(set(outcome)) != 3:
                    raise SystemExit(f"FAIL_CLOSED:STRICT_ORDER_DUPLICATE:{lineno}")
                strict[rid] = outcome
            else:
                excluded_shapes[shape] += 1
    if total != expected_total_lines:
        raise SystemExit(f"FAIL_CLOSED:TOTAL_LINE_COUNT:{total}")
    if len(seen) != expected_ab_count:
        raise SystemExit(f"FAIL_CLOSED:AB_RESULT_COUNT:{len(seen)}")
    if len(strict) < min_strict_count:
        raise SystemExit(f"FAIL_CLOSED:STRICT_COVERAGE_BELOW_PREREG:{len(strict)}")
    return strict, excluded_shapes, total, len(seen)

def race_metrics(pred, outcome):
    table = {(int(a), int(b), int(c)): float(p) for a, b, c, p in pred["ordered_top3_probabilities"]}
    entrants = sorted({k for t in table for k in t})
    n = len(entrants)
    if outcome not in table:
        raise SystemExit("FAIL_CLOSED:OUTCOME_CAR_NOT_IN_PREDICTION")
    p_exact = table[outcome]
    if p_exact <= 0 or not math.isfinite(p_exact):
        raise SystemExit("FAIL_CLOSED:ZERO_OR_NONFINITE_OBSERVED_PROB")
    win = defaultdict(float)
    for (a, b, c), p in table.items():
        win[a] += p
    y = outcome[0]
    pwin = win[y]
    if pwin <= 0 or pwin >= 1 + 1e-10:
        raise SystemExit("FAIL_CLOSED:WINNER_MARGINAL")
    top1 = max(entrants, key=lambda car: (win[car], -car))
    pred_exact = max(table, key=lambda t: (table[t], tuple(-x for x in t)))
    setp = defaultdict(float)
    for t, p in table.items():
        setp[tuple(sorted(t))] += p
    pred_set = max(setp, key=lambda s: (setp[s], tuple(-x for x in s)))
    brier = sum((win[c] - (1.0 if c == y else 0.0)) ** 2 for c in entrants)
    uniform_exact = 1.0 / (n * (n - 1) * (n - 2))
    uniform_win = 1.0 / n
    uniform_brier = sum((uniform_win - (1.0 if c == y else 0.0)) ** 2 for c in entrants)
    return {
        "dev_index": pred["dev_index"],
        "sw0_exact_nll": -math.log(p_exact),
        "uniform_exact_nll": -math.log(uniform_exact),
        "sw0_win_nll": -math.log(pwin),
        "uniform_win_nll": -math.log(uniform_win),
        "sw0_brier": brier,
        "uniform_brier": uniform_brier,
        "top1_hit": int(top1 == y),
        "ordered_top3_hit": int(pred_exact == outcome),
        "unordered_top3_hit": int(tuple(sorted(outcome)) == pred_set),
    }

def mean(xs):
    if not xs:
        raise SystemExit("FAIL_CLOSED:EMPTY_METRIC_SEGMENT")
    return sum(xs) / len(xs)

def summarize(ms):
    return {
        "race_count": len(ms),
        "mean_sw0_exact_nll": mean([m["sw0_exact_nll"] for m in ms]),
        "mean_uniform_exact_nll": mean([m["uniform_exact_nll"] for m in ms]),
        "primary_effect_uniform_minus_sw0": mean([m["uniform_exact_nll"] - m["sw0_exact_nll"] for m in ms]),
        "mean_sw0_win_nll": mean([m["sw0_win_nll"] for m in ms]),
        "mean_uniform_win_nll": mean([m["uniform_win_nll"] for m in ms]),
        "mean_sw0_brier": mean([m["sw0_brier"] for m in ms]),
        "mean_uniform_brier": mean([m["uniform_brier"] for m in ms]),
        "winner_brier_improvement": mean([m["uniform_brier"] - m["sw0_brier"] for m in ms]),
        "top1_accuracy": mean([m["top1_hit"] for m in ms]),
        "ordered_top3_hit_rate": mean([m["ordered_top3_hit"] for m in ms]),
        "unordered_top3_set_hit_rate": mean([m["unordered_top3_hit"] for m in ms]),
    }

def bootstrap_effect(ms, reps=10000, seed=20260914):
    vals = [m["uniform_exact_nll"] - m["sw0_exact_nll"] for m in ms]
    n = len(vals)
    if n == 0:
        raise SystemExit("FAIL_CLOSED:EMPTY_BOOTSTRAP")
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        out.append(sum(vals[rng.randrange(n)] for __ in range(n)) / n)
    out.sort()
    return [out[int(0.025 * reps)], out[int(0.975 * reps) - 1]]

def evaluate(prediction_path, prediction_sha, outcome_path, outcome_sha,
             expected_prediction_count=1500, expected_total_lines=2000,
             min_strict_count=1487, bootstrap_reps=10000, bootstrap_seed=20260914):
    preds = load_predictions(prediction_path, prediction_sha, expected_prediction_count)
    by_rid = {p["race_id"]: p for p in preds}
    strict, excluded_shapes, total, ab_count = load_strict_singleton_outcomes(
        outcome_path, outcome_sha, set(by_rid),
        expected_total_lines=expected_total_lines,
        expected_ab_count=expected_prediction_count,
        min_strict_count=min_strict_count,
    )
    ms = [race_metrics(p, strict[p["race_id"]]) for p in preds if p["race_id"] in strict]
    pooled = summarize(ms)
    a = summarize([m for m in ms if m["dev_index"] <= 1000])
    b = summarize([m for m in ms if m["dev_index"] >= 1001])
    ci = bootstrap_effect(ms, reps=bootstrap_reps, seed=bootstrap_seed)
    strong = (
        pooled["primary_effect_uniform_minus_sw0"] > 0
        and ci[0] > 0
        and a["primary_effect_uniform_minus_sw0"] > 0
        and b["primary_effect_uniform_minus_sw0"] > 0
        and pooled["winner_brier_improvement"] > 0
    )
    if strong:
        verdict = "STRONG_PREDICTIVE_SIGNAL_STRICT_SINGLETON_SUBSET"
    elif pooled["primary_effect_uniform_minus_sw0"] > 0:
        verdict = "POSITIVE_BUT_UNCERTAIN_STRICT_SINGLETON_SUBSET"
    else:
        verdict = "NO_PREDICTIVE_SIGNAL_STRICT_SINGLETON_SUBSET"
    return {
        "verdict": verdict,
        "evidence_class": "LINEAGE_LOCAL_PREOUTCOME_HISTORICAL_PREDICTIVE_EVALUATION_STRICT_SINGLETON_OUTCOME_SUBSET_NOT_GLOBAL_UNTOUCHED_HOLDOUT",
        "claim_scope": "STRICT_SINGLETON_FIRST_SECOND_THIRD_SET_ROWS_ONLY_NOT_SOURCE_WIDE",
        "coverage": {
            "total_result_lines": total,
            "ab_result_rows": ab_count,
            "strict_singleton_rows_scored": len(strict),
            "non_strict_rows_excluded_from_scoring": ab_count - len(strict),
            "excluded_shape_histogram": {
                f"{a}-{b}-{c}": n for (a, b, c), n in sorted(excluded_shapes.items())
            },
            "minimum_preregistered_strict_count": min_strict_count,
        },
        "pooled": pooled,
        "segment_A": a,
        "segment_B": b,
        "primary_effect_bootstrap_95pct": ci,
        "method": {
            "parser_required": EXPECTED_PARSER,
            "non_singleton_tie_rows_scalarized": False,
            "bootstrap_reps": bootstrap_reps,
            "bootstrap_seed": bootstrap_seed,
        },
        "prohibitions": {
            "model_promotion": True,
            "odds_price_payout_economics": True,
            "DEV2000_C": True,
            "ECON_HOLDOUT1000": True,
        },
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--prediction-sha256", required=True)
    ap.add_argument("--outcomes", required=True)
    ap.add_argument("--outcome-sha256", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--minimum-strict-count", type=int, default=1487)
    args = ap.parse_args()
    result = evaluate(
        args.predictions, args.prediction_sha256,
        args.outcomes, args.outcome_sha256,
        min_strict_count=args.minimum_strict_count,
    )
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
