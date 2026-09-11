#!/usr/bin/env python3
"""Prospective v54 one-shot decision freeze runner (fail closed).

This adapter is PRE-only. It:
- consumes an immutable B1A PRE freeze receipt;
- derives exact Plackett-Luce 2shatan / 3rentan ticket probabilities;
- binds genuine pre-cutoff decimal-odds snapshots by saved-file SHA256;
- applies the exact frozen B1a_MKT50_v1 0.50/0.50 transform;
- applies the exact frozen SINGLE selector / FK10_R2 stake semantics;
- emits an immutable selected-ticket (or preregistered no-bet) ledger.

The frozen outcome-time validator is deliberately NOT executed here because
result/payout data do not exist at PRE freeze time. Its exact git blob is pinned
for post-outcome evaluation.

No fitting, tuning, network access, result access, payout access, or overwrite.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
from typing import Any, Mapping

MKT50_GIT_BLOB = "6fb09aaba113cd1b4a8d9f4b0b68e5beaff18fff"
FINAL_SELECTOR_GIT_BLOB = "34c4ae08bfd21240bdfec63de9427e1b5d277d6f"
POST_OUTCOME_VALIDATOR_GIT_BLOB = "bbdcef51ce1d216fbda9e1bdf042ed9ef397876f"
STAGE1_PL_ENGINE_GIT_BLOB = "029904b359e8151263c6a9bf8c4635f026941b0b"

POOL_WEIGHT_MODEL = 0.50
POOL_WEIGHT_MARKET = 0.50
EPS = 1e-15
COMPETITION_THRESHOLD = 0.40
SUPPORTED_MARKETS = ("3rentan", "2shatan")
TICKET_TEMPLATE = "SINGLE"
STAKE_POLICY = "FK10_R2"
KELLY_MULT = 0.10
TICKET_CAP = 0.0025
RACE_CAP = 0.02
STAKE_UNIT = 100

FORBIDDEN_TOKENS = (
    "result", "payout", "refund", "finish", "winner",
    "着順", "払戻", "確定",
)
REQUIRED_FROZEN_BINDINGS = {
    "b1a_mkt50_transform_git_blob": MKT50_GIT_BLOB,
    "final_selector_git_blob": FINAL_SELECTOR_GIT_BLOB,
    "validator_git_blob": POST_OUTCOME_VALIDATOR_GIT_BLOB,
    "pool_weight": 0.50,
    "competition_score_threshold": 0.40,
    "ticket_template": "SINGLE",
    "stake_policy": "FK10_R2",
}


class FailClosed(ValueError):
    pass


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_time(raw: Any, label: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception as exc:
        raise FailClosed(f"{label}:invalid_timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise FailClosed(f"{label}:timezone_required")
    return dt


def reject_outcome_fields(obj: Any, path: str = "$") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            low = str(k).lower()
            if any(token.lower() in low for token in FORBIDDEN_TOKENS):
                raise FailClosed(f"outcome_or_settlement_field_forbidden:{path}.{k}")
            reject_outcome_fields(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            reject_outcome_fields(v, f"{path}[{i}]")


def identity_tuple(obj: Mapping[str, Any]) -> tuple[str, str, int]:
    try:
        return (
            str(obj["event_date"]),
            str(obj["venue"]).strip(),
            int(obj["race_number"]),
        )
    except Exception as exc:
        raise FailClosed("target_identity_missing_or_invalid") from exc


def validate_frozen_bindings(bindings: Mapping[str, Any]) -> None:
    if not isinstance(bindings, Mapping):
        raise FailClosed("frozen_v54_missing")
    for k, expected in REQUIRED_FROZEN_BINDINGS.items():
        if k not in bindings:
            raise FailClosed(f"frozen_v54_missing:{k}")
        actual = bindings[k]
        if isinstance(expected, float):
            try:
                if float(actual) != expected:
                    raise FailClosed(f"frozen_v54_mismatch:{k}")
            except (TypeError, ValueError) as exc:
                raise FailClosed(f"frozen_v54_mismatch:{k}") from exc
        elif actual != expected:
            raise FailClosed(f"frozen_v54_mismatch:{k}")


def norm_text(x: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", x)).lower()


def event_date_tokens(value: str) -> set[str]:
    try:
        d = date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise FailClosed("target_event_date_invalid") from exc
    y, m, day = d.year, d.month, d.day
    return {
        f"{y:04d}-{m:02d}-{day:02d}",
        f"{y:04d}/{m:02d}/{day:02d}",
        f"{y:04d}.{m:02d}.{day:02d}",
        f"{y:04d}年{m:02d}月{day:02d}日",
        f"{y:04d}年{m}月{day}日",
    }


def race_tokens(n: int) -> set[str]:
    return {
        f"{n}R", f"第{n}R", f"第{n}レース", f"{n}レース",
        f"R{n}", f"race{n}", f"race#{n}",
    }


def verify_snapshot_identity(path: Path, identity: Mapping[str, Any], label: str) -> dict[str, bool]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FailClosed(f"{label}:trusted_snapshot_not_utf8") from exc
    event_date, venue, race_number = identity_tuple(identity)
    body = norm_text(text)
    flags = {
        "event_date": any(norm_text(t) in body for t in event_date_tokens(event_date)),
        "venue": norm_text(venue) in body,
        "race_number": any(norm_text(t) in body for t in race_tokens(race_number)),
    }
    if not all(flags.values()):
        missing = ",".join(k for k, v in flags.items() if not v)
        raise FailClosed(f"{label}:snapshot_target_identity_mismatch:{missing}")
    return flags


def validate_saved_receipt(
    receipt: Mapping[str, Any],
    repo_root: Path,
    capture_time: datetime,
    cutoff: datetime,
    label: str,
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise FailClosed(f"{label}:receipt_not_mapping")
    try:
        http_status = int(receipt["http_status"])
        retrieved = parse_time(receipt["retrieved_at"], f"{label}.retrieved_at")
        snapshot_path = str(receipt["snapshot_path"])
        expected_sha = str(receipt["content_sha256"]).lower()
    except KeyError as exc:
        raise FailClosed(f"{label}:receipt_missing:{exc.args[0]}") from exc

    if http_status != 200:
        raise FailClosed(f"{label}:http_status_not_200")
    if retrieved > capture_time or retrieved > cutoff:
        raise FailClosed(f"{label}:receipt_after_capture_or_cutoff")

    p = Path(snapshot_path)
    if p.is_absolute() or ".." in p.parts:
        raise FailClosed(f"{label}:unsafe_snapshot_path")
    full = (repo_root / p).resolve()
    root = repo_root.resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise FailClosed(f"{label}:snapshot_escapes_repo_root") from exc
    if not full.is_file():
        raise FailClosed(f"{label}:snapshot_missing")
    actual_sha = sha256_file(full)
    if actual_sha != expected_sha:
        raise FailClosed(f"{label}:snapshot_sha256_mismatch")
    identity_flags = verify_snapshot_identity(full, target_identity, label)

    return {
        "source_id": receipt.get("source_id"),
        "source_locator": receipt.get("source_locator"),
        "trust_class": str(receipt.get("trust_class", "")).upper(),
        "retrieved_at": str(receipt["retrieved_at"]),
        "http_status": http_status,
        "snapshot_path": snapshot_path,
        "content_sha256": actual_sha,
        "target_identity_match": identity_flags,
    }


def exact_order_probs(cars: list[int], p: Mapping[int, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for i in cars:
        d2 = 1.0 - p[i]
        if d2 <= 0:
            raise FailClosed("invalid_PL_denominator_after_first")
        for j in cars:
            if j == i:
                continue
            d3 = 1.0 - p[i] - p[j]
            if d3 <= 0:
                raise FailClosed("invalid_PL_denominator_after_second")
            for k in cars:
                if k == i or k == j:
                    continue
                out[f"{i}-{j}-{k}"] = p[i] * (p[j] / d2) * (p[k] / d3)
    return out


def build_frozen_ticket_probabilities(
    winner_prediction: Mapping[str, Any],
) -> dict[str, dict[str, float]]:
    rows = winner_prediction.get("probabilities")
    if not isinstance(rows, list) or len(rows) < 2:
        raise FailClosed("winner_probabilities_invalid")
    p: dict[int, float] = {}
    for row in rows:
        try:
            car = int(row["car_no"])
            v = float(row["b1a_reconstituted_v1_win_prob"])
        except Exception as exc:
            raise FailClosed("winner_probability_row_invalid") from exc
        if car <= 0 or car in p or not math.isfinite(v) or v <= 0:
            raise FailClosed("winner_probability_invalid")
        p[car] = v
    if abs(sum(p.values()) - 1.0) > 1e-10:
        raise FailClosed("winner_probability_sum_invalid")
    cars = sorted(p)
    pair: dict[str, float] = {}
    for i in cars:
        d = 1.0 - p[i]
        if d <= 0:
            raise FailClosed("invalid_pair_denominator")
        for j in cars:
            if i != j:
                pair[f"{i}-{j}"] = p[i] * p[j] / d
    triple = exact_order_probs(cars, p)
    for market, cat in (("2shatan", pair), ("3rentan", triple)):
        if any(not math.isfinite(v) or v <= 0 for v in cat.values()):
            raise FailClosed(f"{market}:ticket_probability_invalid")
        if abs(sum(cat.values()) - 1.0) > 1e-10:
            raise FailClosed(f"{market}:ticket_probability_sum_invalid")
    return {"3rentan": triple, "2shatan": pair}


def clean_distribution(d: Mapping[str, Any], label: str) -> dict[str, float]:
    if not isinstance(d, Mapping) or not d:
        raise FailClosed(f"{label}:empty_distribution")
    out: dict[str, float] = {}
    for k, raw in d.items():
        try:
            v = float(raw)
        except Exception as exc:
            raise FailClosed(f"{label}/{k}:non_numeric") from exc
        if not math.isfinite(v) or v < 0:
            raise FailClosed(f"{label}/{k}:invalid_probability")
        out[str(k)] = v
    total = sum(out.values())
    if not math.isfinite(total) or total <= 0:
        raise FailClosed(f"{label}:invalid_total")
    return {k: v / total for k, v in out.items()}


def market_shape_from_decimal_odds(odds: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(odds, Mapping) or not odds:
        raise FailClosed("odds:empty_distribution")
    inv: dict[str, float] = {}
    for k, raw in odds.items():
        try:
            v = float(raw)
        except Exception as exc:
            raise FailClosed(f"odds/{k}:non_numeric") from exc
        if not math.isfinite(v) or v <= 1.0:
            raise FailClosed(f"odds/{k}:decimal_odds_must_be_gt_1")
        inv[str(k)] = 1.0 / v
    z = sum(inv.values())
    if not math.isfinite(z) or z <= 0:
        raise FailClosed("odds:invalid_inverse_total")
    return {k: v / z for k, v in inv.items()}


def mkt50_transform(
    model_probability: Mapping[str, Any],
    market_shape_probability: Mapping[str, Any],
) -> dict[str, float]:
    pm = clean_distribution(model_probability, "model")
    pq = clean_distribution(market_shape_probability, "market")
    if set(pm) != set(pq):
        raise FailClosed("ticket_universe_mismatch")
    raw = {
        k: math.sqrt(max(pm[k], EPS) * max(pq[k], EPS))
        for k in pm
    }
    z = sum(raw.values())
    if not math.isfinite(z) or z <= 0:
        raise FailClosed("pooled_normalization_invalid")
    out = {k: v / z for k, v in raw.items()}
    if abs(sum(out.values()) - 1.0) > 1e-12:
        raise FailClosed("pooled_probability_sum_invalid")
    return out


def validate_competition_score(
    block: Mapping[str, Any],
    target_identity: Mapping[str, Any],
    cutoff: datetime,
) -> tuple[float, dict[str, Any]]:
    if not isinstance(block, Mapping):
        raise FailClosed("competition_score_missing")
    required = (
        "value", "captured_at", "frozen_before_target_cutoff",
        "provenance", "method_binding",
    )
    missing = [k for k in required if k not in block]
    if missing:
        raise FailClosed("competition_score_missing:" + ",".join(missing))
    try:
        score = float(block["value"])
    except Exception as exc:
        raise FailClosed("competition_score_non_numeric") from exc
    if not math.isfinite(score):
        raise FailClosed("competition_score_nonfinite")
    captured = parse_time(block["captured_at"], "competition_score.captured_at")
    if captured > cutoff or block["frozen_before_target_cutoff"] is not True:
        raise FailClosed("competition_score_not_frozen_before_cutoff")
    prov = block["provenance"]
    if not isinstance(prov, Mapping) or not prov:
        raise FailClosed("competition_score_provenance_missing")
    if "target_identity" in prov and identity_tuple(prov["target_identity"]) != identity_tuple(target_identity):
        raise FailClosed("competition_score_identity_mismatch")
    method_binding = str(block["method_binding"]).strip()
    if not method_binding:
        raise FailClosed("competition_score_method_binding_missing")
    return score, {
        "value": score,
        "captured_at": str(block["captured_at"]),
        "frozen_before_target_cutoff": True,
        "provenance": prov,
        "method_binding": method_binding,
        "origin": "EXTERNAL_PRECOMPUTED_PROVENANCE_BOUND",
        "runner_recomputed_score": False,
    }


def select_single_exact(
    race_markets: Mapping[str, dict[str, Any]],
    competition_score: float,
    bankroll: int,
) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
    if not math.isfinite(competition_score):
        raise FailClosed("invalid_competition_score")
    if bankroll < 0:
        raise FailClosed("negative_bankroll")
    diagnostics: dict[str, dict[str, Any]] = {}
    if competition_score < COMPETITION_THRESHOLD or bankroll < STAKE_UNIT:
        return None, diagnostics

    pool: list[tuple[str, str, float, float, float, float]] = []
    for market in SUPPORTED_MARKETS:
        row = race_markets.get(market)
        if row is None:
            continue
        model = clean_distribution(
            row.get("b1a_ticket_probability") or {}, f"{market}.model"
        )
        raw_odds = row.get("decimal_odds") or {}
        odds: dict[str, float] = {}
        for k, raw in raw_odds.items():
            try:
                odds[str(k)] = float(raw)
            except Exception as exc:
                raise FailClosed(f"{market}.odds/{k}:non_numeric") from exc
        market_shape = market_shape_from_decimal_odds(odds)
        if set(model) != set(market_shape):
            raise FailClosed(f"{market}:ticket_universe_mismatch")
        q = mkt50_transform(model, market_shape)
        diagnostics[market] = {
            "model_probability": model,
            "market_shape_probability": market_shape,
            "mkt50_probability": q,
            "decimal_odds": odds,
        }
        for ticket, prob in q.items():
            o = odds[ticket]
            ev = o * prob - 1.0
            ratio = prob / market_shape[ticket]
            if ev >= 0.0 and ratio >= 1.0:
                pool.append((market, ticket, prob, ev, ratio, o))
    if not pool:
        return None, diagnostics

    pool.sort(key=lambda x: (-x[3], -x[4], -x[2], x[0], x[1]))
    market, ticket, prob, ev, ratio, o = pool[0]
    kelly = max(0.0, (o * prob - 1.0) / (o - 1.0)) if o > 1.0 else 0.0
    frac = min(TICKET_CAP, max(0.0, KELLY_MULT * kelly), RACE_CAP)
    stake = int(math.floor((bankroll * frac) / STAKE_UNIT + 1e-12)) * STAKE_UNIT
    if stake < STAKE_UNIT:
        return None, diagnostics
    if stake > bankroll:
        raise FailClosed("stake_exceeds_bankroll")
    return {
        "market": market,
        "ticket": ticket,
        "q": prob,
        "odds": o,
        "raw_ev": ev,
        "shape_edge_ratio": ratio,
        "stake_yen": stake,
        "kelly_fraction_raw": kelly,
        "stake_fraction_after_FK10_R2": frac,
    }, diagnostics


def run(envelope: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    pre = envelope.get("pre_freeze_receipt")
    if not isinstance(pre, Mapping):
        raise FailClosed("pre_freeze_receipt_missing")
    if pre.get("record") != "KEIRIN_PROSPECTIVE_PRE_FREEZE_RECEIPT_v1":
        raise FailClosed("pre_freeze_receipt_record_mismatch")
    if pre.get("status") != "PASS_PRE_FROZEN_BEFORE_OUTCOME":
        raise FailClosed("pre_freeze_receipt_not_pass")
    if pre.get("outcome_accessed") is not False or pre.get("post_result_reconstruction") is not False:
        raise FailClosed("pre_freeze_receipt_future_data_flag_invalid")

    target_identity = pre.get("target_identity")
    if not isinstance(target_identity, Mapping):
        raise FailClosed("pre_target_identity_missing")
    target_key = identity_tuple(target_identity)
    capture_time = parse_time(pre.get("capture_time"), "pre.capture_time")
    cutoff = parse_time(pre.get("target_cutoff"), "pre.target_cutoff")
    if capture_time > cutoff:
        raise FailClosed("pre_capture_after_cutoff")

    bindings = envelope.get("frozen_v54")
    validate_frozen_bindings(bindings)
    if pre.get("frozen_v54_exact_match") is not True:
        raise FailClosed("pre_frozen_v54_exact_match_not_true")

    winner = pre.get("winner_prediction")
    if not isinstance(winner, Mapping):
        raise FailClosed("winner_prediction_missing")
    if (
        str(winner.get("event_date")),
        str(winner.get("venue", "")).strip(),
        int(winner.get("race_number", -1)),
    ) != target_key:
        raise FailClosed("winner_prediction_identity_mismatch")
    ticket_model = build_frozen_ticket_probabilities(winner)

    market_capture = envelope.get("market_capture")
    if not isinstance(market_capture, Mapping):
        raise FailClosed("market_capture_missing")
    reject_outcome_fields(market_capture)
    if identity_tuple(market_capture.get("target_identity") or {}) != target_key:
        raise FailClosed("market_capture_identity_mismatch")
    market_time = parse_time(market_capture.get("capture_time"), "market_capture.capture_time")
    market_cutoff = parse_time(market_capture.get("target_cutoff"), "market_capture.target_cutoff")
    if market_cutoff != cutoff:
        raise FailClosed("market_capture_cutoff_mismatch")
    if market_time > cutoff:
        raise FailClosed("market_capture_after_cutoff")

    receipts = market_capture.get("source_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise FailClosed("market_source_receipts_missing")
    bound_receipts = [
        validate_saved_receipt(r, repo_root, market_time, cutoff, f"market_receipt[{i}]", target_identity)
        for i, r in enumerate(receipts)
    ]
    trusted = [
        r for r in bound_receipts
        if str(r.get("trust_class", "")).upper() in {"OFFICIAL", "PRIMARY"}
    ]
    if not trusted:
        raise FailClosed("market_trusted_source_receipt_missing")

    market_rows = market_capture.get("markets")
    if not isinstance(market_rows, Mapping) or not market_rows:
        raise FailClosed("market_odds_missing")
    unexpected = set(market_rows) - set(SUPPORTED_MARKETS)
    if unexpected:
        raise FailClosed("unsupported_market_present:" + ",".join(sorted(unexpected)))

    race_markets: dict[str, dict[str, Any]] = {}
    for market in SUPPORTED_MARKETS:
        if market not in market_rows:
            continue
        row = market_rows[market]
        if not isinstance(row, Mapping):
            raise FailClosed(f"{market}:market_row_invalid")
        odds = row.get("decimal_odds")
        if not isinstance(odds, Mapping) or not odds:
            raise FailClosed(f"{market}:decimal_odds_missing")
        expected_universe = set(ticket_model[market])
        actual_universe = {str(k) for k in odds}
        if actual_universe != expected_universe:
            raise FailClosed(f"{market}:ticket_universe_mismatch")
        market_shape_from_decimal_odds(odds)
        race_markets[market] = {
            "b1a_ticket_probability": ticket_model[market],
            "decimal_odds": {str(k): float(v) for k, v in odds.items()},
        }

    if not race_markets:
        raise FailClosed("no_supported_market_odds")

    score_block = envelope.get("competition_score")
    reject_outcome_fields(score_block)
    score, score_binding = validate_competition_score(
        score_block, target_identity, cutoff
    )
    try:
        bankroll = int(envelope["bankroll_yen"])
    except Exception as exc:
        raise FailClosed("bankroll_yen_missing_or_invalid") from exc
    if bankroll < 0:
        raise FailClosed("negative_bankroll")

    selected, diagnostics = select_single_exact(race_markets, score, bankroll)

    decision = "SELECTED_SINGLE" if selected is not None else "NO_BET_FROZEN_RULE"
    selected_ledger = None
    if selected is not None:
        md = diagnostics[selected["market"]]
        ticket = selected["ticket"]
        selected_ledger = {
            **selected,
            "model_ticket_probability": md["model_probability"][ticket],
            "market_shape_probability": md["market_shape_probability"][ticket],
            "mkt50_pooled_probability": md["mkt50_probability"][ticket],
            "competition_score": score,
            "competition_score_binding": score_binding,
            "ticket_template": TICKET_TEMPLATE,
            "stake_policy": STAKE_POLICY,
        }

    body: dict[str, Any] = {
        "record": "KEIRIN_PROSPECTIVE_V54_DECISION_FREEZE_RECEIPT_v1",
        "status": "PASS_DECISION_FROZEN_BEFORE_OUTCOME",
        "decision": decision,
        "target_event_id": str(pre.get("target_event_id")),
        "target_identity": dict(target_identity),
        "pre_capture_time": str(pre.get("capture_time")),
        "market_capture_time": str(market_capture.get("capture_time")),
        "target_cutoff": str(pre.get("target_cutoff")),
        "pre_freeze_receipt_sha256": str(pre.get("freeze_receipt_sha256")),
        "pre_payload_sha256": str(pre.get("pre_payload_sha256")),
        "market_source_receipts": bound_receipts,
        "market_capture_payload_sha256": sha256_bytes(canonical_bytes(market_capture)),
        "frozen_v54": dict(bindings),
        "stage1_pl_ticket_probability_engine_git_blob": STAGE1_PL_ENGINE_GIT_BLOB,
        "selected_ticket_ledger": selected_ledger,
        "competition_score_binding": score_binding,
        "bankroll_yen_at_decision": bankroll,
        "post_outcome_validator": {
            "git_blob": POST_OUTCOME_VALIDATOR_GIT_BLOB,
            "status": "NOT_RUN_PRE_OUTCOME_BY_DESIGN",
            "reason": "requires later result/payout evidence; PRE runner forbids those fields",
        },
        "structural_validation_status": "PASS_FAIL_CLOSED",
        "outcome_accessed": False,
        "payout_accessed": False,
        "post_cutoff_backfill": False,
        "post_result_reconstruction": False,
        "retune": False,
        "network_access": False,
        "runtime": "OFF",
        "automatic_betting": False,
        "scientific_trial_count": 0,
    }
    body["decision_freeze_receipt_sha256"] = sha256_bytes(canonical_bytes(body))
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    try:
        env = json.loads(Path(args.input).read_text(encoding="utf-8"))
        out = run(env, Path(args.repo_root))
        op = Path(args.output)
        if op.exists():
            raise FailClosed("output_already_exists")
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(
            json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps(
            {"status": "FAIL_CLOSED", "reason": str(exc)},
            ensure_ascii=False, sort_keys=True
        ))
        return 3
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
