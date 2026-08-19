#!/usr/bin/env python3
"""Diagnostic-only postmortem for the closed DEV2000 Stage-7 A/B lineage.

Purpose:
- replay the already-frozen A_TOP10 on Segment A and Segment B only
- report exact B metrics plus daily/weekly/monthly stability and return concentration
- verify A replay equals the frozen A_TOP10 receipt

STRICTLY NO:
- Segment C settlement access
- ECON_HOLDOUT1000 access
- new rule selection / threshold tuning / model refit
- live wagering
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

EXPECTED_EVALUATOR_BLOB = "ce8e109fa4c20f683ea1ec999b2fe5dd6f49c865"
EXPECTED_STAGE2_SHA256 = "34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_PRED_SHA256 = "772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
EXPECTED_UNIVERSE_SHA256 = "eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"

class FailClosed(RuntimeError):
    pass

def git_blob_sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def import_evaluator(repo: Path):
    p = repo / "v3" / "historical_all_market" / "stage7_frozen_evaluator_v2.py"
    if not p.is_file():
        raise FailClosed(f"evaluator missing: {p}")
    blob = git_blob_sha1_bytes(p.read_bytes())
    if blob != EXPECTED_EVALUATOR_BLOB:
        raise FailClosed(f"evaluator blob mismatch: {blob} != {EXPECTED_EVALUATOR_BLOB}")
    spec = importlib.util.spec_from_file_location("multiverse_closed_stage7_eval", p)
    if spec is None or spec.loader is None:
        raise FailClosed("cannot import evaluator")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_dates(universe: Path) -> dict[int, str]:
    out = {}
    with universe.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            idx = int(r["dev_index"])
            ds = str(r["race_date"]).strip()
            date.fromisoformat(ds)
            if idx in out:
                raise FailClosed(f"duplicate universe date idx={idx}")
            out[idx] = ds
    if set(out) != set(range(1, 2001)):
        raise FailClosed("universe date index set != 1..2000")
    return out

def load_ab_receipt(path: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    x = json.loads(path.read_text(encoding="utf-8"))
    if x.get("status") != "NO_B_VALIDATED_CONFIGURATION":
        raise FailClosed("postmortem requires closed NO_B_VALIDATED_CONFIGURATION receipt")
    if x.get("segment_c_opened") is not False or int(x.get("scientific_segment_c_scoring_count", -1)) != 0:
        raise FailClosed("closed receipt says Segment C was opened/scored")
    if x.get("ECON_HOLDOUT1000") != "SEALED":
        raise FailClosed("HOLDOUT state drift")
    top = x.get("A_TOP10")
    if not isinstance(top, list) or len(top) != 10:
        raise FailClosed("A_TOP10 cardinality != 10")
    ids = []
    metrics = {}
    for r in top:
        cid = str(r.get("configuration_id", ""))
        if not cid or cid in metrics:
            raise FailClosed("duplicate/blank A_TOP10 config")
        ids.append(cid)
        metrics[cid] = r
    return ids, metrics

def rank_selected(mod, selected):
    return mod.global_rank(selected)

def ticket_return_details(allocations, settlement):
    sett = settlement["settlements_yen_per_100"]
    ticket_returns = []
    ticket_profits = []
    hits = 0
    for m, k, _, stake in allocations:
        pay = int(sett.get(m, {}).get(k, 0))
        ret = pay * (int(stake) // 100) if pay > 0 else 0
        if ret > 0:
            hits += 1
            ticket_returns.append(ret)
        ticket_profits.append(ret - int(stake))
    return hits, ticket_returns, ticket_profits

def replay_top10(mod, stage2: Path, by_idx: dict[int, str], pred: dict, dates: dict[int, str],
                 A_sett: dict[str, Any], B_sett: dict[str, Any], cids: list[str]):
    states = {
        "A": {cid: mod.SegmentState() for cid in cids},
        "B": {cid: mod.SegmentState() for cid in cids},
    }
    ledger = {cid: {"A": [], "B": []} for cid in cids}
    bases = {mod.parse_config(cid)[:3] for cid in cids}

    for idx, A, B in mod.iter_stage2_pairs(stage2, by_idx):
        if idx > 1500:
            break
        seg = "A" if idx <= 1000 else "B"
        rid = by_idx[idx]
        settlement = A_sett[rid] if seg == "A" else B_sett[rid]
        sel_by_base = mod.selections_for_needed_bases(mod_stage456, rid, A, B, pred, bases)
        for cid in cids:
            p, g, t, pol = mod.parse_config(cid)
            selected = rank_selected(mod, sel_by_base[(p, g, t)])
            st = states[seg][cid]
            allocations = mod.allocate_stakes(selected, pol, st.bankroll)
            hits, ticket_returns, ticket_profits = ticket_return_details(allocations, settlement)
            race = st.settle_race(allocations, settlement)
            if int(race["hit_ticket_count"]) != hits:
                raise FailClosed(f"{rid}/{cid}: hit-accounting mismatch")
            ledger[cid][seg].append({
                "dev_index": idx,
                "race_id": rid,
                "race_date": dates[idx],
                "stake": int(race["stake"]),
                "return": int(race["return"]),
                "race_profit": int(race["return"]) - int(race["stake"]),
                "bet_ticket_count": int(race["bet_ticket_count"]),
                "hit_ticket_count": int(race["hit_ticket_count"]),
                "positive_ticket_returns": ticket_returns,
                "ticket_profits": ticket_profits,
                "bankroll_after": int(race["bankroll_after"]),
            })
    return states, ledger

def period_key(ds: str, mode: str) -> str:
    d = date.fromisoformat(ds)
    if mode == "daily":
        return ds
    if mode == "weekly":
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if mode == "monthly":
        return f"{d.year:04d}-{d.month:02d}"
    raise ValueError(mode)

def consecutive_negative(values: list[float]) -> int:
    best = cur = 0
    for v in values:
        if v < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best

def period_metrics(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    g = defaultdict(lambda: {"stake": 0, "return": 0, "bet_races": 0})
    for r in rows:
        k = period_key(r["race_date"], mode)
        g[k]["stake"] += int(r["stake"])
        g[k]["return"] += int(r["return"])
        if int(r["stake"]) > 0:
            g[k]["bet_races"] += 1
    active = []
    for k in sorted(g):
        q = g[k]
        if q["stake"] <= 0:
            continue
        roi = q["return"] / q["stake"] - 1.0
        active.append({"period": k, **q, "roi": roi})
    rois = [x["roi"] for x in active]
    if not rois:
        return {
            "active_periods": 0, "positive_periods": 0, "zero_periods": 0, "negative_periods": 0,
            "positive_active_period_share": None, "median_roi": None, "worst_roi": None, "best_roi": None,
            "maximum_consecutive_losing_active_periods": 0, "periods": [],
        }
    srt = sorted(rois)
    n = len(srt)
    median = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2.0
    pos = sum(v > 0 for v in rois); zero = sum(v == 0 for v in rois); neg = sum(v < 0 for v in rois)
    return {
        "active_periods": len(rois), "positive_periods": pos, "zero_periods": zero, "negative_periods": neg,
        "positive_active_period_share": pos / len(rois), "median_roi": median,
        "worst_roi": min(rois), "best_roi": max(rois),
        "maximum_consecutive_losing_active_periods": consecutive_negative(rois), "periods": active,
    }

def concentration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_return = sum(int(r["return"]) for r in rows)
    ticket_returns = sorted((v for r in rows for v in r["positive_ticket_returns"] if v > 0), reverse=True)
    race_returns = sorted((int(r["return"]) for r in rows if int(r["return"]) > 0), reverse=True)
    race_profits = [int(r["race_profit"]) for r in rows]
    total_profit = sum(race_profits)
    def share(vals, n):
        if total_return <= 0 or not vals:
            return None
        return sum(vals[:n]) / total_return
    return {
        "total_realized_return": total_return,
        "positive_ticket_return_count": len(ticket_returns),
        "largest_single_ticket_return_share": share(ticket_returns, 1),
        "top3_ticket_return_share": share(ticket_returns, 3),
        "largest_winning_race_return_share": share(race_returns, 1),
        "top3_winning_race_return_share": share(race_returns, 3),
        "best_race_profit_share_of_total_profit": (max(race_profits) / total_profit) if race_profits and total_profit > 0 else None,
    }

def close_enough(a: Any, b: Any, tol: float = 1e-12) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)
    return a == b

def verify_A_replay(states, frozen_A):
    fields = ["realized_roi", "total_stake", "total_return", "bet_race_count", "hit_ticket_count", "ending_bankroll", "maximum_drawdown", "minimum_bankroll", "negative_bankroll"]
    for cid, expected in frozen_A.items():
        got = states["A"][cid].metrics()
        for f in fields:
            if not close_enough(got[f], expected[f]):
                raise FailClosed(f"A replay mismatch {cid}/{f}: {got[f]} != {expected[f]}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--stage2-jsonl", required=True)
    ap.add_argument("--prediction-csv", required=True)
    ap.add_argument("--universe-csv", required=True)
    ap.add_argument("--settlement-dir", required=True)
    ap.add_argument("--ab-receipt", required=True)
    ap.add_argument("--out-json", required=True)
    return ap.parse_args()

def main() -> int:
    global mod_stage456
    a = parse_args()
    repo = Path(a.repo_root)
    stage2 = Path(a.stage2_jsonl); pred_path = Path(a.prediction_csv); universe = Path(a.universe_csv)
    settlement_dir = Path(a.settlement_dir); ab_receipt = Path(a.ab_receipt); out_json = Path(a.out_json)

    if sha256_file(stage2) != EXPECTED_STAGE2_SHA256 or sha256_file(pred_path) != EXPECTED_PRED_SHA256 or sha256_file(universe) != EXPECTED_UNIVERSE_SHA256:
        raise FailClosed("exact input SHA binding failed")

    mod = import_evaluator(repo)
    mod.verify_governance(repo)
    mod.verify_input_hashes(stage2, pred_path, universe)
    mod_stage456 = mod.import_stage456(repo)
    by_idx, _ = mod.load_universe(universe)
    pred = mod.load_predictions(pred_path)
    dates = load_dates(universe)
    cids, frozen_A = load_ab_receipt(ab_receipt)

    A_sett = mod.load_settlement_segment(settlement_dir / "DEV2000_SETTLEMENT_A_v1.jsonl", "A", set(range(1, 1001)), by_idx)
    B_sett = mod.load_settlement_segment(settlement_dir / "DEV2000_SETTLEMENT_B_v1.jsonl", "B", set(range(1001, 1501)), by_idx)

    states, ledger = replay_top10(mod, stage2, by_idx, pred, dates, A_sett, B_sett, cids)
    verify_A_replay(states, frozen_A)

    configs = []
    for cid in cids:
        segs = {}
        for seg in ("A", "B"):
            rows = ledger[cid][seg]
            segs[seg] = {
                "overall": states[seg][cid].metrics(),
                "daily": period_metrics(rows, "daily"),
                "weekly": period_metrics(rows, "weekly"),
                "monthly": period_metrics(rows, "monthly"),
                "return_concentration": concentration(rows),
            }
        configs.append({"configuration_id": cid, "segments": segs})

    out = {
        "record": "STAGE7_AB_POSTMORTEM_DIAGNOSTICS_v1",
        "status": "PASS_DIAGNOSTIC_ONLY",
        "closed_lineage_status": "NO_B_VALIDATED_CONFIGURATION",
        "A_replay_exact_match_to_frozen_receipt": True,
        "A_TOP10_count": 10,
        "segment_C_access": False,
        "segment_C_scoring_count": 0,
        "new_rule_selection_performed": False,
        "model_refit_performed": False,
        "ECON_HOLDOUT1000": "SEALED",
        "stage2_sha256": EXPECTED_STAGE2_SHA256,
        "prediction_sha256": EXPECTED_PRED_SHA256,
        "universe_sha256": EXPECTED_UNIVERSE_SHA256,
        "evaluator_git_blob": EXPECTED_EVALUATOR_BLOB,
        "configs": configs,
    }
    atomic_json(out_json, out)
    print(json.dumps({
        "status": out["status"],
        "A_TOP10_count": 10,
        "B_metrics_emitted": 10,
        "segment_C_access": False,
        "ECON_HOLDOUT1000": "SEALED",
        "output_sha256": sha256_file(out_json),
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
