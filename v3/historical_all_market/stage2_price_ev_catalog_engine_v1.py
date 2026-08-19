#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — All-Market Historical Economic Track
Stage-2 price / EV catalog engine v1.

Inputs:
- Stage-0 PRICE catalog (closing odds only)
- Stage-1 PL elementary-ticket probability catalog

Outputs:
- price/probability joins and preregistered raw-EV / market-shape diagnostics only

STRICTLY NO:
- RESULT / finishing order
- PAYOUT / refund / Settlement
- realized hit / realized return / ROI
- portfolio / bankroll
- HOLDOUT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPECTED_PRICE_SHA256 = "2ca98097f74e5282fdc9c91629083f39bef4dafb94a1fc4f7e510acadefc407b"
EXPECTED_PROB_SHA256 = "6348d9af2a535578cf454afca52ea2c944cb6c50cab87f6e6ffa75149880b526"
EXPECTED_RACES = 2000
EXPECTED_PROB_ROWS = 4000
POINT_MARKETS = {"3rentan", "3renhuku", "2shatan", "2shahuku", "2wakutan", "2wakuhuku"}
ALL_MARKETS = POINT_MARKETS | {"wide"}
MODELS = {"candidate_a", "b1a_reconstituted_v1"}
TOL = 1e-10


class FailClosed(RuntimeError):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                x = json.loads(line)
            except Exception as e:
                raise FailClosed(f"JSON parse error {path.name}:{ln}: {e}") from e
            if not isinstance(x, dict):
                raise FailClosed(f"non-object JSONL record {path.name}:{ln}")
            out.append(x)
    return out


def finite_pos(x: Any, label: str) -> float:
    try:
        v = float(x)
    except Exception as e:
        raise FailClosed(f"{label}: non-numeric={x!r}") from e
    if not math.isfinite(v) or v <= 0:
        raise FailClosed(f"{label}: expected finite positive value, got {v}")
    return v


def make_stats() -> dict[str, float | int]:
    return {
        "ticket_count": 0,
        "primary_ev_positive_count": 0,
        "primary_ev_sum": 0.0,
        "primary_ev_min": math.inf,
        "primary_ev_max": -math.inf,
        "shape_edge_delta_sum": 0.0,
        "shape_edge_delta_min": math.inf,
        "shape_edge_delta_max": -math.inf,
        "shape_edge_ratio_sum": 0.0,
        "shape_edge_ratio_min": math.inf,
        "shape_edge_ratio_max": -math.inf,
    }


def update_stats(s: dict[str, float | int], ev: float, edge_delta: float, edge_ratio: float) -> None:
    s["ticket_count"] = int(s["ticket_count"]) + 1
    if ev > 0:
        s["primary_ev_positive_count"] = int(s["primary_ev_positive_count"]) + 1
    s["primary_ev_sum"] = float(s["primary_ev_sum"]) + ev
    s["primary_ev_min"] = min(float(s["primary_ev_min"]), ev)
    s["primary_ev_max"] = max(float(s["primary_ev_max"]), ev)
    s["shape_edge_delta_sum"] = float(s["shape_edge_delta_sum"]) + edge_delta
    s["shape_edge_delta_min"] = min(float(s["shape_edge_delta_min"]), edge_delta)
    s["shape_edge_delta_max"] = max(float(s["shape_edge_delta_max"]), edge_delta)
    s["shape_edge_ratio_sum"] = float(s["shape_edge_ratio_sum"]) + edge_ratio
    s["shape_edge_ratio_min"] = min(float(s["shape_edge_ratio_min"]), edge_ratio)
    s["shape_edge_ratio_max"] = max(float(s["shape_edge_ratio_max"]), edge_ratio)


def finalize_stats(s: dict[str, float | int]) -> dict[str, float | int]:
    n = int(s["ticket_count"])
    if n <= 0:
        raise FailClosed("attempted to finalize empty statistics")
    return {
        "ticket_count": n,
        "primary_ev_positive_count": int(s["primary_ev_positive_count"]),
        "primary_ev_positive_share": int(s["primary_ev_positive_count"]) / n,
        "primary_ev_mean": float(s["primary_ev_sum"]) / n,
        "primary_ev_min": float(s["primary_ev_min"]),
        "primary_ev_max": float(s["primary_ev_max"]),
        "shape_edge_delta_mean": float(s["shape_edge_delta_sum"]) / n,
        "shape_edge_delta_min": float(s["shape_edge_delta_min"]),
        "shape_edge_delta_max": float(s["shape_edge_delta_max"]),
        "shape_edge_ratio_mean": float(s["shape_edge_ratio_sum"]) / n,
        "shape_edge_ratio_min": float(s["shape_edge_ratio_min"]),
        "shape_edge_ratio_max": float(s["shape_edge_ratio_max"]),
    }


