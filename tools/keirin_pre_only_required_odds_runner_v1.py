#!/usr/bin/env python3
"""PRE-only candidate-ticket and raw break-even odds runner.

Purpose
-------
Continue prediction research without waiting for live odds. This runner reuses
and pins the exact ticket-probability construction already present in the frozen
prospective v54 v1 runner, and reuses the pinned race competition-gate producer.

It deliberately DOES NOT perform the market-dependent B1a_MKT50 transform,
shape-edge test, raw-EV ranking, staking, or final executable v54 selection.
Therefore its output is prediction-only research evidence, not an executable
frozen-v54 betting decision.

For each supported market it ranks raw B1A/Plackett-Luce ticket probabilities
and emits raw break-even decimal odds = 1 / q. Positive raw-model EV requires
actual decimal odds strictly greater than that threshold; exact v54 eligibility
may be stricter once the genuine PRE-close market snapshot is available.

No network, result, payout, fitting, retuning, overwrite, spend, or live effect.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

V1_REL = "tools/keirin_prospective_v54_decision_freeze_runner_v1.py"
V1_GIT_BLOB = "417fa8947ab9b15dde305adc15085d558659d134"
SCORE_PRODUCER_REL = "tools/keirin_prospective_competition_gate_score_v1.py"
SCORE_PRODUCER_GIT_BLOB = "8ffbab9d02562a3f8b617047c614a2008378932b"
COMPETITION_THRESHOLD = 0.40
SUPPORTED_MARKETS = ("3rentan", "2shatan")


class FailClosed(RuntimeError):
    pass


def git_blob_sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()


def _load_pinned(repo_root: Path, rel: str, expected_blob: str, module_name: str):
    p = repo_root / rel
    if not p.is_file():
        raise FailClosed(f"missing_pinned_module:{rel}")
    observed = git_blob_sha1_bytes(p.read_bytes())
    if observed != expected_blob:
        raise FailClosed(f"pinned_module_blob_mismatch:{rel}:{observed}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        raise FailClosed(f"cannot_import_pinned_module:{rel}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _require_mapping(obj: Any, label: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise FailClosed(f"{label}_not_object")
    return obj


def _rank_market(probs: dict[str, float]) -> list[dict[str, Any]]:
    if not probs:
        raise FailClosed("empty_ticket_probability_market")
    rows: list[dict[str, Any]] = []
    for ticket, raw_q in probs.items():
        q = float(raw_q)
        if not math.isfinite(q) or q <= 0.0 or q > 1.0:
            raise FailClosed(f"invalid_ticket_probability:{ticket}")
        rows.append(
            {
                "ticket": str(ticket),
                "raw_b1a_pl_probability": q,
                "raw_break_even_decimal_odds": 1.0 / q,
                "raw_positive_ev_condition": "actual_decimal_odds > raw_break_even_decimal_odds",
                "exact_v54_executable": False,
            }
        )
    rows.sort(key=lambda r: (-r["raw_b1a_pl_probability"], r["ticket"]))
    for i, row in enumerate(rows, start=1):
        row["raw_probability_rank"] = i
    return rows


_ALLOWED_OUTCOME_CONTROL_PATHS = frozenset({
    "$.pre_freeze_receipt.winner_prediction",
    "$.pre_freeze_receipt.post_result_reconstruction",
})


def _reject_outcome_fields_scoped(
    obj: Any, forbidden_tokens: tuple[str, ...], path: str = "$"
) -> None:
    """Reject outcome/settlement fields while allowing exact PRE receipt control keys."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}"
            lowered = str(key).lower()
            if child not in _ALLOWED_OUTCOME_CONTROL_PATHS and any(
                str(token).lower() in lowered for token in forbidden_tokens
            ):
                raise FailClosed(f"outcome_or_settlement_field_forbidden:{child}")
            _reject_outcome_fields_scoped(value, forbidden_tokens, child)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            _reject_outcome_fields_scoped(value, forbidden_tokens, f"{path}[{i}]")


