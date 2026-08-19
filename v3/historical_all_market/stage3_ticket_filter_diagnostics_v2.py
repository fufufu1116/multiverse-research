#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — Stage 3 ticket filter diagnostics v2.

Runtime-resilient implementation of the already preregistered Stage 3 v1
semantics. Scientific rules are unchanged.

Key engineering changes from v1:
- compact one-record-per-race/model diagnostics;
- 250-record resumable chunks;
- atomic local-temp -> Drive chunk publication;
- completed valid chunks are reused;
- final quality is rebuilt from chunks without rescanning Stage 2.

NO RESULT / PAYOUT / Settlement / realized ROI / HOLDOUT access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_STAGE2_SHA256 = "34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_STAGE3_PREREG_GIT_BLOB = "ba4175bb044bcacfa66a7b8d089e92c04762b2e6"
EXPECTED_INPUT_ROWS = 4000
EXPECTED_RACES = 2000
CHUNK_SIZE = 250
EXPECTED_CHUNKS = 16
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
PROFILE_IDS = tuple(p[0] for p in PROFILES)
SCHEMA = "STAGE3_COMPACT_CHUNK_v2"


class FailClosed(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return float(xs[lo])
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def expected_chunk_bounds(chunk_id: int) -> tuple[int, int]:
    start = chunk_id * CHUNK_SIZE
    end = min(EXPECTED_INPUT_ROWS, start + CHUNK_SIZE)
    return start, end


def chunk_path(chunk_dir: Path, chunk_id: int) -> Path:
    return chunk_dir / f"stage3_chunk_{chunk_id:02d}.json"


def validate_chunk_obj(obj: Any, chunk_id: int) -> bool:
    if not isinstance(obj, dict):
        return False
    start, end = expected_chunk_bounds(chunk_id)
    if obj.get("schema") != SCHEMA:
        return False
    if obj.get("chunk_id") != chunk_id or obj.get("start_index") != start or obj.get("end_index") != end:
        return False
    if obj.get("stage2_catalog_sha256") != EXPECTED_STAGE2_SHA256:
        return False
    if obj.get("stage3_prereg_git_blob") != EXPECTED_STAGE3_PREREG_GIT_BLOB:
        return False
    if obj.get("profiles") != [list(x) for x in PROFILES]:
        return False
    records = obj.get("records")
    if not isinstance(records, list) or len(records) != end - start:
        return False
    seen = set()
    for rec in records:
        if not isinstance(rec, dict):
            return False
        rid = str(rec.get("race_id", ""))
        model = str(rec.get("probability_source", ""))
        if not rid or model not in MODELS or (rid, model) in seen:
            return False
        seen.add((rid, model))
        markets = rec.get("markets")
        if not isinstance(markets, dict) or not markets or not set(markets).issubset(MARKETS):
            return False
        for m, md in markets.items():
            if not isinstance(md, dict):
                return False
            total = md.get("total_ticket_count")
            counts = md.get("candidate_counts")
            if not isinstance(total, int) or total <= 0 or not isinstance(counts, dict) or set(counts) != set(PROFILE_IDS):
                return False
            prior = total + 1
            for pid in PROFILE_IDS:
                c = counts.get(pid)
                if not isinstance(c, int) or c < 0 or c > total or c > prior:
                    return False
                prior = c
    return True


def load_valid_chunk(path: Path, chunk_id: int) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if validate_chunk_obj(obj, chunk_id) else None


def process_stage2_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    rid = str(row.get("race_id", "")).strip()
    model = str(row.get("probability_source", "")).strip()
    if not rid or model not in MODELS:
        raise FailClosed(f"invalid race/model line={line_no} race_id={rid!r} model={model!r}")
    if row.get("result_fields_included") is not False:
        raise FailClosed(f"{rid}/{model}: result firewall flag drift")
    if row.get("settlement_fields_included") is not False:
        raise FailClosed(f"{rid}/{model}: settlement firewall flag drift")
    if row.get("realized_roi_computed") is not False:
        raise FailClosed(f"{rid}/{model}: realized ROI flag drift")
    if row.get("threshold_selected") is not False or row.get("portfolio_constructed") is not False:
        raise FailClosed(f"{rid}/{model}: decision-rule firewall drift")
    if row.get("wide_primary_price_rule") != "LOW":
        raise FailClosed(f"{rid}/{model}: Wide primary price rule drift")

    sold = list(row.get("sold_markets", []))
    if len(sold) != len(set(sold)) or not set(sold).issubset(MARKETS):
        raise FailClosed(f"{rid}/{model}: invalid sold_markets={sold}")
    metrics = row.get("ticket_price_probability_metrics")
    if not isinstance(metrics, dict) or set(metrics) != set(sold):
        raise FailClosed(f"{rid}/{model}: metric market keys != sold markets")

    out_markets: dict[str, Any] = {}
    for market in sold:
        tickets = metrics[market]
        if not isinstance(tickets, dict) or not tickets:
            raise FailClosed(f"{rid}/{model}/{market}: empty/non-object ticket metrics")
        total = len(tickets)
        pass_counts = {pid: 0 for pid in PROFILE_IDS}
        for ticket_key, tm in tickets.items():
            if not isinstance(tm, dict):
                raise FailClosed(f"{rid}/{model}/{market}/{ticket_key}: metric non-object")
            ev = finite_number(tm.get("raw_ev_primary"), f"{rid}/{model}/{market}/{ticket_key}/ev")
            ratio = finite_number(tm.get("shape_edge_ratio_primary"), f"{rid}/{model}/{market}/{ticket_key}/ratio")
            if ratio < 0:
                raise FailClosed(f"{rid}/{model}/{market}/{ticket_key}: negative ratio")
            for pid, ev_min, ratio_min in PROFILES:
                if ev >= ev_min and ratio >= ratio_min:
                    pass_counts[pid] += 1
        prior = total + 1
        for pid in PROFILE_IDS:
            c = pass_counts[pid]
            if c > prior:
                raise FailClosed(f"{rid}/{model}/{market}: profile monotonicity violation at {pid}")
            prior = c
        out_markets[market] = {
            "total_ticket_count": total,
            "candidate_counts": pass_counts,
        }
    return {"race_id": rid, "probability_source": model, "markets": out_markets}


def publish_chunk_atomic(obj: dict[str, Any], final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stage3chunk_") as td:
        tmp = Path(td) / final_path.name
        tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        check = json.loads(tmp.read_text(encoding="utf-8"))
        if not validate_chunk_obj(check, int(obj["chunk_id"])):
            raise FailClosed(f"chunk self-validation failed chunk={obj['chunk_id']}")
        # One small Drive write per 250 Stage2 records.
        shutil.copyfile(tmp, final_path)
        reread = load_valid_chunk(final_path, int(obj["chunk_id"]))
        if reread is None:
            raise FailClosed(f"published chunk validation failed chunk={obj['chunk_id']}")


def aggregate_chunks(chunk_dir: Path, summary_csv: Path, quality_path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for cid in range(EXPECTED_CHUNKS):
        obj = load_valid_chunk(chunk_path(chunk_dir, cid), cid)
        if obj is None:
            raise FailClosed(f"missing/invalid completed chunk={cid}")
        records.extend(obj["records"])
    if len(records) != EXPECTED_INPUT_ROWS:
        raise FailClosed(f"compact record count={len(records)} expected={EXPECTED_INPUT_ROWS}")

    seen = set(); race_ids = set(); market_model_races = Counter(); total_ticket_counts = Counter()
    candidate_totals = Counter(); no_bet_counts = Counter(); per_race_counts: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        rid = rec["race_id"]; model = rec["probability_source"]
        key = (rid, model)
        if key in seen:
            raise FailClosed(f"duplicate compact key={key}")
        seen.add(key); race_ids.add(rid)
        for market, md in rec["markets"].items():
            total = int(md["total_ticket_count"])
            market_model_races[f"{model}:{market}"] += 1
            total_ticket_counts[f"{model}:{market}"] += total
            for pid in PROFILE_IDS:
                c = int(md["candidate_counts"][pid])
                agg = f"{model}:{market}:{pid}"
                candidate_totals[agg] += c
                if c == 0:
                    no_bet_counts[agg] += 1
                per_race_counts[agg].append(c)

    if len(seen) != EXPECTED_INPUT_ROWS or len(race_ids) != EXPECTED_RACES:
        raise FailClosed(f"cardinality mismatch keys={len(seen)} races={len(race_ids)}")
    for model in MODELS:
        for market in MARKETS:
            expected = 211 if market in {"2wakutan", "2wakuhuku"} else EXPECTED_RACES
            observed = market_model_races[f"{model}:{market}"]
            if observed != expected:
                raise FailClosed(f"market coverage drift {model}/{market}: {observed} != {expected}")

    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    diagnostics = {}
    for model in MODELS:
        for market in MARKETS:
            race_count = market_model_races[f"{model}:{market}"]
            total_tickets = total_ticket_counts[f"{model}:{market}"]
            for pid, ev_min, ratio_min in PROFILES:
                agg = f"{model}:{market}:{pid}"
                xs = sorted(per_race_counts[agg])
                candidates = candidate_totals[agg]; no_bet = no_bet_counts[agg]
                d = {
                    "probability_source": model, "market": market, "profile_id": pid,
                    "ev_min": ev_min, "shape_edge_ratio_min": ratio_min,
                    "race_count": race_count, "total_ticket_count": total_tickets,
                    "candidate_ticket_count": candidates,
                    "candidate_ticket_share": candidates / total_tickets,
                    "no_bet_race_count": no_bet, "no_bet_race_share": no_bet / race_count,
                    "candidate_per_race_min": xs[0],
                    "candidate_per_race_p25": quantile_sorted(xs, .25),
                    "candidate_per_race_median": quantile_sorted(xs, .50),
                    "candidate_per_race_p75": quantile_sorted(xs, .75),
                    "candidate_per_race_p90": quantile_sorted(xs, .90),
                    "candidate_per_race_p95": quantile_sorted(xs, .95),
                    "candidate_per_race_p99": quantile_sorted(xs, .99),
                    "candidate_per_race_max": xs[-1],
                    "candidate_per_race_mean": candidates / race_count,
                }
                rows.append(d); diagnostics[agg] = d
    fieldnames = list(rows[0].keys())
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    quality = {
        "record": "STAGE3_TICKET_FILTER_DIAGNOSTICS_QUALITY_v2",
        "status": "PASS",
        "runtime_mode": "RESUMABLE_ATOMIC_CHUNKS",
        "stage2_catalog_sha256": EXPECTED_STAGE2_SHA256,
        "stage3_prereg_git_blob": EXPECTED_STAGE3_PREREG_GIT_BLOB,
        "input_rows": EXPECTED_INPUT_ROWS,
        "unique_races": EXPECTED_RACES,
        "chunk_size": CHUNK_SIZE,
        "completed_chunks": EXPECTED_CHUNKS,
        "profiles": [{"profile_id": a, "ev_min": b, "shape_edge_ratio_min": c} for a,b,c in PROFILES],
        "profile_selection_performed": False,
        "market_specific_threshold_tuning_performed": False,
        "diagnostics": diagnostics,
        "summary_csv_sha256": sha256_file(summary_csv),
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
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return quality


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage2_jsonl")
    ap.add_argument("chunk_dir")
    ap.add_argument("summary_csv")
    ap.add_argument("quality_json")
    ap.add_argument("fatal_json")
    args = ap.parse_args()
    stage2 = Path(args.stage2_jsonl); chunk_dir = Path(args.chunk_dir)
    summary_csv = Path(args.summary_csv); quality = Path(args.quality_json); fatal = Path(args.fatal_json)
    chunk_dir.mkdir(parents=True, exist_ok=True); fatal.parent.mkdir(parents=True, exist_ok=True)
    try:
        observed = sha256_file(stage2)
        if observed != EXPECTED_STAGE2_SHA256:
            raise FailClosed(f"Stage2 SHA mismatch expected={EXPECTED_STAGE2_SHA256} observed={observed}")

        valid_existing = {cid for cid in range(EXPECTED_CHUNKS) if load_valid_chunk(chunk_path(chunk_dir,cid),cid) is not None}
        print(f"[RESUME] valid completed chunks={len(valid_existing)}/{EXPECTED_CHUNKS}", flush=True)
        current_records: list[dict[str, Any]] = []
        current_cid = 0
        line_index = 0

        with stage2.open("r", encoding="utf-8") as src:
            for raw in src:
                if not raw.strip():
                    continue
                if line_index >= EXPECTED_INPUT_ROWS:
                    raise FailClosed("Stage2 has more nonblank rows than expected")
                cid = line_index // CHUNK_SIZE
                start, end = expected_chunk_bounds(cid)
                if cid in valid_existing:
                    line_index += 1
                    if line_index == end:
                        print(f"[SKIP] chunk {cid:02d} already valid ({end}/{EXPECTED_INPUT_ROWS})", flush=True)
                    continue

                try:
                    row = json.loads(raw)
                except Exception as e:
                    raise FailClosed(f"Stage2 JSON parse error index={line_index}: {e}") from e
                current_records.append(process_stage2_row(row, line_index + 1))
                line_index += 1
                if line_index == end:
                    obj = {
                        "schema": SCHEMA,
                        "chunk_id": cid,
                        "start_index": start,
                        "end_index": end,
                        "stage2_catalog_sha256": EXPECTED_STAGE2_SHA256,
                        "stage3_prereg_git_blob": EXPECTED_STAGE3_PREREG_GIT_BLOB,
                        "profiles": [list(x) for x in PROFILES],
                        "created_at_utc": now_utc(),
                        "records": current_records,
                    }
                    publish_chunk_atomic(obj, chunk_path(chunk_dir,cid))
                    print(f"[PASS] chunk {cid:02d} rows={start}-{end-1} ({end}/{EXPECTED_INPUT_ROWS})", flush=True)
                    current_records = []

        if line_index != EXPECTED_INPUT_ROWS:
            raise FailClosed(f"Stage2 row count={line_index} expected={EXPECTED_INPUT_ROWS}")
        if current_records:
            raise FailClosed("internal: unflushed chunk records")

        q = aggregate_chunks(chunk_dir, summary_csv, quality)
        if fatal.exists():
            fatal.unlink()
        print(json.dumps({
            "status": "PASS",
            "completed_chunks": q["completed_chunks"],
            "input_rows": q["input_rows"],
            "unique_races": q["unique_races"],
            "summary_csv_sha256": q["summary_csv_sha256"],
            "profile_selection_performed": False,
            "settlement_access": False,
            "scientific_trial_count": 0,
            "ECON_HOLDOUT1000": "SEALED",
        }, ensure_ascii=False, indent=2), flush=True)
        return 0
    except Exception as e:
        obj = {
            "record": "STAGE3_RUNTIME_FATAL_v2",
            "classification": "SCIENTIFIC_FAIL_CLOSED" if isinstance(e, FailClosed) else "RUNTIME_RETRYABLE",
            "failed_at_utc": now_utc(),
            "error_type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "valid_completed_chunks": [cid for cid in range(EXPECTED_CHUNKS) if load_valid_chunk(chunk_path(chunk_dir,cid),cid) is not None],
            "scientific_trial_count": 0,
            "settlement_access": False,
            "ECON_HOLDOUT1000": "SEALED",
        }
        try:
            fatal.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"status":"FAIL","classification":obj["classification"],"error":str(e),"valid_completed_chunks":obj["valid_completed_chunks"]},ensure_ascii=False,indent=2),file=sys.stderr,flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
