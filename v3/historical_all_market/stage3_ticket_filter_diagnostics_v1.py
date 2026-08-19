#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — Stage 3 ticket filter diagnostics v1.

Consumes Stage-2 PRICE/EV catalog only and applies the preregistered candidate
filter family. No RESULT/PAYOUT/Settlement/realized ROI is read or computed.

Outputs are diagnostics (candidate density / NO-BET counts), not a promoted
wagering policy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPECTED_STAGE2_SHA256 = "34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_STAGE3_PREREG_GIT_BLOB = "ba4175bb044bcacfa66a7b8d089e92c04762b2e6"
EXPECTED_INPUT_ROWS = 4000
EXPECTED_RACES = 2000
MODELS = ("candidate_a", "b1a_reconstituted_v1")
MARKETS = ("3rentan", "3renhuku", "2shatan", "2shahuku", "wide", "2wakutan", "2wakuhuku")

PROFILES = (
    ("P00", 0.00, 1.00),
    ("P05", 0.05, 1.05),
    ("P10", 0.10, 1.10),
    ("P20", 0.20, 1.20),
    ("P35", 0.35, 1.35),
    ("P50", 0.50, 1.50),
    ("P100", 1.00, 2.00),
)


class FailClosed(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_number(x: Any, label: str) -> float:
    try:
        v = float(x)
    except Exception as e:
        raise FailClosed(f"{label}: non-numeric value={x!r}") from e
    if not math.isfinite(v):
        raise FailClosed(f"{label}: non-finite value={v}")
    return v


def quantile_sorted(xs: list[int], q: float) -> float:
    if not xs:
        raise FailClosed("quantile requested for empty list")
    if not 0 <= q <= 1:
        raise ValueError(q)
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(xs[lo])
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage2_jsonl")
    ap.add_argument("race_counts_csv")
    ap.add_argument("quality_json")
    args = ap.parse_args()

    stage2 = Path(args.stage2_jsonl)
    race_csv = Path(args.race_counts_csv)
    quality_path = Path(args.quality_json)

    observed_sha = sha256_file(stage2)
    if observed_sha != EXPECTED_STAGE2_SHA256:
        raise FailClosed(
            f"Stage2 catalog SHA mismatch expected={EXPECTED_STAGE2_SHA256} observed={observed_sha}"
        )

    race_csv.parent.mkdir(parents=True, exist_ok=True)
    quality_path.parent.mkdir(parents=True, exist_ok=True)

    seen_keys: set[tuple[str, str]] = set()
    race_ids: set[str] = set()
    input_rows = 0
    market_model_races = Counter()
    total_ticket_counts = Counter()
    candidate_totals = Counter()
    no_bet_counts = Counter()
    per_race_candidate_counts: dict[str, list[int]] = defaultdict(list)
    per_race_ticket_counts: dict[str, list[int]] = defaultdict(list)
    monotonicity_violations = 0

    fieldnames = [
        "race_id", "probability_source", "market", "profile_id",
        "total_ticket_count", "candidate_count", "candidate_share", "no_bet",
    ]

    with stage2.open("r", encoding="utf-8") as src, race_csv.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception as e:
                raise FailClosed(f"Stage2 JSON parse error line={line_no}: {e}") from e
            if not isinstance(row, dict):
                raise FailClosed(f"Stage2 non-object row line={line_no}")

            input_rows += 1
            rid = str(row.get("race_id", "")).strip()
            model = str(row.get("probability_source", "")).strip()
            if not rid or model not in MODELS:
                raise FailClosed(f"invalid race/model line={line_no} race_id={rid!r} model={model!r}")
            key = (rid, model)
            if key in seen_keys:
                raise FailClosed(f"duplicate Stage2 race/model key={key}")
            seen_keys.add(key)
            race_ids.add(rid)

            if row.get("result_fields_included") is not False:
                raise FailClosed(f"{rid}/{model}: Stage2 result firewall flag is not false")
            if row.get("settlement_fields_included") is not False:
                raise FailClosed(f"{rid}/{model}: Stage2 settlement firewall flag is not false")
            if row.get("realized_roi_computed") is not False:
                raise FailClosed(f"{rid}/{model}: Stage2 realized ROI flag is not false")
            if row.get("threshold_selected") is not False:
                raise FailClosed(f"{rid}/{model}: Stage2 threshold_selected is not false")
            if row.get("portfolio_constructed") is not False:
                raise FailClosed(f"{rid}/{model}: Stage2 portfolio_constructed is not false")
            if row.get("wide_primary_price_rule") != "LOW":
                raise FailClosed(f"{rid}/{model}: Wide primary price rule drift")

            sold = list(row.get("sold_markets", []))
            if len(sold) != len(set(sold)) or not set(sold).issubset(MARKETS):
                raise FailClosed(f"{rid}/{model}: invalid sold_markets={sold}")
            metrics = row.get("ticket_price_probability_metrics")
            if not isinstance(metrics, dict) or set(metrics) != set(sold):
                raise FailClosed(f"{rid}/{model}: metric market keys != sold markets")

            for market in sold:
                tickets = metrics[market]
                if not isinstance(tickets, dict) or not tickets:
                    raise FailClosed(f"{rid}/{model}/{market}: empty/non-object ticket metrics")
                total = len(tickets)
                market_model_races[f"{model}:{market}"] += 1
                total_ticket_counts[f"{model}:{market}"] += total

                pass_counts = {pid: 0 for pid, _, _ in PROFILES}
                for ticket_key, tm in tickets.items():
                    if not isinstance(tm, dict):
                        raise FailClosed(f"{rid}/{model}/{market}/{ticket_key}: metric is non-object")
                    ev = finite_number(tm.get("raw_ev_primary"), f"{rid}/{model}/{market}/{ticket_key}/raw_ev_primary")
                    ratio = finite_number(tm.get("shape_edge_ratio_primary"), f"{rid}/{model}/{market}/{ticket_key}/shape_edge_ratio_primary")
                    if ratio < 0:
                        raise FailClosed(f"{rid}/{model}/{market}/{ticket_key}: negative shape-edge ratio={ratio}")
                    prior_pass = True
                    for pid, ev_min, ratio_min in PROFILES:
                        passed = ev >= ev_min and ratio >= ratio_min
                        if passed:
                            pass_counts[pid] += 1
                        # Profiles are ordered weak -> strong. A strong profile may never pass if the prior weaker one failed.
                        if passed and not prior_pass:
                            monotonicity_violations += 1
                        prior_pass = prior_pass and passed

                prior_count = total + 1
                for pid, _, _ in PROFILES:
                    c = pass_counts[pid]
                    if c > prior_count:
                        monotonicity_violations += 1
                    prior_count = c
                    agg = f"{model}:{market}:{pid}"
                    candidate_totals[agg] += c
                    if c == 0:
                        no_bet_counts[agg] += 1
                    per_race_candidate_counts[agg].append(c)
                    per_race_ticket_counts[agg].append(total)
                    writer.writerow({
                        "race_id": rid,
                        "probability_source": model,
                        "market": market,
                        "profile_id": pid,
                        "total_ticket_count": total,
                        "candidate_count": c,
                        "candidate_share": f"{c/total:.12g}",
                        "no_bet": 1 if c == 0 else 0,
                    })

            if input_rows % 250 == 0:
                print(f"[STAGE3] rows={input_rows}/{EXPECTED_INPUT_ROWS} races={len(race_ids)}", flush=True)

    if input_rows != EXPECTED_INPUT_ROWS:
        raise FailClosed(f"Stage2 input rows={input_rows} expected={EXPECTED_INPUT_ROWS}")
    if len(seen_keys) != EXPECTED_INPUT_ROWS:
        raise FailClosed(f"unique race/model keys={len(seen_keys)} expected={EXPECTED_INPUT_ROWS}")
    if len(race_ids) != EXPECTED_RACES:
        raise FailClosed(f"unique races={len(race_ids)} expected={EXPECTED_RACES}")
    if monotonicity_violations:
        raise FailClosed(f"profile monotonicity violations={monotonicity_violations}")

    # Ensure the expected market coverage from Stage 2 is preserved.
    for model in MODELS:
        for market in MARKETS:
            n = market_model_races[f"{model}:{market}"]
            expected = 211 if market in {"2wakutan", "2wakuhuku"} else EXPECTED_RACES
            if n != expected:
                raise FailClosed(f"market coverage drift {model}/{market}: observed={n} expected={expected}")

    summary: dict[str, Any] = {}
    for model in MODELS:
        for market in MARKETS:
            race_count = market_model_races[f"{model}:{market}"]
            total_tickets = total_ticket_counts[f"{model}:{market}"]
            for pid, ev_min, ratio_min in PROFILES:
                agg = f"{model}:{market}:{pid}"
                counts = sorted(per_race_candidate_counts[agg])
                if len(counts) != race_count:
                    raise FailClosed(f"race-count list mismatch {agg}: {len(counts)} != {race_count}")
                candidates = candidate_totals[agg]
                no_bet = no_bet_counts[agg]
                summary[agg] = {
                    "probability_source": model,
                    "market": market,
                    "profile_id": pid,
                    "ev_min": ev_min,
                    "shape_edge_ratio_min": ratio_min,
                    "race_count": race_count,
                    "total_ticket_count": total_tickets,
                    "candidate_ticket_count": candidates,
                    "candidate_ticket_share": candidates / total_tickets if total_tickets else None,
                    "no_bet_race_count": no_bet,
                    "no_bet_race_share": no_bet / race_count if race_count else None,
                    "candidate_count_per_race": {
                        "min": counts[0],
                        "p25": quantile_sorted(counts, 0.25),
                        "median": quantile_sorted(counts, 0.50),
                        "p75": quantile_sorted(counts, 0.75),
                        "p90": quantile_sorted(counts, 0.90),
                        "p95": quantile_sorted(counts, 0.95),
                        "p99": quantile_sorted(counts, 0.99),
                        "max": counts[-1],
                        "mean": candidates / race_count,
                    },
                }

    quality = {
        "record": "STAGE3_TICKET_FILTER_DIAGNOSTICS_QUALITY_v1",
        "status": "PASS",
        "stage2_catalog_sha256": observed_sha,
        "stage3_prereg_git_blob": EXPECTED_STAGE3_PREREG_GIT_BLOB,
        "input_rows": input_rows,
        "unique_races": len(race_ids),
        "probability_sources": list(MODELS),
        "markets": list(MARKETS),
        "profiles": [
            {"profile_id": pid, "ev_min": ev_min, "shape_edge_ratio_min": ratio_min}
            for pid, ev_min, ratio_min in PROFILES
        ],
        "profile_selection_performed": False,
        "market_specific_threshold_tuning_performed": False,
        "ticket_level_candidate_catalog_persisted": False,
        "diagnostics": summary,
        "profile_monotonicity_violations": monotonicity_violations,
        "result_access": False,
        "payout_access": False,
        "settlement_access": False,
        "realized_roi_computed": False,
        "stage4_started": False,
        "stage5_started": False,
        "stage6_started": False,
        "scientific_trial_count": 0,
        "ECON_HOLDOUT1000": "SEALED",
    }
    quality["race_counts_csv_sha256"] = sha256_file(race_csv)
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": quality["status"],
        "input_rows": input_rows,
        "unique_races": len(race_ids),
        "race_counts_csv_sha256": quality["race_counts_csv_sha256"],
        "quality_path": str(quality_path),
        "settlement_access": False,
        "scientific_trial_count": 0,
        "ECON_HOLDOUT1000": "SEALED",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