def run(envelope: dict[str, Any], repo_root: Path, top_n: int = 10) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise FailClosed("input_envelope_not_object")
    if top_n <= 0:
        raise FailClosed("top_n_must_be_positive")

    # Reject outcome/settlement contamination while allowing the two exact PRE
    # receipt control-field names that intentionally contain forbidden substrings.
    v1 = _load_pinned(repo_root, V1_REL, V1_GIT_BLOB, "keirin_v54_v1_for_pre_only_required_odds")
    _reject_outcome_fields_scoped(envelope, tuple(v1.FORBIDDEN_TOKENS))
    score_mod = _load_pinned(
        repo_root,
        SCORE_PRODUCER_REL,
        SCORE_PRODUCER_GIT_BLOB,
        "keirin_gate_score_for_pre_only_required_odds",
    )

    pre_receipt = _require_mapping(envelope.get("pre_freeze_receipt"), "pre_freeze_receipt")
    if pre_receipt.get("record") != "KEIRIN_PROSPECTIVE_PRE_FREEZE_RECEIPT_v1":
        raise FailClosed("pre_freeze_receipt_record_mismatch")
    if pre_receipt.get("status") != "PASS_PRE_FROZEN_BEFORE_OUTCOME":
        raise FailClosed("pre_freeze_receipt_not_pass")
    if pre_receipt.get("outcome_accessed") is not False:
        raise FailClosed("pre_freeze_receipt_outcome_flag_invalid")
    if pre_receipt.get("post_result_reconstruction") is not False:
        raise FailClosed("pre_freeze_receipt_reconstruction_flag_invalid")

    target_identity = _require_mapping(pre_receipt.get("target_identity"), "target_identity")
    capture_time = v1.parse_time(pre_receipt.get("capture_time"), "pre.capture_time")
    cutoff = v1.parse_time(pre_receipt.get("target_cutoff"), "pre.target_cutoff")
    if capture_time > cutoff:
        raise FailClosed("pre_capture_after_cutoff")

    pre_payload = _require_mapping(envelope.get("pre_payload_for_gate_score"), "pre_payload_for_gate_score")
    expected_pre_sha = str(pre_receipt.get("pre_payload_sha256", "")).strip().lower()
    if len(expected_pre_sha) != 64:
        raise FailClosed("pre_payload_sha256_missing")
    observed_pre_sha = v1.sha256_bytes(v1.canonical_bytes(pre_payload))
    if observed_pre_sha != expected_pre_sha:
        raise FailClosed("pre_payload_sha256_mismatch")
    if v1.identity_tuple(pre_payload) != v1.identity_tuple(target_identity):
        raise FailClosed("pre_payload_target_identity_mismatch")

    winner = _require_mapping(pre_receipt.get("winner_prediction"), "winner_prediction")
    if (
        str(winner.get("event_date")),
        str(winner.get("venue", "")).strip(),
        int(winner.get("race_number", -1)),
    ) != v1.identity_tuple(target_identity):
        raise FailClosed("winner_prediction_identity_mismatch")

    model = score_mod.load_frozen_model(repo_root)
    generated_gate = score_mod.produce_gate_score(pre_payload, model)
    gate_value = float(generated_gate["value"])
    if not math.isfinite(gate_value):
        raise FailClosed("generated_competition_gate_nonfinite")

    ticket_probs = _require_mapping(v1.build_frozen_ticket_probabilities(winner), "ticket_probabilities")
    markets: dict[str, Any] = {}
    gate_pass = gate_value >= COMPETITION_THRESHOLD
    for market in SUPPORTED_MARKETS:
        probs = _require_mapping(ticket_probs.get(market), f"ticket_probabilities.{market}")
        ranked = _rank_market(probs)
        markets[market] = {
            "ticket_count": len(ranked),
            "prediction_only_candidate": ranked[0] if gate_pass else None,
            "top_ranked_raw_candidates": ranked[:top_n] if gate_pass else [],
        }

    out = {
        "record": "KEIRIN_PRE_ONLY_REQUIRED_ODDS_RECEIPT_v1",
        "status": "PASS_PRE_ONLY_CANDIDATES" if gate_pass else "PASS_PRE_ONLY_GATE_NO_CANDIDATE",
        "target_identity": dict(target_identity),
        "capture_time": str(pre_receipt.get("capture_time")),
        "target_cutoff": str(pre_receipt.get("target_cutoff")),
        "pre_payload_sha256": observed_pre_sha,
        "competition_gate": {
            "value": gate_value,
            "threshold": COMPETITION_THRESHOLD,
            "pass": gate_pass,
            "semantic_name": generated_gate.get("semantic_name"),
            "top1_agreement": generated_gate.get("top1_agreement"),
            "score_producer_git_blob": SCORE_PRODUCER_GIT_BLOB,
        },
        "ticket_probability_source": {
            "method": "frozen_v54_v1_build_frozen_ticket_probabilities",
            "v1_runner_git_blob": V1_GIT_BLOB,
            "markets": list(SUPPORTED_MARKETS),
        },
        "markets": markets,
        "required_odds_semantics": {
            "formula": "raw_break_even_decimal_odds = 1 / raw_b1a_pl_probability",
            "positive_raw_model_ev": "actual_decimal_odds > raw_break_even_decimal_odds",
            "warning": "NOT_EXACT_V54_EXECUTABLE_UNTIL_GENUINE_PRE_CLOSE_MARKET_CHECKS; MKT50/shape-edge/raw-EV ranking/staking are intentionally absent",
        },
        "exact_v54_executable": False,
        "result_accessed": False,
        "payout_accessed": False,
        "network_access": False,
        "runtime": "OFF",
        "automatic_betting": False,
        "retune": False,
    }
    out["receipt_sha256"] = v1.sha256_bytes(v1.canonical_bytes(out))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output", required=True)
    ap.add_argument("--top-n", type=int, default=10)
    a = ap.parse_args()

    out_path = Path(a.output)
    if out_path.exists():
        raise FailClosed("output_already_exists")
    envelope = json.loads(Path(a.input).read_text(encoding="utf-8"))
    rec = run(envelope, Path(a.repo_root).resolve(), top_n=a.top_n)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
