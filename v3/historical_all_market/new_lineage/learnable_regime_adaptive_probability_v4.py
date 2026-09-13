from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import digital_twin_learnable_regime_v2 as twin
import synthetic_market_probability_diagnostic_v1 as v1diag

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_PROBABILITY_PREREG_20260913_v4.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
OUT = ROOT / "research_candidates" / "learnable_regime_adaptive_probability_v4"


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sigmoid(x: float) -> float:
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def mix_joint(c0: dict, n1: dict, w: float) -> dict:
    if set(c0) != set(n1):
        raise RuntimeError("component_support_mismatch")
    if not (0.0 <= w <= 1.0):
        raise RuntimeError("invalid_weight")
    out = {k: (1.0 - w) * float(c0[k]) + w * float(n1[k]) for k in c0}
    if abs(sum(out.values()) - 1.0) > 1e-10:
        raise RuntimeError("mixed_probability_mass_mismatch")
    return out


def stratum(signal: float) -> str:
    if signal < -0.35:
        return "LOW"
    if signal > 0.35:
        return "HIGH"
    return "MID"


def load_rules() -> tuple[dict, dict]:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_rule = json.loads(V1_PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_DESIGN_SCORING":
        raise RuntimeError("prereg_status_invalid")
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("evidence_class_invalid")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False or p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary_invalid")
    return rule, v1_rule


def config_space(rule: dict) -> list[dict]:
    fam = rule["adaptive_family"]
    out = []
    for bias in fam["bias_values"]:
        for slope in fam["slope_values"]:
            cid = f"ADAPT:B{float(bias):+.2f}:S{float(slope):.2f}"
            out.append({"candidate_id": cid, "bias": float(bias), "slope": float(slope)})
    out.sort(key=lambda x: x["candidate_id"])
    if len(out) != int(fam["candidate_count"]):
        raise RuntimeError("candidate_count_mismatch")
    if any(abs(x["bias"] + 0.30) < 1e-12 and abs(x["slope"] - 1.0) < 1e-12 for x in out):
        raise RuntimeError("direct_truth_parameter_pair_not_excluded")
    return out


def evaluate_batch(seed: int, races: int, rule: dict, v1_rule: dict, candidates: list[dict]) -> dict:
    baseline_specs = {
        "C0_SCORE_PL": 0.0,
        "N1_CONDITIONAL": 1.0,
        "GLOBAL_MIX_005": 0.05,
        "GLOBAL_MIX_050": 0.50,
    }
    baseline_kl = {name: [] for name in baseline_specs}
    baseline_stratum = {name: defaultdict(list) for name in baseline_specs}
    candidate_kl = {c["candidate_id"]: [] for c in candidates}
    candidate_stratum = {c["candidate_id"]: defaultdict(list) for c in candidates}
    counts = Counter()

    for idx in range(races):
        race = twin.v1.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = twin.v1.pre_view(race)
        signal = twin.pre_mechanism_signal(pre)
        band = stratum(signal)
        counts[band] += 1

        # Prediction objects are constructed strictly from PRE before scoring-only oracle access.
        forecasts = v1diag.forecasts(pre, v1_rule)
        c0 = forecasts["C0_SCORE_PL"]
        n1 = forecasts["N1_CONDITIONAL"]
        baseline_joint = {name: mix_joint(c0, n1, w) for name, w in baseline_specs.items()}
        adaptive_joint = {}
        for c in candidates:
            w_hat = sigmoid(c["bias"] + c["slope"] * signal)
            adaptive_joint[c["candidate_id"]] = mix_joint(c0, n1, w_hat)

        oracle, _hidden_alpha = twin.learnable_regime_oracle(race)
        for name, joint in baseline_joint.items():
            _ce, kl = v1diag.top3_metrics(oracle, joint)
            baseline_kl[name].append(kl)
            baseline_stratum[name][band].append(kl)
        for cid, joint in adaptive_joint.items():
            _ce, kl = v1diag.top3_metrics(oracle, joint)
            candidate_kl[cid].append(kl)
            candidate_stratum[cid][band].append(kl)

    baselines = {}
    for name in baseline_specs:
        baselines[name] = {
            "overall_mean_KL": mean(baseline_kl[name]),
            "stratum_mean_KL": {b: mean(baseline_stratum[name][b]) for b in ("LOW", "MID", "HIGH") if baseline_stratum[name][b]},
        }
    cand = {}
    for c in candidates:
        cid = c["candidate_id"]
        cand[cid] = {
            "bias": c["bias"],
            "slope": c["slope"],
            "overall_mean_KL": mean(candidate_kl[cid]),
            "stratum_mean_KL": {b: mean(candidate_stratum[cid][b]) for b in ("LOW", "MID", "HIGH") if candidate_stratum[cid][b]},
        }
    return {
        "seed": seed,
        "races": races,
        "stratum_counts": dict(counts),
        "baselines": baselines,
        "candidates": cand,
    }


def best_universal(batch: dict) -> dict:
    b = batch["baselines"]
    overall_name = min(b, key=lambda name: b[name]["overall_mean_KL"])
    strata = {}
    for band in ("LOW", "MID", "HIGH"):
        names = [name for name in b if band in b[name]["stratum_mean_KL"]]
        if names:
            best = min(names, key=lambda name: b[name]["stratum_mean_KL"][band])
            strata[band] = {"name": best, "KL": b[best]["stratum_mean_KL"][band]}
    return {
        "overall": {"name": overall_name, "KL": b[overall_name]["overall_mean_KL"]},
        "strata": strata,
    }


def design_decision(batch: dict) -> dict:
    universal = best_universal(batch)
    counts = batch["stratum_counts"]
    rows = []
    eligible = []
    for cid, row in batch["candidates"].items():
        ratios = {band: row["stratum_mean_KL"][band] / universal["strata"][band]["KL"] for band in universal["strata"]}
        flags = {
            "overall_better_than_best_universal": row["overall_mean_KL"] < universal["overall"]["KL"],
            "all_strata_at_most_1_02x_best_universal": all(v <= 1.02 for v in ratios.values()),
            "low_count_at_least_40": int(counts.get("LOW", 0)) >= 40,
            "high_count_at_least_40": int(counts.get("HIGH", 0)) >= 40,
        }
        flags["eligible"] = all(flags.values())
        r = {**row, "candidate_id": cid, "stratum_relative_to_best_universal": ratios, "eligibility": flags}
        rows.append(r)
        if flags["eligible"]:
            eligible.append(r)
    eligible.sort(key=lambda x: (
        x["overall_mean_KL"],
        max(x["stratum_relative_to_best_universal"].values()),
        abs(x["slope"] - 1.0),
        abs(x["bias"]),
        x["candidate_id"],
    ))
    winner = eligible[0] if eligible else None
    return {
        "best_universal": universal,
        "eligible_count": len(eligible),
        "winner": winner,
        "status": "FROZEN_ONE_ADAPTIVE_MAPPING" if winner else "NO_DEVELOPMENT_ELIGIBLE_ADAPTIVE_MAPPING",
        "candidates": rows,
    }


def evaluation_decision(batch: dict, frozen: dict) -> dict:
    universal = best_universal(batch)
    row = batch["candidates"][frozen["candidate_id"]]
    counts = batch["stratum_counts"]
    ratios = {band: row["stratum_mean_KL"][band] / universal["strata"][band]["KL"] for band in universal["strata"]}
    criteria = {
        "overall_at_most_0_98x_best_universal": row["overall_mean_KL"] <= 0.98 * universal["overall"]["KL"],
        "all_strata_at_most_best_universal": all(v <= 1.0 for v in ratios.values()),
        "low_count_at_least_80": int(counts.get("LOW", 0)) >= 80,
        "high_count_at_least_80": int(counts.get("HIGH", 0)) >= 80,
    }
    passed = all(criteria.values())
    return {
        "status": "PASS_SYNTHETIC_LEARNABLE_REGIME_ADAPTIVE_REPLICATION" if passed else "FAIL_SYNTHETIC_LEARNABLE_REGIME_ADAPTIVE_REPLICATION",
        "frozen_candidate": frozen,
        "best_universal": universal,
        "adaptive": row,
        "stratum_relative_to_best_universal": ratios,
        "criteria": criteria,
    }


def main() -> int:
    rule, v1_rule = load_rules()
    candidates = config_space(rule)
    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_PROBABILITY_GOVERNANCE_AUDIT_v4",
        "status": "PASS_SYNTHETIC_ONLY",
        "evidence_class": rule["evidence_class"],
        "prediction_inputs": "PRE_ONLY",
        "hidden_alpha_used_for_prediction": False,
        "oracle_used_for_prediction": False,
        "world_or_regime_label_used_for_prediction": False,
        "real_historical_input": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "DEV2000_RESULT_PAYOUT": "NOT_ACCESSED",
        "odds": "NOT_USED",
        "economics": "NOT_COMPUTED",
        "roi": "NOT_COMPUTED",
        "runtime": "OFF",
        "automatic_betting": False,
        "real_money": False,
        "spend": False,
        "credential": False,
    })

    dcfg = rule["design_batch"]
    design = evaluate_batch(int(dcfg["seed"]), int(dcfg["races"]), rule, v1_rule, candidates)
    decision = design_decision(design)
    dump("01_DESIGN_SCORE_AND_FREEZE.json", {
        "record": "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_DESIGN_v4",
        "status": decision["status"],
        "design": design,
        "selection": decision,
        "evaluation_accessed": False,
    })

    winner = decision["winner"]
    if winner is None:
        final = {
            "record": "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_DECISION_v4",
            "status": "NO_DEVELOPMENT_ELIGIBLE_ADAPTIVE_MAPPING",
            "evaluation_accessed": False,
            "model_promotion": False,
            "real_world_claim": False,
            "evidence_class": rule["evidence_class"],
        }
        dump("02_EVALUATION_SCORE.json", {"status": "NOT_ACCESSED_NO_DESIGN_WINNER", "evaluation_seed_accessed": False})
        dump("03_DECISION.json", final)
        print(json.dumps(final, sort_keys=True))
        return 0

    frozen = {"candidate_id": winner["candidate_id"], "bias": winner["bias"], "slope": winner["slope"]}
    ecfg = rule["evaluation_batch"]
    eval_batch = evaluate_batch(int(ecfg["seed"]), int(ecfg["races"]), rule, v1_rule, [frozen])
    eval_dec = evaluation_decision(eval_batch, frozen)
    dump("02_EVALUATION_SCORE.json", {
        "record": "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_EVALUATION_v4",
        "status": eval_dec["status"],
        "evaluation_seed_accessed": True,
        "evaluation": eval_batch,
        "decision": eval_dec,
    })
    final = {
        "record": "KEIRIN_LEARNABLE_REGIME_ADAPTIVE_DECISION_v4",
        "status": eval_dec["status"],
        "design_eligible_count": decision["eligible_count"],
        "frozen_candidate": frozen,
        "evaluation_decision": eval_dec,
        "model_promotion": False,
        "real_world_claim": False,
        "evidence_class": rule["evidence_class"],
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("03_DECISION.json", final)
    print(json.dumps({
        "status": final["status"],
        "frozen_candidate": frozen,
        "criteria": eval_dec["criteria"],
        "runtime": "OFF",
        "automatic_betting": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
