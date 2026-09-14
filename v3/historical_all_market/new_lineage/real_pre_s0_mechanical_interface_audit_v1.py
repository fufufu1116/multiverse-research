from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

EXPECTED_SHA256 = "4fb0a2e9ede9aa343fa7828a65099beb2e4ce8ee76522c9952331ad536b0db84"
ALLOWED_VALUE_KEYS = {"race_id", "car_no", "class", "style", "score"}
FORBIDDEN_KEY_TOKENS = (
    "result", "payout", "outcome", "settlement", "odds", "price", "economics", "roi", "profit"
)
CLASS_COEF = {"A1": 0.05, "A2": -0.03, "A3": 0.0, "S1": 0.08, "S2": -0.03}
STYLE_COEF = {"逃": 0.06, "両": 0.04, "追": 0.0}
SHRINK = 0.7677543186180422


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _scan_string_end(s: str, i: int) -> int:
    assert s[i] == '"'
    i += 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            return i + 1
        i += 1
    raise ValueError("unterminated_string")


def _scan_value_end(s: str, i: int) -> int:
    i = _skip_ws(s, i)
    if i >= len(s):
        raise ValueError("missing_value")
    ch = s[i]
    if ch == '"':
        return _scan_string_end(s, i)
    if ch in "[{":
        open_ch, close_ch = ("[", "]") if ch == "[" else ("{", "}")
        depth = 1
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
                elif c == open_ch:
                    depth += 1
                elif c == close_ch:
                    depth -= 1
                    if depth == 0:
                        return i + 1
            i += 1
        raise ValueError("unterminated_container")
    j = i
    while j < len(s) and s[j] not in ",}":
        j += 1
    return j


def selective_object(line: str) -> tuple[dict, set[str]]:
    dec = json.JSONDecoder()
    i = _skip_ws(line, 0)
    if i >= len(line) or line[i] != "{":
        raise ValueError("row_not_object")
    i += 1
    selected: dict = {}
    keys: set[str] = set()
    while True:
        i = _skip_ws(line, i)
        if i < len(line) and line[i] == "}":
            break
        if i >= len(line) or line[i] != '"':
            raise ValueError("expected_key")
        key, end = dec.raw_decode(line, i)
        if not isinstance(key, str):
            raise ValueError("key_not_string")
        keys.add(key)
        i = _skip_ws(line, end)
        if i >= len(line) or line[i] != ":":
            raise ValueError("expected_colon")
        i = _skip_ws(line, i + 1)
        if key in ALLOWED_VALUE_KEYS:
            value, i = dec.raw_decode(line, i)
            selected[key] = value
        else:
            i = _scan_value_end(line, i)
        i = _skip_ws(line, i)
        if i < len(line) and line[i] == ",":
            i += 1
            continue
        if i < len(line) and line[i] == "}":
            break
        raise ValueError("expected_comma_or_end")
    return selected, keys


