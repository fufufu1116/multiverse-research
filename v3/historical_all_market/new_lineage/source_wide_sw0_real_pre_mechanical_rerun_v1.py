from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

EXPECTED_SHA256 = "4fb0a2e9ede9aa343fa7828a65099beb2e4ce8ee76522c9952331ad536b0db84"
RIDER_ALLOWED_VALUES = {"car_no", "class", "style", "score"}
FORBIDDEN_KEY_TOKENS = ("result", "payout", "outcome", "settlement", "odds", "price", "economics", "roi", "profit")
SHRINK = 0.7677543186180422


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def scan_string_end(s: str, i: int) -> int:
    if s[i] != '"':
        raise ValueError("expected_string")
    i += 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            return i + 1
        i += 1
    raise ValueError("unterminated_string")


def scan_value_end(s: str, i: int) -> int:
    i = skip_ws(s, i)
    if i >= len(s):
        raise ValueError("missing_value")
    if s[i] == '"':
        return scan_string_end(s, i)
    if s[i] in "[{":
        stack = ["]" if s[i] == "[" else "}"]
        i += 1
        in_str = False
        esc = False
        while i < len(s):
            c = s[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "[":
                    stack.append("]")
                elif c == "{":
                    stack.append("}")
                elif stack and c == stack[-1]:
                    stack.pop()
                    if not stack:
                        return i + 1
            i += 1
        raise ValueError("unterminated_container")
    j = i
    while j < len(s) and s[j] not in ",]}":
        j += 1
    return j


def bad_key(key: str) -> bool:
    return any(tok in key.lower() for tok in FORBIDDEN_KEY_TOKENS)


def parse_rider_object(s: str, i: int, decoder: json.JSONDecoder, keys_seen: set[str]) -> tuple[dict, int]:
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "{":
        raise ValueError("entrant_not_object")
    i += 1
    rider = {}
    while True:
        i = skip_ws(s, i)
        if i < len(s) and s[i] == "}":
            return rider, i + 1
        key, end = decoder.raw_decode(s, i)
        if not isinstance(key, str):
            raise ValueError("entrant_key_not_string")
        keys_seen.add(key)
        if bad_key(key):
            raise RuntimeError(f"forbidden_key:{key}")
        i = skip_ws(s, end)
        if i >= len(s) or s[i] != ":":
            raise ValueError("entrant_expected_colon")
        i = skip_ws(s, i + 1)
        if key in RIDER_ALLOWED_VALUES:
            value, i = decoder.raw_decode(s, i)
            rider[key] = value
        else:
            i = scan_value_end(s, i)
        i = skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "}":
            return rider, i + 1
        raise ValueError("entrant_expected_comma_or_end")


def parse_entrants(s: str, i: int, decoder: json.JSONDecoder, keys_seen: set[str]) -> tuple[list[dict], int]:
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "[":
        raise ValueError("entrants_not_array")
    i += 1
    entrants = []
    while True:
        i = skip_ws(s, i)
        if i < len(s) and s[i] == "]":
            return entrants, i + 1
        rider, i = parse_rider_object(s, i, decoder, keys_seen)
        entrants.append(rider)
        i = skip_ws(s, i)
        if i < len(s) and s[i] == ",":
            i += 1
            continue
        if i < len(s) and s[i] == "]":
            return entrants, i + 1
        raise ValueError("entrants_expected_comma_or_end")


def parse_race_line(line: str) -> tuple[str | None, list[dict], set[str]]:
    decoder = json.JSONDecoder()
    i = skip_ws(line, 0)
    if i >= len(line) or line[i] != "{":
        raise ValueError("race_row_not_object")
    i += 1
    race_id = None
    entrants = None
    keys_seen: set[str] = set()
    while True:
        i = skip_ws(line, i)
        if i < len(line) and line[i] == "}":
            break
        key, end = decoder.raw_decode(line, i)
        if not isinstance(key, str):
            raise ValueError("top_key_not_string")
        keys_seen.add(key)
        if bad_key(key):
            raise RuntimeError(f"forbidden_key:{key}")
        i = skip_ws(line, end)
        if i >= len(line) or line[i] != ":":
            raise ValueError("top_expected_colon")
        i = skip_ws(line, i + 1)
        if key == "race_id":
            race_id, i = decoder.raw_decode(line, i)
        elif key == "entrants":
            entrants, i = parse_entrants(line, i, decoder, keys_seen)
        else:
            i = scan_value_end(line, i)
        i = skip_ws(line, i)
        if i < len(line) and line[i] == ",":
            i += 1
            continue
        if i < len(line) and line[i] == "}":
            break
        raise ValueError("top_expected_comma_or_end")
    return None if race_id is None else str(race_id), [] if entrants is None else entrants, keys_seen


def pl_top3(score_by_car: dict[int, float]) -> list[float]:
    cars = sorted(score_by_car)
    shift = max(score_by_car.values())
    weight = {c: math.exp(SHRINK * score_by_car[c] - SHRINK * shift) for c in cars}
    total1 = sum(weight.values())
    out = []
    for a, b, c in permutations(cars, 3):
        p1 = weight[a] / total1
        total2 = total1 - weight[a]
        p2 = weight[b] / total2
        total3 = total2 - weight[b]
        p3 = weight[c] / total3
        out.append(p1 * p2 * p3)
    return out


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: rerun.py PRE_STRUCTURED.jsonl.gz OUT.json")
    src = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    actual_sha = sha256_file(src)
    if actual_sha != EXPECTED_SHA256:
        raise RuntimeError(f"source_sha256_mismatch:{actual_sha}")

    race_rows = 0
    entrant_rows = 0
    missing = Counter()
    types = {k: Counter() for k in ["race_id", "car_no", "class", "style", "score"]}
    class_support = Counter()
    style_support = Counter()
    entrant_count_distribution = Counter()
    keys_seen: set[str] = set()
    malformed_races = 0
    duplicate_car_races = 0
    generated_probability_values = 0
    all_finite = True
    all_nonnegative = True
    max_mass_error = 0.0
    min_probability = None
    max_probability = None

    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            race_id, entrants, line_keys = parse_race_line(line)
            keys_seen.update(line_keys)
            race_rows += 1
            if race_id is None:
                missing["race_id"] += 1
                malformed_races += 1
                continue
            types["race_id"]["str"] += 1
            entrant_count_distribution[len(entrants)] += 1
            if len(entrants) < 3:
                malformed_races += 1
                continue

            cars = []
            score_by_car = {}
            bad = False
            for rider in entrants:
                entrant_rows += 1
                for key in RIDER_ALLOWED_VALUES:
                    if key not in rider or rider[key] is None:
                        missing[key] += 1
                        bad = True
                    else:
                        types[key][type(rider[key]).__name__] += 1
                if bad:
                    continue
                car_no = rider["car_no"]
                cls = rider["class"]
                sty = rider["style"]
                score = rider["score"]
                if not isinstance(car_no, int) or isinstance(car_no, bool):
                    raise RuntimeError(f"unsupported_car_no_type_line_{line_no}")
                if not isinstance(cls, str):
                    raise RuntimeError(f"unsupported_class_type_line_{line_no}")
                if not isinstance(sty, str):
                    raise RuntimeError(f"unsupported_style_type_line_{line_no}")
                if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(float(score)):
                    raise RuntimeError(f"unsupported_score_line_{line_no}")
                cars.append(car_no)
                score_by_car[car_no] = float(score)
                class_support[cls] += 1
                style_support[sty] += 1

            if bad:
                malformed_races += 1
                continue
            if len(set(cars)) != len(cars):
                duplicate_car_races += 1
                malformed_races += 1
                continue

            probs = pl_top3(score_by_car)
            vals = list(probs)
            mass_error = abs(sum(vals) - 1.0)
            max_mass_error = max(max_mass_error, mass_error)
            finite_here = all(math.isfinite(p) for p in vals)
            nonnegative_here = all(p >= 0.0 for p in vals)
            all_finite = all_finite and finite_here
            all_nonnegative = all_nonnegative and nonnegative_here
            pmin, pmax = min(vals), max(vals)
            min_probability = pmin if min_probability is None else min(min_probability, pmin)
            max_probability = pmax if max_probability is None else max(max_probability, pmax)
            generated_probability_values += len(vals)

    required_keys = {"race_id", "entrants", "car_no", "class", "style", "score"}
    absent_keys = sorted(required_keys - keys_seen)
    passed = (
        not absent_keys
        and race_rows == 2000
        and malformed_races == 0
        and duplicate_car_races == 0
        and all(missing[k] == 0 for k in ["race_id", "car_no", "class", "style", "score"])
        and all_finite
        and all_nonnegative
        and max_mass_error <= 1e-10
    )
    result = {
        "record": "KEIRIN_SOURCE_WIDE_SW0_REAL_PRE_MECHANICAL_RERUN_RESULT_v1",
        "status": "PASS_SOURCE_WIDE_MECHANICAL_COMPATIBILITY" if passed else "FAIL_CLOSED_SOURCE_WIDE_MECHANICAL_COMPATIBILITY",
        "evidence_class": "REAL_PRE_MECHANICAL_INTERFACE_COMPATIBILITY_ONLY_NOT_PREDICTIVE_PERFORMANCE",
        "source_identity": {"sha256_expected": EXPECTED_SHA256, "sha256_actual": actual_sha},
        "selected_candidate": "SW0_SCORE_ONLY_PL",
        "utility_consumes_only": ["car_no", "score"],
        "authorized_values_decoded_only": ["race_id", "car_no", "class", "style", "score"],
        "unapproved_values_materialized": False,
        "race_rows": race_rows,
        "entrant_rows": entrant_rows,
        "entrant_count_distribution": dict(sorted(entrant_count_distribution.items())),
        "missingness": {k: missing[k] for k in ["race_id", "car_no", "class", "style", "score"]},
        "types": {k: dict(types[k]) for k in ["race_id", "car_no", "class", "style", "score"]},
        "support": {"class": dict(sorted(class_support.items())), "style": dict(sorted(style_support.items()))},
        "race_shape": {"malformed_races": malformed_races, "duplicate_car_races": duplicate_car_races},
        "probability_sanity": {
            "generated_ordered_top3_values": generated_probability_values,
            "all_finite": all_finite,
            "all_nonnegative": all_nonnegative,
            "max_abs_mass_error": max_mass_error,
            "min_probability": min_probability,
            "max_probability": max_probability
        },
        "forbidden_key_scan": "CLEAR",
        "frozen_candidate_unchanged": True,
        "frozen_S0_unchanged": True,
        "frozen_N2_unchanged": True,
        "real_PRE_fit_training_parameter_model_selection": False,
        "model_promotion": False,
        "real_predictive_performance_claim": False,
        "protected_boundaries": {
            "RESULT_PAYOUT": "NOT_ACCESSED",
            "outcome_settlement": "NOT_ACCESSED",
            "odds_price": "NOT_ACCESSED",
            "economics_ROI_profit": "NOT_ACCESSED_NOT_COMPUTED",
            "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
            "DEV2000_C_results": "NOT_ACCESSED",
            "runtime": "OFF",
            "automatic_betting": False
        }
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "race_rows": race_rows, "entrant_rows": entrant_rows, "generated_ordered_top3_values": generated_probability_values, "max_abs_mass_error": max_mass_error}, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
