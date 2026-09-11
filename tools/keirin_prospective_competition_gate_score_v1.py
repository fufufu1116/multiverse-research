#!/usr/bin/env python3
"""Prospective strict-0.40 race-gate score producer.

Replays the frozen S0/challenger PRE-only confidence gate recovered from the
Sep-10/11 forward-lane authority.  This is NOT the rider's 65-111-ish
`competition_score`; it produces the race-level scalar consumed by the later
0.40 selector gate.

Rule:
- S0 logits: beta * rider competition_score.
- Challenger logits: S0 + circumference-signed exact-rider delta when frozen
  support exists, else circumference-signed frozen style delta, else S0.
- softmax each model within the race.
- if S0/challenger Top1 disagree: race gate score = 0.0 (agreement gate fails).
- if they agree: race gate score = min(S0 Top1 probability,
  challenger Top1 probability).

No outcomes, payouts, odds, fitting, retuning, or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

MODEL_FREEZE_REL = "v3/historical_all_market/research_candidates/KEIRIN_PRE_ONLY_RIDER_OR_STYLE_CIRCUMFERENCE_MODEL_FREEZE_20260908_v2.json"
MODEL_FREEZE_GIT_BLOB = "061ef5b227fc78fdf35a1dd9ef48e3c16a1ea878"
EXPECTED_BETA = 0.22260435254784533
EXPECTED_STYLE_DELTAS = {
    "逃": -0.020537046719,
    "追": 0.038120995374,
    "両": 0.0024804485,
}
CIRCUMFERENCE_Q = {"400": -1.0, "333_OR_333_33": 1.0}
FORBIDDEN_KEYS = (
    "result", "outcome", "payout", "refund", "finish", "winner", "着順", "払戻", "確定"
)


class FailClosed(RuntimeError):
    pass


def git_blob_sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()


def _scan_forbidden(x: Any, path: str = "root") -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            s = str(k).lower()
            if any(tok.lower() in s for tok in FORBIDDEN_KEYS):
                raise FailClosed(f"forbidden_outcome_key:{path}.{k}")
            _scan_forbidden(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _scan_forbidden(v, f"{path}[{i}]")


def _finite(v: Any, label: str) -> float:
    if isinstance(v, bool):
        raise FailClosed(f"{label}:not_numeric")
    try:
        x = float(v)
    except Exception as e:
        raise FailClosed(f"{label}:not_numeric") from e
    if not math.isfinite(x):
        raise FailClosed(f"{label}:not_finite")
    return x


def _softmax(logits: dict[int, float]) -> dict[int, float]:
    if len(logits) < 2:
        raise FailClosed("race_requires_at_least_two_active_entrants")
    m = max(logits.values())
    ex = {k: math.exp(v - m) for k, v in logits.items()}
    z = sum(ex.values())
    if not math.isfinite(z) or z <= 0:
        raise FailClosed("softmax_normalizer_invalid")
    out = {k: v / z for k, v in ex.items()}
    if abs(sum(out.values()) - 1.0) > 1e-12:
        raise FailClosed("softmax_sum_drift")
    return out


def _top1(probs: dict[int, float]) -> int:
    # Stable deterministic tie break: lower car number.
    return min(probs, key=lambda car: (-probs[car], car))


def load_frozen_model(repo_root: Path) -> dict[str, Any]:
    p = repo_root / MODEL_FREEZE_REL
    if not p.is_file():
        raise FailClosed(f"missing_frozen_model:{MODEL_FREEZE_REL}")
    raw = p.read_bytes()
    observed = git_blob_sha1_bytes(raw)
    if observed != MODEL_FREEZE_GIT_BLOB:
        raise FailClosed(f"frozen_model_blob_mismatch:{observed}")
    try:
        model = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise FailClosed("frozen_model_json_invalid") from e
    beta = _finite(model.get("baseline", {}).get("beta"), "baseline.beta")
    if abs(beta - EXPECTED_BETA) > 1e-15:
        raise FailClosed("frozen_beta_drift")
    styles = model.get("style_level", model.get("style_fallback", {})).get("lookup")
    if not isinstance(styles, dict):
        # Current frozen artifact stores the style block under a nearby namespace;
        # locate exactly one lookup matching the expected three styles, otherwise fail.
        matches: list[dict[str, Any]] = []
        def walk(x: Any) -> None:
            if isinstance(x, dict):
                lk = x.get("lookup")
                if isinstance(lk, dict) and set(EXPECTED_STYLE_DELTAS).issubset(lk):
                    matches.append(lk)
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(model)
        if len(matches) != 1:
            raise FailClosed(f"frozen_style_lookup_ambiguous:{len(matches)}")
        styles = matches[0]
    for style, exp in EXPECTED_STYLE_DELTAS.items():
        got = _finite(styles.get(style, {}).get("delta_logit"), f"style.{style}.delta_logit")
        if abs(got - exp) > 1e-12:
            raise FailClosed(f"frozen_style_delta_drift:{style}")
    return model


def _rider_delta_map(model: dict[str, Any]) -> dict[str, float]:
    rows = model.get("rider_level", {}).get("lookup")
    if not isinstance(rows, list):
        raise FailClosed("frozen_rider_lookup_missing")
    out: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise FailClosed("frozen_rider_lookup_row_invalid")
        reg = str(row.get("official_registration_number", "")).strip()
        if not reg:
            raise FailClosed("frozen_rider_registration_missing")
        if reg in out:
            raise FailClosed(f"frozen_rider_registration_duplicate:{reg}")
        out[reg] = _finite(row.get("delta_logit"), f"rider.{reg}.delta_logit")
    return out


def produce_gate_score(pre_payload: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    _scan_forbidden(pre_payload)
    qkey = str(pre_payload.get("circumference_bucket", "")).strip()
    if qkey not in CIRCUMFERENCE_Q:
        raise FailClosed(f"unsupported_circumference_bucket:{qkey}")
    q = CIRCUMFERENCE_Q[qkey]
    entrants = pre_payload.get("entrants")
    if not isinstance(entrants, list) or len(entrants) < 2:
        raise FailClosed("entrants_missing_or_too_short")
    beta = _finite(model.get("baseline", {}).get("beta"), "baseline.beta")
    rider_delta = _rider_delta_map(model)
    style_delta = dict(EXPECTED_STYLE_DELTAS)
    s0_logits: dict[int, float] = {}
    ch_logits: dict[int, float] = {}
    support_mode: dict[int, str] = {}
    seen: set[int] = set()
    for i, row in enumerate(entrants):
        if not isinstance(row, dict):
            raise FailClosed(f"entrant_{i}:not_object")
        if row.get("withdrawn") is True:
            continue
        car = int(row.get("car_no"))
        if car <= 0 or car in seen:
            raise FailClosed(f"entrant_{i}:invalid_or_duplicate_car")
        seen.add(car)
        score = _finite(row.get("competition_score"), f"entrant_{car}.competition_score")
        reg = str(row.get("registration_number", row.get("official_registration_number", ""))).strip()
        style = str(row.get("style", "")).strip()
        base = beta * score
        if reg and reg in rider_delta:
            delta = q * rider_delta[reg]
            mode = "EXACT_RIDER"
        elif style in style_delta:
            delta = q * style_delta[style]
            mode = "STYLE_FALLBACK"
        else:
            delta = 0.0
            mode = "S0_FALLBACK"
        s0_logits[car] = base
        ch_logits[car] = base + delta
        support_mode[car] = mode
    s0 = _softmax(s0_logits)
    ch = _softmax(ch_logits)
    s0_top = _top1(s0)
    ch_top = _top1(ch)
    agree = s0_top == ch_top
    gate_score = min(s0[s0_top], ch[ch_top]) if agree else 0.0
    return {
        "record": "KEIRIN_PROSPECTIVE_COMPETITION_GATE_SCORE_v1",
        "semantic_name": "conservative_top1_probability_with_same_top1_agreement",
        "value": gate_score,
        "top1_agreement": agree,
        "s0_top1_car_no": s0_top,
        "challenger_top1_car_no": ch_top,
        "s0_top1_probability": s0[s0_top],
        "challenger_top1_probability": ch[ch_top],
        "threshold": 0.40,
        "gate_pass": bool(agree and gate_score >= 0.40),
        "circumference_bucket": qkey,
        "support_mode_by_car": {str(k): v for k, v in sorted(support_mode.items())},
        "s0_probabilities": {str(k): v for k, v in sorted(s0.items())},
        "challenger_probabilities": {str(k): v for k, v in sorted(ch.items())},
        "frozen_model_path": MODEL_FREEZE_REL,
        "frozen_model_git_blob": MODEL_FREEZE_GIT_BLOB,
        "beta": EXPECTED_BETA,
        "retune": False,
        "result_accessed": False,
        "payout_accessed": False,
        "odds_accessed": False,
        "network_access": False,
        "runtime": "OFF",
        "automatic_betting": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pre_payload_json")
    ap.add_argument("output_json")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args()
    inp = Path(a.pre_payload_json)
    out = Path(a.output_json)
    if out.exists():
        raise FailClosed("output_already_exists")
    pre = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(pre, dict):
        raise FailClosed("pre_payload_not_object")
    model = load_frozen_model(Path(a.repo_root).resolve())
    rec = produce_gate_score(pre, model)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
