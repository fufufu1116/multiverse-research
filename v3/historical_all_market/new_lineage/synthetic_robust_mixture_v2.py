from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean

import synthetic_market_probability_diagnostic_v1 as v1

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_PREREG_20260913_v2.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
V1_SCRIPT = HERE / "synthetic_market_probability_diagnostic_v1.py"
OUT = ROOT / "research_candidates" / "synthetic_robust_mixture_v2"
EXPECTED_PREREG_SHA256 = "b57f585da1f62c4cc96d127dad058c7d9a8ab86fb214f43a047601b754c90fa2"
EXPECTED_V1_PREREG_SHA256 = "ad96bd369ccee1177dbf9979314f36bfb61e631145c3ed0818ac3bbed7c248b2"
EXPECTED_V1_SCRIPT_SHA256 = "2356765dfca8764065ccda8927227420c832e5a3f8dd25c8056a1630be7b88c1"
WORLDS = ("W0", "W1", "W2", "W3", "W4")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def load_rules() -> tuple[dict, dict]:
    if sha256_file(PREREG) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("v2_prereg_sha256_mismatch")
    if sha256_file(V1_PREREG) != EXPECTED_V1_PREREG_SHA256:
        raise RuntimeError("v1_prereg_sha256_mismatch")
    if sha256_file(V1_SCRIPT) != EXPECTED_V1_SCRIPT_SHA256:
        raise RuntimeError("v1_implementation_sha256_mismatch")
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_rule = json.loads(V1_PREREG.read_text(encoding="utf-8"))
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("invalid_evidence_class")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False or p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary_invalid")
    return rule, v1_rule


def mix_joint(c0: dict, n1: dict, weight: float) -> dict:
    if set(c0) != set(n1):
        raise RuntimeError("component_support_mismatch")
    out = {k: (1.0 - weight) * float(c0[k]) + weight * float(n1[k]) for k in c0}
    mass = sum(out.values())
    if abs(mass - 1.0) > 1e-10:
        raise RuntimeError(f"mixture_mass_mismatch:{mass}")
    return out


def evaluate_seed(seed: int, n_races: int, weights: list[float], v1_rule: dict) -> dict:
    c0_kls = {w: [] for w in WORLDS}
    mix_kls = {weight: {w: [] for w in WORLDS} for weight in weights}

    for idx in range(n_races):
        race = v1.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = v1.pre_view(race)
        forecast = v1.forecasts(pre, v1_rule)
        c0 = forecast["C0_SCORE_PL"]
        n1 = forecast["N1_CONDITIONAL"]
        mixes = {weight: mix_joint(c0, n1, weight) for weight in weights}
        for world in WORLDS:
            oracle = v1.world_joint_distribution(race, world)
            _ce, c0_kl = v1.top3_metrics(oracle, c0)
            c0_kls[world].append(c0_kl)
            for weight, joint in mixes.items():
                _ce, kl = v1.top3_metrics(oracle, joint)
                mix_kls[weight][world].append(kl)

    baseline = {world: mean(c0_kls[world]) for world in WORLDS}
    candidates = {
        str(weight): {world: mean(mix_kls[weight][world]) for world in WORLDS}
        for weight in weights
    }
    return {
        "seed": seed,
        "races_per_world": n_races,
        "worlds": list(WORLDS),
        "baseline_C0_mean_KL": baseline,
        "candidate_mean_KL": candidates,
    }


def aggregate(row: dict) -> dict:
    vals = [float(row[w]) for w in WORLDS]
    return {
        "max_world_mean_KL": max(vals),
        "mean_of_world_mean_KL": mean(vals),
    }


def design_decision(design: dict, weights: list[float]) -> dict:
    baseline = design["baseline_C0_mean_KL"]
    base_agg = aggregate(baseline)
    rows = []
    eligible = []
    for weight in weights:
        per_world = design["candidate_mean_KL"][str(weight)]
        agg = aggregate(per_world)
        rel = {w: per_world[w] / baseline[w] for w in WORLDS}
        flags = {
            "max_world_KL_strictly_lower_than_C0": agg["max_world_mean_KL"] < base_agg["max_world_mean_KL"],
            "all_worlds_at_most_1_05x_C0": all(rel[w] <= 1.05 for w in WORLDS),
        }
        flags["eligible"] = all(flags.values())
        row = {
            "weight": weight,
            "per_world_mean_KL": per_world,
            "relative_to_C0": rel,
            **agg,
            "eligibility": flags,
        }
        rows.append(row)
        if flags["eligible"]:
            eligible.append(row)

    eligible.sort(key=lambda x: (x["max_world_mean_KL"], x["mean_of_world_mean_KL"], x["weight"]))
    winner = eligible[0] if eligible else None
    return {
        "baseline_C0": {**baseline, **base_agg},
        "candidates": rows,
        "eligible_count": len(eligible),
        "winner": winner,
        "status": "FROZEN_ONE_GLOBAL_MIXTURE" if winner else "NO_DEVELOPMENT_ELIGIBLE_GLOBAL_MIXTURE",
    }