def pl_top3(utilities: dict[int, float]) -> dict[tuple[int, int, int], float]:
    cars = sorted(utilities)
    m = max(utilities.values())
    w = {c: math.exp(utilities[c] - m) for c in cars}
    total1 = sum(w.values())
    out = {}
    for a, b, c in permutations(cars, 3):
        p1 = w[a] / total1
        total2 = total1 - w[a]
        p2 = w[b] / total2
        total3 = total2 - w[b]
        p3 = w[c] / total3
        out[(a, b, c)] = p1 * p2 * p3
    return out


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit.py PRE_STRUCTURED.jsonl.gz OUT.json")
    src, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    actual_sha = sha256_file(src)
    if actual_sha != EXPECTED_SHA256:
        raise RuntimeError(f"source_sha256_mismatch:{actual_sha}")

    rows = 0
    missing = Counter()
    types = {k: Counter() for k in ALLOWED_VALUE_KEYS}
    classes, styles = Counter(), Counter()
    races: dict[str, list[dict]] = defaultdict(list)
    union_keys: set[str] = set()

    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            selected, keys = selective_object(line)
            union_keys.update(keys)
            bad_keys = sorted(k for k in keys if any(tok in k.lower() for tok in FORBIDDEN_KEY_TOKENS))
            if bad_keys:
                raise RuntimeError(f"forbidden_key_detected_line_{line_no}:{bad_keys}")
            rows += 1
            for key in ALLOWED_VALUE_KEYS:
                if key not in selected or selected[key] is None:
                    missing[key] += 1
                else:
                    types[key][type(selected[key]).__name__] += 1
            if any(k not in selected or selected[k] is None for k in ALLOWED_VALUE_KEYS):
                continue
            race_id = str(selected["race_id"])
            car_no = selected["car_no"]
            cls = selected["class"]
            sty = selected["style"]
            score = selected["score"]
            if not isinstance(car_no, int) or isinstance(car_no, bool):
                raise RuntimeError(f"unsupported_car_no_type_line_{line_no}")
            if not isinstance(cls, str) or cls not in CLASS_COEF:
                raise RuntimeError(f"unsupported_class_line_{line_no}:{cls!r}")
            if not isinstance(sty, str) or sty not in STYLE_COEF:
                raise RuntimeError(f"unsupported_style_line_{line_no}:{sty!r}")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(float(score)):
                raise RuntimeError(f"unsupported_score_line_{line_no}")
            classes[cls] += 1
            styles[sty] += 1
            races[race_id].append({"car_no": car_no, "class": cls, "style": sty, "score": float(score)})

    required_missing_from_schema = sorted(ALLOWED_VALUE_KEYS - union_keys)
    if required_missing_from_schema:
        raise RuntimeError(f"required_keys_absent:{required_missing_from_schema}")

    valid_races = 0
    malformed_races = 0
    generated_probs = 0
    max_mass_error = 0.0
    min_prob = 1.0
    max_prob = 0.0
    all_finite = True
    all_nonnegative = True

    for race_rows in races.values():
        cars = [r["car_no"] for r in race_rows]
        if len(race_rows) != 7 or len(set(cars)) != 7:
            malformed_races += 1
            continue
        util = {
            r["car_no"]: SHRINK * r["score"] + CLASS_COEF[r["class"]] + STYLE_COEF[r["style"]]
            for r in race_rows
        }
        probs = pl_top3(util)
        vals = list(probs.values())
        mass = sum(vals)
        err = abs(mass - 1.0)
        max_mass_error = max(max_mass_error, err)
        min_prob = min(min_prob, min(vals))
        max_prob = max(max_prob, max(vals))
        finite_here = all(math.isfinite(x) for x in vals)
        nonnegative_here = all(x >= 0.0 for x in vals)
        all_finite = all_finite and finite_here
        all_nonnegative = all_nonnegative and nonnegative_here
        generated_probs += len(vals)
        valid_races += 1

    passed = (
        valid_races > 0
        and all_finite
        and all_nonnegative
        and max_mass_error <= 1e-10
        and all(missing[k] == 0 for k in ALLOWED_VALUE_KEYS)
    )
    result = {
        "record": "KEIRIN_REAL_PRE_S0_MECHANICAL_INTERFACE_RESULT_v1",
        "status": "PASS_MECHANICAL_COMPATIBILITY" if passed else "FAIL_MECHANICAL_COMPATIBILITY",
        "evidence_class": "REAL_PRE_MECHANICAL_INTERFACE_COMPATIBILITY_ONLY_NOT_PREDICTIVE_PERFORMANCE",
        "source_identity": {"sha256_expected": EXPECTED_SHA256, "sha256_actual": actual_sha},
        "authorized_value_fields": ["car_no", "class", "style", "score"],
        "identity_only_field": "race_id",
        "rows_seen": rows,
        "unique_race_ids": len(races),
        "missingness": {k: missing[k] for k in sorted(ALLOWED_VALUE_KEYS)},
        "types": {k: dict(types[k]) for k in sorted(ALLOWED_VALUE_KEYS)},
        "support": {"class": dict(sorted(classes.items())), "style": dict(sorted(styles.items()))},
        "race_shape": {"valid_7_unique_car_races": valid_races, "malformed_or_non7_races": malformed_races},
        "probability_sanity": {"generated_ordered_top3_values": generated_probs, "all_finite": all_finite, "all_nonnegative": all_nonnegative, "max_abs_mass_error": max_mass_error, "min_probability": min_prob if generated_probs else None, "max_probability": max_prob if generated_probs else None},
        "frozen_S0_unchanged": True,
        "training_fit_selection": False,
        "model_promotion": False,
        "real_predictive_performance_claim": False,
        "protected_boundaries": {"RESULT_PAYOUT":"NOT_ACCESSED","outcome_settlement":"NOT_ACCESSED","odds_price":"NOT_ACCESSED","economics_ROI_profit":"NOT_ACCESSED_NOT_COMPUTED","ECON_HOLDOUT1000":"SEALED_NOT_ACCESSED","DEV2000_C_results":"NOT_ACCESSED","runtime":"OFF","automatic_betting":False}
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rows_seen": rows, "unique_race_ids": len(races), "valid_races": valid_races, "max_abs_mass_error": max_mass_error}, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