def point_market_metrics(pcat: dict[str, Any], ocat: dict[str, Any], rid: str, model: str, market: str):
    if set(pcat) != set(ocat):
        miss = sorted(set(pcat) - set(ocat))[:5]
        extra = sorted(set(ocat) - set(pcat))[:5]
        raise FailClosed(f"{rid}/{model}/{market}: ticket join mismatch missing_price={miss} extra_price={extra}")

    probs = {k: finite_pos(v, f"{rid}/{model}/{market}/{k}/p") for k, v in pcat.items()}
    odds = {k: finite_pos(ocat[k], f"{rid}/{model}/{market}/{k}/odds") for k in pcat}
    p_sum = sum(probs.values())
    if abs(p_sum - 1.0) > TOL:
        raise FailClosed(f"{rid}/{model}/{market}: model probability sum={p_sum}, expected 1")
    q_raw = {k: 1.0 / odds[k] for k in probs}
    q_sum = sum(q_raw.values())
    if not math.isfinite(q_sum) or q_sum <= 0:
        raise FailClosed(f"{rid}/{model}/{market}: invalid market implied sum={q_sum}")

    cat = {}
    for k in sorted(probs):
        p = probs[k]
        model_shape = p / p_sum
        market_shape = q_raw[k] / q_sum
        ratio = model_shape / market_shape
        cat[k] = {
            "model_event_probability": p,
            "closing_odds": odds[k],
            "raw_ev_primary": p * odds[k] - 1.0,
            "raw_implied_probability": q_raw[k],
            "model_shape_probability": model_shape,
            "market_shape_probability_primary": market_shape,
            "shape_edge_delta_primary": model_shape - market_shape,
            "shape_edge_ratio_primary": ratio,
        }
    diag = {
        "model_probability_sum": p_sum,
        "market_implied_sum_primary": q_sum,
        "wide_price_surface": None,
    }
    return cat, diag


