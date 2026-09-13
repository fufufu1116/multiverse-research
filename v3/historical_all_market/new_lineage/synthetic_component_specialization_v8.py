from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import digital_twin_learnable_regime_v2 as twin2
import digital_twin_v1 as twin1
import synthetic_market_probability_diagnostic_v1 as diag
import synthetic_spec_aligned_conditional_v6 as v6

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_COMPONENT_SPECIALIZATION_PREREG_20260914_v8.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
V6_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_SPEC_ALIGNED_CONDITIONAL_PREREG_20260914_v6.json"
OUT = ROOT / "research_candidates" / "synthetic_component_specialization_v8"

MODELS = ("C0_SCORE_PL", "N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL")
WORLDS = ("W0", "W2")


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def band(signal: float) -> str:
    if signal < -0.35:
        return "LOW"
    if signal > 0.35:
        return "HIGH"
    return "MID"


def load_rules() -> tuple[dict, dict, dict]:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_rule = json.loads(V1_PREREG.read_text(encoding="utf-8"))
    v6_rule = json.loads(V6_PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_COMPONENT_SCORING":
        raise RuntimeError("invalid_prereg_status")
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("invalid_evidence_class")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False or p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary_invalid")
    return rule, v1_rule, v6_rule


def evaluate_seed(seed: int, races: int, v1_rule: dict, v6_rule: dict) -> dict:
    acc = {w: {m: [] for m in MODELS} for w in WORLDS}
    stratum_acc = {w: {m: defaultdict(list) for m in MODELS} for w in WORLDS}
    counts = Counter()

    for idx in range(races):
        race = twin1.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = twin1.pre_view(race)
        b = band(twin2.pre_mechanism_signal(pre))
        counts[b] += 1

        # Build forecasts strictly from PRE before oracle scoring.
        c0 = diag.forecasts(pre, v1_rule)["C0_SCORE_PL"]
        n2 = v6.n2_forecast(pre, v6_rule)
        forecasts = {"C0_SCORE_PL": c0, "N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL": n2}

        for world in WORLDS:
            oracle = twin1.world_joint_distribution(race, world)
            for model, joint in forecasts.items():
                _ce, kl = diag.top3_metrics(oracle, joint)
                acc[world][model].append(kl)
                stratum_acc[world][model][b].append(kl)

    worlds = {}
    for world in WORLDS:
        rows = {}
        for model in MODELS:
            rows[model] = {
                "mean_KL": mean(acc[world][model]),
                "stratum_mean_KL": {
                    b: mean(stratum_acc[world][model][b])
                    for b in ("LOW", "MID", "HIGH")
                    if stratum_acc[world][model][b]
                },
            }
        n2 = rows["N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"]
        c0 = rows["C0_SCORE_PL"]
        n2["relative_to_C0"] = n2["mean_KL"] / c0["mean_KL"]
        n2["stratum_relative_to_C0"] = {
            b: n2["stratum_mean_KL"][b] / c0["stratum_mean_KL"][b]
            for b in n2["stratum_mean_KL"]
        }
        worlds[world] = rows
    return {"seed": seed, "races": races, "stratum_counts": dict(counts), "worlds": worlds}


def classify(results: list[dict]) -> dict:
    c0_w0_specialized = []
    n2_w0_dominates = []
    n2_w2_dominates = []
    for result in results:
        w0 = result["worlds"]["W0"]
        w2 = result["worlds"]["W2"]
        c0 = w0["C0_SCORE_PL"]["mean_KL"]
        n2_w0 = w0["N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"]["mean_KL"]
        c0_w2 = w2["C0_SCORE_PL"]["mean_KL"]
        n2_w2 = w2["N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"]["mean_KL"]
        c0_w0_specialized.append(c0 <= 0.95 * n2_w0)
        n2_w0_dominates.append(n2_w0 <= c0)
        n2_w2_dominates.append(n2_w2 <= 0.90 * c0_w2)

    if all(c0_w0_specialized) and all(n2_w2_dominates):
        classification = "CLEAN_SPECIALIZATION"
    elif all(n2_w0_dominates) and all(n2_w2_dominates):
        classification = "N2_DOMINATES_W0_W2"
    else:
        classification = "NO_CLEAN_COMPONENT_SPECIALIZATION"
    return {
        "classification": classification,
        "C0_W0_specialization_seed_passes": c0_w0_specialized,
        "N2_W0_dominance_seed_passes": n2_w0_dominates,
        "N2_W2_dominance_seed_passes": n2_w2_dominates,
    }


def main() -> int:
    rule, v1_rule, v6_rule = load_rules()
    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_COMPONENT_SPECIALIZATION_GOVERNANCE_AUDIT_v8",
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
    results = [evaluate_seed(int(cfg["seed"]), int(cfg["races"]), v1_rule, v6_rule) for cfg in rule["batches"]]
    decision = classify(results)
    payload = {
        "record": "KEIRIN_SYNTHETIC_COMPONENT_SPECIALIZATION_RESULT_v8",
        "status": "COMPLETE_SYNTHETIC_COMPONENT_SPECIALIZATION_AUDIT",
        "evidence_class": rule["evidence_class"],
        "results": results,
        "decision": decision,
        "model_promotion": False,
        "real_world_claim": False,
        "next_action": (
            "Preregister a broad W0-W4 synthetic robustness audit for frozen N2; adaptive selection is unnecessary for the current W0/W2 construction."
            if decision["classification"] == "N2_DOMINATES_W0_W2"
            else "Do not tune selector weights. Use the classification to define a separately preregistered component or twin-structure falsification experiment."
        ),
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("01_RESULT.json", payload)
    print(json.dumps({"status": payload["status"], "classification": decision["classification"], "runtime": "OFF", "automatic_betting": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