def evaluation_decision(evaluation: dict, weight: float) -> dict:
    baseline = evaluation["baseline_C0_mean_KL"]
    per_world = evaluation["candidate_mean_KL"][str(weight)]
    base_agg = aggregate(baseline)
    mix_agg = aggregate(per_world)
    rel = {w: per_world[w] / baseline[w] for w in WORLDS}
    flags = {
        "max_world_KL_strictly_lower_than_C0": mix_agg["max_world_mean_KL"] < base_agg["max_world_mean_KL"],
        "mean_world_KL_at_most_C0": mix_agg["mean_of_world_mean_KL"] <= base_agg["mean_of_world_mean_KL"],
        "all_worlds_at_most_1_05x_C0": all(rel[w] <= 1.05 for w in WORLDS),
    }
    passed = all(flags.values())
    return {
        "weight": weight,
        "baseline_C0": {**baseline, **base_agg},
        "mixture": {**per_world, **mix_agg},
        "relative_to_C0": rel,
        "criteria": flags,
        "status": "PASS_SYNTHETIC_ROBUST_MIXTURE_REPLICATION" if passed else "FAIL_SYNTHETIC_ROBUST_MIXTURE_REPLICATION",
    }


def main() -> int:
    rule, v1_rule = load_rules()
    weights = [float(x) for x in rule["architecture"]["candidate_weights"]]

    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_GOVERNANCE_AUDIT_v2",
        "status": "PASS_SYNTHETIC_ONLY",
        "prereg_sha256": EXPECTED_PREREG_SHA256,
        "v1_prereg_sha256": EXPECTED_V1_PREREG_SHA256,
        "v1_implementation_sha256": EXPECTED_V1_SCRIPT_SHA256,
        "prediction_world_identity_used": False,
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

    design_cfg = rule["design_batch"]
    design = evaluate_seed(
        seed=int(design_cfg["seed"]),
        n_races=int(design_cfg["races_per_world"]),
        weights=weights,
        v1_rule=v1_rule,
    )
    decision = design_decision(design, weights)
    dump("01_DESIGN_SCORE_AND_FREEZE.json", {
        "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_DESIGN_v2",
        "status": decision["status"],
        "design": design,
        "selection": decision,
        "evaluation_accessed": False,
    })

    winner = decision["winner"]
    if winner is None:
        dump("02_EVALUATION_SCORE.json", {
            "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_EVALUATION_v2",
            "status": "NOT_ACCESSED_NO_DESIGN_WINNER",
            "evaluation_seed_accessed": False,
        })
        final = {
            "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_DECISION_v2",
            "status": "NO_DEVELOPMENT_ELIGIBLE_GLOBAL_MIXTURE",
            "design_eligible_count": 0,
            "evaluation_accessed": False,
            "model_promotion": False,
            "real_world_claim": False,
            "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        }
        dump("03_DECISION.json", final)
        print(json.dumps(final, sort_keys=True))
        return 0

    weight = float(winner["weight"])
    eval_cfg = rule["evaluation_batch"]
    evaluation = evaluate_seed(
        seed=int(eval_cfg["seed"]),
        n_races=int(eval_cfg["races_per_world"]),
        weights=[weight],
        v1_rule=v1_rule,
    )
    eval_decision = evaluation_decision(evaluation, weight)
    dump("02_EVALUATION_SCORE.json", {
        "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_EVALUATION_v2",
        "status": eval_decision["status"],
        "evaluation_seed_accessed": True,
        "evaluation": evaluation,
        "decision": eval_decision,
    })
    final = {
        "record": "KEIRIN_SYNTHETIC_ROBUST_MIXTURE_DECISION_v2",
        "status": eval_decision["status"],
        "design_eligible_count": int(decision["eligible_count"]),
        "frozen_weight": weight,
        "design_winner": winner,
        "evaluation_decision": eval_decision,
        "evaluation_accessed": True,
        "model_promotion": False,
        "real_world_claim": False,
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("03_DECISION.json", final)
    print(json.dumps({
        "status": final["status"],
        "frozen_weight": weight,
        "evaluation_criteria": eval_decision["criteria"],
        "runtime": "OFF",
        "automatic_betting": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
