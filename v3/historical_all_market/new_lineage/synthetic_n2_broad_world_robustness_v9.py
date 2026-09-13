from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import digital_twin_v1 as twin
import synthetic_market_probability_diagnostic_v1 as diag
import synthetic_spec_aligned_conditional_v6 as v6

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_N2_BROAD_WORLD_ROBUSTNESS_PREREG_20260914_v9.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
V6_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_SPEC_ALIGNED_CONDITIONAL_PREREG_20260914_v6.json"
OUT = ROOT / "research_candidates" / "synthetic_n2_broad_world_robustness_v9"

LEGACY = ("C0_SCORE_PL", "C1_LINE_PL", "N1_CONDITIONAL")
N2 = "N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"
WORLDS = ("W0", "W1", "W2", "W3", "W4")


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_rules() -> tuple[dict, dict, dict]:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_rule = json.loads(V1_PREREG.read_text(encoding="utf-8"))
    v6_rule = json.loads(V6_PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_BROAD_WORLD_SCORING":
        raise RuntimeError("invalid_prereg_status")
    if tuple(rule.get("worlds", [])) != WORLDS:
        raise RuntimeError("world_set_mismatch")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False or p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary_invalid")
    return rule, v1_rule, v6_rule


def evaluate_seed(seed: int, races: int, v1_rule: dict, v6_rule: dict) -> dict:
    scores = {world: {m: [] for m in (*LEGACY, N2)} for world in WORLDS}
    for idx in range(races):
        race = twin.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = twin.pre_view(race)
        frozen = diag.forecasts(pre, v1_rule)
        forecasts = {m: frozen[m] for m in LEGACY}
        forecasts[N2] = v6.n2_forecast(pre, v6_rule)
        for world in WORLDS:
            oracle = twin.world_joint_distribution(race, world)
            for model, joint in forecasts.items():
                _ce, kl = diag.top3_metrics(oracle, joint)
                scores[world][model].append(kl)

    worlds = {}
    for world in WORLDS:
        means = {m: mean(scores[world][m]) for m in (*LEGACY, N2)}
        best_legacy = min(LEGACY, key=lambda m: means[m])
        worlds[world] = {
            "mean_KL": means,
            "best_legacy": best_legacy,
            "best_legacy_KL": means[best_legacy],
            "N2_relative_to_best_legacy": means[N2] / means[best_legacy],
        }
    pooled = {m: mean([worlds[w]["mean_KL"][m] for w in WORLDS]) for m in (*LEGACY, N2)}
    best_pooled_legacy = min(LEGACY, key=lambda m: pooled[m])
    return {
        "seed": seed,
        "races": races,
        "worlds": worlds,
        "equal_weight_pooled_mean_KL": pooled,
        "best_single_legacy_pooled": best_pooled_legacy,
        "best_single_legacy_pooled_KL": pooled[best_pooled_legacy],
        "N2_relative_to_best_single_legacy_pooled": pooled[N2] / pooled[best_pooled_legacy],
    }


def decide(results: list[dict]) -> dict:
    core_passes = []
    stress_passes = []
    pooled_passes = []
    for r in results:
        core_passes.append(all(r["worlds"][w]["N2_relative_to_best_legacy"] <= 1.0 for w in ("W0", "W1", "W2")))
        stress_passes.append(all(r["worlds"][w]["N2_relative_to_best_legacy"] <= 1.05 for w in ("W3", "W4")))
        pooled_passes.append(r["N2_relative_to_best_single_legacy_pooled"] <= 0.98)
    passed = all(core_passes) and all(stress_passes) and all(pooled_passes)
    return {
        "core_W0_W2_seed_passes": core_passes,
        "stress_W3_W4_seed_passes": stress_passes,
        "pooled_seed_passes": pooled_passes,
        "broad_robust_pass": passed,
        "classification": "N2_BROADLY_ROBUST_W0_W4_SYNTHETIC" if passed else "N2_NOT_BROADLY_ROBUST_W0_W4",
    }


def main() -> int:
    rule, v1_rule, v6_rule = load_rules()
    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_N2_BROAD_WORLD_ROBUSTNESS_GOVERNANCE_AUDIT_v9",
        "status": "PASS_SYNTHETIC_ONLY",
        "evidence_class": rule["evidence_class"],
        "prediction_inputs": "PRE_ONLY",
        "oracle_used_for_prediction": False,
        "world_label_used_for_prediction": False,
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
    results = [evaluate_seed(int(c["seed"]), int(c["races"]), v1_rule, v6_rule) for c in rule["batches"]]
    decision = decide(results)
    payload = {
        "record": "KEIRIN_SYNTHETIC_N2_BROAD_WORLD_ROBUSTNESS_RESULT_v9",
        "status": "COMPLETE_SYNTHETIC_BROAD_WORLD_ROBUSTNESS_AUDIT",
        "evidence_class": rule["evidence_class"],
        "results": results,
        "decision": decision,
        "model_promotion": False,
        "real_world_claim": False,
        "next_action": (
            "Synthetic evidence supports N2 as a broad engineering candidate; any transition to real/historical evidence requires a separate governed Owner Gate."
            if decision["broad_robust_pass"]
            else "Preregister a fixed robust-combination experiment across exposed synthetic W0-W4 with disjoint design/evaluation seeds; do not change N2 in place."
        ),
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("01_RESULT.json", payload)
    print(json.dumps({"status": payload["status"], "classification": decision["classification"], "runtime": "OFF", "automatic_betting": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