def wide_market_metrics(pcat: dict[str, Any], ocat: dict[str, Any], rid: str, model: str):
    market = "wide"
    if set(pcat) != set(ocat):
        miss = sorted(set(pcat) - set(ocat))[:5]
        extra = sorted(set(ocat) - set(pcat))[:5]
        raise FailClosed(f"{rid}/{model}/{market}: ticket join mismatch missing_price={miss} extra_price={extra}")

    probs = {k: finite_pos(v, f"{rid}/{model}/{market}/{k}/p") for k, v in pcat.items()}
    p_sum = sum(probs.values())
    if abs(p_sum - 3.0) > TOL:
        raise FailClosed(f"{rid}/{model}/wide: probability sum={p_sum}, expected 3")

    lows: dict[str, float] = {}
    highs: dict[str, float] = {}
    for k in probs:
        q = ocat[k]
        if not isinstance(q, dict) or set(q) != {"low", "high"}:
            raise FailClosed(f"{rid}/{model}/wide/{k}: expected exact low/high interval object")
        low = finite_pos(q["low"], f"{rid}/{model}/wide/{k}/low")
        high = finite_pos(q["high"], f"{rid}/{model}/wide/{k}/high")
        if high < low:
            raise FailClosed(f"{rid}/{model}/wide/{k}: high={high} < low={low}")
        lows[k] = low
        highs[k] = high

    q_low_raw = {k: 1.0 / lows[k] for k in probs}
    q_high_raw = {k: 1.0 / highs[k] for k in probs}
    q_low_sum = sum(q_low_raw.values())
    q_high_sum = sum(q_high_raw.values())
    if q_low_sum <= 0 or q_high_sum <= 0:
        raise FailClosed(f"{rid}/{model}/wide: invalid implied sums")

    cat = {}
    for k in sorted(probs):
        p = probs[k]
        model_shape = p / p_sum
        market_shape_low = q_low_raw[k] / q_low_sum
        market_shape_high = q_high_raw[k] / q_high_sum
        ratio_low = model_shape / market_shape_low
        ratio_high = model_shape / market_shape_high
        cat[k] = {
            "model_event_probability": p,
            "closing_odds_low": lows[k],
            "closing_odds_high": highs[k],
            "raw_ev_primary": p * lows[k] - 1.0,
            "raw_ev_high_diagnostic": p * highs[k] - 1.0,
            "raw_implied_probability_primary": q_low_raw[k],
            "raw_implied_probability_high_diagnostic": q_high_raw[k],
            "model_shape_probability": model_shape,
            "market_shape_probability_primary": market_shape_low,
            "market_shape_probability_high_diagnostic": market_shape_high,
            "shape_edge_delta_primary": model_shape - market_shape_low,
            "shape_edge_delta_high_diagnostic": model_shape - market_shape_high,
            "shape_edge_ratio_primary": ratio_low,
            "shape_edge_ratio_high_diagnostic": ratio_high,
        }
    diag = {
        "model_probability_sum": p_sum,
        "market_implied_sum_primary": q_low_sum,
        "market_implied_sum_high_diagnostic": q_high_sum,
        "wide_price_surface": "LOW_PRIMARY_HIGH_DIAGNOSTIC",
    }
    return cat, diag


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("price_jsonl")
    ap.add_argument("probability_jsonl")
    ap.add_argument("output_jsonl")
    ap.add_argument("quality_json")
    a = ap.parse_args()

    price_path = Path(a.price_jsonl)
    prob_path = Path(a.probability_jsonl)
    out_path = Path(a.output_jsonl)
    quality_path = Path(a.quality_json)

    price_sha = sha256_file(price_path)
    prob_sha = sha256_file(prob_path)
    if price_sha != EXPECTED_PRICE_SHA256:
        raise FailClosed(f"PRICE SHA mismatch expected={EXPECTED_PRICE_SHA256} observed={price_sha}")
    if prob_sha != EXPECTED_PROB_SHA256:
        raise FailClosed(f"probability SHA mismatch expected={EXPECTED_PROB_SHA256} observed={prob_sha}")

    price_rows = load_jsonl(price_path)
    if len(price_rows) != EXPECTED_RACES:
        raise FailClosed(f"PRICE race rows={len(price_rows)} expected={EXPECTED_RACES}")
    price_by: dict[str, dict[str, Any]] = {}
    for r in price_rows:
        rid = str(r.get("race_id", ""))
        if not rid or rid in price_by:
            raise FailClosed(f"PRICE duplicate/blank race_id={rid!r}")
        price_by[rid] = r

    stats = defaultdict(make_stats)
    market_race_counts = Counter()
    implied_sum_stats: dict[str, dict[str, float | int]] = defaultdict(lambda: {
        "race_count": 0,
        "primary_sum_total": 0.0,
        "primary_sum_min": math.inf,
        "primary_sum_max": -math.inf,
    })
    wide_high_implied = {"race_count": 0, "sum_total": 0.0, "sum_min": math.inf, "sum_max": -math.inf}
    seen_prob_keys: set[tuple[str, str]] = set()
    output_rows = 0
    ticket_join_mismatches = 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with prob_path.open("r", encoding="utf-8") as f, out_path.open("w", encoding="utf-8", newline="\n") as w:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            pr = json.loads(line)
            rid = str(pr.get("race_id", ""))
            model = str(pr.get("probability_source", ""))
            key = (rid, model)
            if not rid or model not in MODELS or key in seen_prob_keys:
                raise FailClosed(f"probability duplicate/invalid key line={ln} key={key}")
            seen_prob_keys.add(key)
            if rid not in price_by:
                raise FailClosed(f"{rid}/{model}: missing PRICE race")
            price = price_by[rid]
            sold_p = list(pr.get("sold_markets", []))
            sold_o = list(price.get("sold_markets", []))
            if set(sold_p) != set(sold_o):
                raise FailClosed(f"{rid}/{model}: sold-market mismatch probability={sold_p} price={sold_o}")
            if not set(sold_p).issubset(ALL_MARKETS):
                raise FailClosed(f"{rid}/{model}: unknown market={sorted(set(sold_p)-ALL_MARKETS)}")
            pcats = pr.get("ticket_probabilities", {})
            ocats = price.get("closing_price_catalogs", {})
            if set(pcats) != set(sold_p) or set(ocats) != set(sold_o):
                raise FailClosed(f"{rid}/{model}: market catalog keys do not match sold markets")

            metrics: dict[str, Any] = {}
            market_diags: dict[str, Any] = {}
            for market in sold_p:
                try:
                    if market == "wide":
                        cat, diag = wide_market_metrics(pcats[market], ocats[market], rid, model)
                    else:
                        cat, diag = point_market_metrics(pcats[market], ocats[market], rid, model, market)
                except FailClosed:
                    ticket_join_mismatches += 1
                    raise
                metrics[market] = cat
                market_diags[market] = diag
                market_race_counts[f"{model}:{market}"] += 1

                ds = implied_sum_stats[market]
                primary_sum = float(diag["market_implied_sum_primary"])
                ds["race_count"] = int(ds["race_count"]) + 1
                ds["primary_sum_total"] = float(ds["primary_sum_total"]) + primary_sum
                ds["primary_sum_min"] = min(float(ds["primary_sum_min"]), primary_sum)
                ds["primary_sum_max"] = max(float(ds["primary_sum_max"]), primary_sum)
                if market == "wide":
                    hs = float(diag["market_implied_sum_high_diagnostic"])
                    wide_high_implied["race_count"] = int(wide_high_implied["race_count"]) + 1
                    wide_high_implied["sum_total"] = float(wide_high_implied["sum_total"]) + hs
                    wide_high_implied["sum_min"] = min(float(wide_high_implied["sum_min"]), hs)
                    wide_high_implied["sum_max"] = max(float(wide_high_implied["sum_max"]), hs)

                s = stats[f"{model}:{market}"]
                for t in cat.values():
                    update_stats(s, float(t["raw_ev_primary"]), float(t["shape_edge_delta_primary"]), float(t["shape_edge_ratio_primary"]))

            rec = {
                "race_id": rid,
                "probability_source": model,
                "active_car_numbers": pr.get("active_car_numbers"),
                "sold_markets": sold_p,
                "ticket_price_probability_metrics": metrics,
                "market_diagnostics": market_diags,
                "wide_primary_price_rule": "LOW",
                "result_fields_included": False,
                "settlement_fields_included": False,
                "realized_roi_computed": False,
                "threshold_selected": False,
                "portfolio_constructed": False,
            }
            w.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            output_rows += 1

    if output_rows != EXPECTED_PROB_ROWS or len(seen_prob_keys) != EXPECTED_PROB_ROWS:
        raise FailClosed(f"Stage2 output cardinality rows={output_rows} keys={len(seen_prob_keys)} expected={EXPECTED_PROB_ROWS}")
    if {rid for rid, _ in seen_prob_keys} != set(price_by):
        raise FailClosed("Stage2 probability/PRICE race-set mismatch")

    finalized_stats = {k: finalize_stats(v) for k, v in sorted(stats.items())}
    implied_quality = {}
    # Each model repeats the same price surface, so divide market diagnostic race counts by number of models for race-level reporting.
    for market, ds in sorted(implied_sum_stats.items()):
        n_model_rows = int(ds["race_count"])
        if n_model_rows % len(MODELS) != 0:
            raise FailClosed(f"{market}: implied diagnostic model-row count not divisible by model count")
        n_races = n_model_rows // len(MODELS)
        implied_quality[market] = {
            "race_count": n_races,
            "market_implied_sum_primary_mean": float(ds["primary_sum_total"]) / n_model_rows,
            "market_implied_sum_primary_min": float(ds["primary_sum_min"]),
            "market_implied_sum_primary_max": float(ds["primary_sum_max"]),
        }
    if int(wide_high_implied["race_count"]) > 0:
        implied_quality["wide"]["market_implied_sum_high_diagnostic_mean"] = float(wide_high_implied["sum_total"]) / int(wide_high_implied["race_count"])
        implied_quality["wide"]["market_implied_sum_high_diagnostic_min"] = float(wide_high_implied["sum_min"])
        implied_quality["wide"]["market_implied_sum_high_diagnostic_max"] = float(wide_high_implied["sum_max"])

    quality = {
        "record": "STAGE2_PRICE_EV_CATALOG_QUALITY_v1",
        "status": "PASS",
        "price_sha256": price_sha,
        "ticket_probability_sha256": prob_sha,
        "output_sha256": sha256_file(out_path),
        "races": EXPECTED_RACES,
        "probability_rows": EXPECTED_PROB_ROWS,
        "output_rows": output_rows,
        "probability_sources": sorted(MODELS),
        "model_market_race_counts": dict(sorted(market_race_counts.items())),
        "ticket_join_mismatches": ticket_join_mismatches,
        "descriptive_ticket_metrics": finalized_stats,
        "market_price_diagnostics": implied_quality,
        "wide_primary_price_rule": "LOW",
        "wide_high_price_role": "DIAGNOSTIC_ONLY",
        "result_access": False,
        "settlement_access": False,
        "realized_roi_computed": False,
        "threshold_selected": False,
        "portfolio_constructed": False,
        "scientific_trial_count": 0,
        "ECON_HOLDOUT1000": "SEALED",
    }
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
