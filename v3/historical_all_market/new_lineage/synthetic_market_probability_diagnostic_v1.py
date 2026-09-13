from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from digital_twin_v1 import generate_race, pre_view, world_joint_distribution
from probability_object_contract_v1 import derive_market_probabilities
from top3_architecture_core_v1 import (
    conditional_top3_from_context_logits,
    pl_top3_from_runner_utilities,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
OUT = ROOT / "research_candidates" / "synthetic_market_probability_diagnostic_v1"
EXPECTED_PREREG_SHA256 = "ad96bd369ccee1177dbf9979314f36bfb61e631145c3ed0818ac3bbed7c248b2"
WORLDS = ("W0", "W1", "W2", "W3", "W4")
MODELS = ("C0_SCORE_PL", "C1_LINE_PL", "N1_CONDITIONAL")
MARKETS = ("3rentan", "3renhuku", "2shatan", "2shahuku", "wide")
EPS = 1e-15


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_prereg() -> dict:
    if sha256_file(PREREG) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("prereg_sha256_mismatch")
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("invalid_evidence_class")
    p = rule["protected_boundaries"]
    required = {
        "real_historical_input": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "DEV2000_RESULT_PAYOUT": "NOT_ACCESSED",
        "odds": "NOT_USED",
        "roi": "NOT_COMPUTED",
        "runtime": "OFF",
        "automatic_betting": False,
        "real_money": False,
        "spend": False,
        "credential": False,
    }
    if p != required:
        raise RuntimeError("protected_boundary_mismatch")
    return rule


def c1_utilities(pre: dict, coeff: dict) -> dict[int, float]:
    riders = pre["riders"]
    line_scores: dict[int, list[float]] = defaultdict(list)
    for r in riders:
        line_scores[int(r["line_group_id"])].append(float(r["score"]))
    line_mean = {k: sum(v) / len(v) for k, v in line_scores.items()}

    out: dict[int, float] = {}
    bank = float(pre["bank_length_m"])
    wind = float(pre["wind_speed_mps"])
    for r in riders:
        car = int(r["car_no"])
        style = str(r["style"])
        pos = int(r["line_position"])
        size = int(r["line_size"])
        line_id = int(r["line_group_id"])
        value = float(r["score"])
        value += float(coeff["class"][str(r["class"])])
        value += float(coeff["style"][style])
        wind_coeff = float(coeff["wind_penalty_head"] if pos == 0 else coeff["wind_penalty_other"])
        value -= wind_coeff * wind
        if bank <= 333.0 and style in {"逃", "両"}:
            value += float(coeff["short_bank_self_power_bonus"])
        value += float(coeff["line_mean_score"]) * line_mean[line_id]
        value += float(coeff["line_position"].get(str(pos), 0.0))
        value += float(coeff["line_size_per_extra"]) * max(0, size - 1)
        out[car] = value
    return out


def forecasts(pre: dict, rule: dict) -> dict[str, dict[tuple[int, int, int], float]]:
    c0 = {int(r["car_no"]): float(r["score"]) for r in pre["riders"]}
    c1_coeff = rule["architectures"]["C1_LINE_PL"]["fixed_coefficients"]
    c1 = c1_utilities(pre, c1_coeff)

    cars = sorted(c1)
    rel = rule["architectures"]["N1_CONDITIONAL"]["fixed_context_coefficients"]
    riders = {int(r["car_no"]): r for r in pre["riders"]}
    p2: dict[tuple[int, int], float] = {}
    p3: dict[tuple[int, int, int], float] = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = int(rc["line_group_id"]) == int(rf["line_group_id"])
            follower = same and int(rc["line_position"]) == int(rf["line_position"]) + 1
            p2[(first, candidate)] = (
                c1[candidate]
                + float(rel["p2_same_line"]) * float(same)
                + float(rel["p2_immediate_follower"]) * float(follower)
            )

    for first in cars:
        rf = riders[first]
        for second in cars:
            if second == first:
                continue
            rs = riders[second]
            for candidate in cars:
                if candidate in (first, second):
                    continue
                rc = riders[candidate]
                same_f = int(rc["line_group_id"]) == int(rf["line_group_id"])
                same_s = int(rc["line_group_id"]) == int(rs["line_group_id"])
                chain = (
                    int(rf["line_group_id"]) == int(rs["line_group_id"]) == int(rc["line_group_id"])
                    and int(rf["line_position"]) < int(rs["line_position"]) < int(rc["line_position"])
                )
                p3[(first, second, candidate)] = (
                    c1[candidate]
                    + float(rel["p3_same_as_first"]) * float(same_f)
                    + float(rel["p3_same_as_second"]) * float(same_s)
                    + float(rel["p3_ordered_line_chain"]) * float(chain)
                )

    return {
        "C0_SCORE_PL": pl_top3_from_runner_utilities(c0),
        "C1_LINE_PL": pl_top3_from_runner_utilities(c1),
        "N1_CONDITIONAL": conditional_top3_from_context_logits(c1, p2, p3),
    }


def top3_metrics(oracle: dict, forecast: dict) -> tuple[float, float]:
    ce = 0.0
    kl = 0.0
    for key, q in oracle.items():
        p = max(float(forecast[key]), EPS)
        qf = float(q)
        ce -= qf * math.log(p)
        if qf > 0.0:
            kl += qf * math.log(qf / p)
    return ce, kl


def reliability(rows: list[tuple[float, float]], bins: list[float]) -> list[dict]:
    out = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        vals = [(p, q) for p, q in rows if lo <= p < hi]
        if not vals:
            continue
        mp = mean(x[0] for x in vals)
        mq = mean(x[1] for x in vals)
        out.append({
            "lo": lo,
            "hi": hi,
            "n": len(vals),
            "mean_forecast": mp,
            "mean_oracle": mq,
            "absolute_gap": abs(mp - mq),
        })
    return out


def main() -> int:
    rule = load_prereg()
    seed = int(rule["batch"]["seed"])
    n_races = int(rule["batch"]["races_per_world"])
    bins = [float(x) for x in rule["reliability_bins"]]

    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_GOVERNANCE_AUDIT_v1",
        "status": "PASS_SYNTHETIC_ONLY",
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "real_historical_input": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "DEV2000_RESULT_PAYOUT": "NOT_ACCESSED",
        "odds": "NOT_USED",
        "roi": "NOT_COMPUTED",
        "runtime": "OFF",
        "automatic_betting": False,
        "real_money": False,
        "spend": False,
        "credential": False,
    })

    top_acc: dict[str, dict[str, list[float]]] = {
        w: {m: [] for m in MODELS} for w in WORLDS
    }
    ce_acc: dict[str, dict[str, list[float]]] = {
        w: {m: [] for m in MODELS} for w in WORLDS
    }
    market_rows: dict[str, dict[str, dict[str, list[tuple[float, float]]]]] = {
        w: {m: {mk: [] for mk in MARKETS} for m in MODELS} for w in WORLDS
    }
    mass_errors: dict[str, dict[str, dict[str, float]]] = {
        w: {m: {mk: 0.0 for mk in MARKETS} for m in MODELS} for w in WORLDS
    }

    for world in WORLDS:
        for idx in range(n_races):
            race = generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
            pre = pre_view(race)
            oracle = world_joint_distribution(race, world)
            oracle_market = derive_market_probabilities(oracle)
            pred = forecasts(pre, rule)
            for model, joint in pred.items():
                ce, kl = top3_metrics(oracle, joint)
                ce_acc[world][model].append(ce)
                top_acc[world][model].append(kl)
                market = derive_market_probabilities(joint)
                for mk in MARKETS:
                    if set(market[mk]) != set(oracle_market[mk]):
                        raise RuntimeError(f"market_support_mismatch:{world}:{model}:{mk}")
                    target_mass = 3.0 if mk == "wide" else 1.0
                    mass_errors[world][model][mk] = max(
                        mass_errors[world][model][mk],
                        abs(sum(market[mk].values()) - target_mass),
                    )
                    for key, p in market[mk].items():
                        market_rows[world][model][mk].append((float(p), float(oracle_market[mk][key])))

    result_worlds = {}
    world_kls: dict[str, dict[str, float]] = {}
    for world in WORLDS:
        result_worlds[world] = {}
        world_kls[world] = {}
        for model in MODELS:
            market_metrics = {}
            for mk in MARKETS:
                rows = market_rows[world][model][mk]
                mse = mean((p - q) ** 2 for p, q in rows)
                mae = mean(abs(p - q) for p, q in rows)
                rel = reliability(rows, bins)
                market_metrics[mk] = {
                    "event_count": len(rows),
                    "rmse_vs_exact_oracle": math.sqrt(mse),
                    "mae_vs_exact_oracle": mae,
                    "reliability_bins": rel,
                    "mean_reliability_abs_gap": mean(x["absolute_gap"] for x in rel) if rel else None,
                    "max_probability_mass_error": mass_errors[world][model][mk],
                }
            avg_kl = mean(top_acc[world][model])
            world_kls[world][model] = avg_kl
            result_worlds[world][model] = {
                "races": n_races,
                "mean_ordered_top3_cross_entropy": mean(ce_acc[world][model]),
                "mean_ordered_top3_kl_oracle_to_forecast": avg_kl,
                "markets": market_metrics,
            }

    best_pl = {w: min(world_kls[w]["C0_SCORE_PL"], world_kls[w]["C1_LINE_PL"]) for w in WORLDS}
    base_pl = mean(best_pl[w] for w in ("W0", "W1"))
    hard_pl = mean(best_pl[w] for w in ("W2", "W3", "W4"))
    hard_n1 = mean(world_kls[w]["N1_CONDITIONAL"] for w in ("W2", "W3", "W4"))
    conditional_gate = (
        base_pl > 0.0
        and hard_pl >= 1.20 * base_pl
        and hard_n1 <= 0.90 * hard_pl
    )

    winners = []
    for world in WORLDS:
        vals = world_kls[world]
        best = min(vals.values())
        ws = [m for m, v in vals.items() if abs(v - best) <= 1e-15]
        winners.append(ws[0] if len(ws) == 1 else "TIE")
    stable = winners[0] if len(set(winners)) == 1 and winners[0] != "TIE" else None

    classifications = []
    if conditional_gate:
        classifications.append("SYNTHETICALLY_PLAUSIBLE_CONDITIONAL_ORDER_FAILURE_MODE")
    if stable is not None:
        classifications.append(f"STABLE_SYNTHETIC_ARCHITECTURE_ADVANTAGE:{stable}")
    if not classifications:
        classifications.append("NO_STABLE_SYNTHETIC_ARCHITECTURE_ADVANTAGE")

    result = {
        "record": "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_RESULT_v1",
        "status": "COMPLETE_SYNTHETIC_ENGINEERING_ONLY",
        "prereg_sha256": EXPECTED_PREREG_SHA256,
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "worlds": result_worlds,
        "decision_metrics": {
            "best_pl_mean_kl_W0_W1": base_pl,
            "best_pl_mean_kl_W2_W4": hard_pl,
            "n1_mean_kl_W2_W4": hard_n1,
            "hard_vs_base_best_pl_kl_ratio": hard_pl / base_pl if base_pl > 0.0 else None,
            "n1_vs_best_pl_hard_kl_ratio": hard_n1 / hard_pl if hard_pl > 0.0 else None,
            "world_lowest_kl_architecture": {w: winners[i] for i, w in enumerate(WORLDS)},
        },
        "classifications": classifications,
        "conditional_order_failure_gate_passed": conditional_gate,
        "stable_architecture": stable,
        "claim_boundary": {
            "real_keirin_calibration_claim": False,
            "real_keirin_predictive_edge_claim": False,
            "roi_or_profit_claim": False,
            "model_promotion": False,
            "note": "N1 context terms intentionally target a designed synthetic relation axis; results are sensitivity/falsification evidence only.",
        },
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("01_RESULT.json", result)
    print(json.dumps({
        "status": result["status"],
        "classifications": classifications,
        "decision_metrics": result["decision_metrics"],
        "runtime": "OFF",
        "automatic_betting": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
