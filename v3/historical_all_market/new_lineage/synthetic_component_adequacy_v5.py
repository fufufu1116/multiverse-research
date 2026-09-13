from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import digital_twin_learnable_regime_v2 as twin2
import digital_twin_v1 as twin1
import synthetic_market_probability_diagnostic_v1 as diag

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_COMPONENT_ADEQUACY_PREREG_20260914_v5.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
OUT = ROOT / "research_candidates" / "synthetic_component_adequacy_v5"

MODELS = ("C0_SCORE_PL", "C1_LINE_PL", "N1_CONDITIONAL")
WORLDS = ("W0", "W2")


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def band(signal: float) -> str:
    if signal < -0.35:
        return "LOW"
    if signal > 0.35:
        return "HIGH"
    return "MID"


def load_rules() -> tuple[dict, dict]:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    v1_rule = json.loads(V1_PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_COMPONENT_SCORING":
        raise RuntimeError("invalid_prereg_status")
    if rule.get("evidence_class") != "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY":
        raise RuntimeError("invalid_evidence_class")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False:
        raise RuntimeError("real_input_boundary")
    if p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("result_payout_boundary")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary")
    return rule, v1_rule


def evaluate_seed(seed: int, races: int, v1_rule: dict) -> dict:
    acc = {w: {m: [] for m in MODELS} for w in WORLDS}
    strata = {
        w: {m: defaultdict(list) for m in MODELS}
        for w in WORLDS
    }
    counts = Counter()

    for idx in range(races):
        race = twin1.generate_race(
            seed=seed,
            race_index=idx,
            event_format="STANDARD_FI_FII_7",
        )
        pre = twin1.pre_view(race)
        signal = twin2.pre_mechanism_signal(pre)
        b = band(signal)
        counts[b] += 1

        # Prediction objects are frozen from PRE before oracle scoring.
        forecasts = diag.forecasts(pre, v1_rule)

        for world in WORLDS:
            oracle = twin1.world_joint_distribution(race, world)
            for model in MODELS:
                _ce, kl = diag.top3_metrics(oracle, forecasts[model])
                acc[world][model].append(kl)
                strata[world][model][b].append(kl)

    summary = {"seed": seed, "races": races, "stratum_counts": dict(counts), "worlds": {}}
    for world in WORLDS:
        rows = {}
        for model in MODELS:
            rows[model] = {
                "mean_KL": mean(acc[world][model]),
                "stratum_mean_KL": {
                    b: mean(strata[world][model][b])
                    for b in ("LOW", "MID", "HIGH")
                    if strata[world][model][b]
                },
            }
        best_pl = min(rows["C0_SCORE_PL"]["mean_KL"], rows["C1_LINE_PL"]["mean_KL"])
        for model in MODELS:
            rows[model]["relative_to_best_PL"] = rows[model]["mean_KL"] / best_pl
            rows[model]["stratum_relative_to_best_PL"] = {}
            for b in ("LOW", "MID", "HIGH"):
                if b not in rows[model]["stratum_mean_KL"]:
                    continue
                bp = min(
                    rows["C0_SCORE_PL"]["stratum_mean_KL"][b],
                    rows["C1_LINE_PL"]["stratum_mean_KL"][b],
                )
                rows[model]["stratum_relative_to_best_PL"][b] = (
                    rows[model]["stratum_mean_KL"][b] / bp
                )
        summary["worlds"][world] = rows
    return summary


def decide(results: list[dict], minimum_count: int) -> dict:
    c0_w0_passes = []
    n1_overall_passes = []
    n1_stratum_passes = []

    for result in results:
        w0 = result["worlds"]["W0"]
        c0_w0_passes.append(
            w0["C0_SCORE_PL"]["mean_KL"]
            <= min(w0["C1_LINE_PL"]["mean_KL"], w0["N1_CONDITIONAL"]["mean_KL"])
        )

        w2 = result["worlds"]["W2"]
        n1 = w2["N1_CONDITIONAL"]
        n1_overall_passes.append(n1["relative_to_best_PL"] <= 0.95)

        seed_stratum_ok = True
        for b in ("LOW", "MID", "HIGH"):
            if int(result["stratum_counts"].get(b, 0)) < minimum_count:
                seed_stratum_ok = False
                continue
            ratio = n1["stratum_relative_to_best_PL"][b]
            if ratio > 1.02:
                seed_stratum_ok = False
        n1_stratum_passes.append(seed_stratum_ok)

    c0_ok = all(c0_w0_passes)
    n1_ok = all(n1_overall_passes) and all(n1_stratum_passes)
    classification = (
        "N1_COMPONENT_ADEQUATE_FOR_W2"
        if n1_ok
        else "N1_COMPONENT_INADEQUATE_FOR_W2_SPEC_ALIGNED_COMPONENT_REQUIRED"
    )
    return {
        "c0_W0_reference_adequate": c0_ok,
        "c0_W0_seed_passes": c0_w0_passes,
        "n1_W2_overall_seed_passes": n1_overall_passes,
        "n1_W2_stratum_seed_passes": n1_stratum_passes,
        "n1_W2_component_adequate": n1_ok,
        "classification": classification,
    }


def main() -> int:
    rule, v1_rule = load_rules()
    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_COMPONENT_ADEQUACY_GOVERNANCE_AUDIT_v5",
        "status": "PASS_SYNTHETIC_ONLY",
        "evidence_class": rule["evidence_class"],
        "prediction_inputs": "PRE_ONLY",
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

    results = [
        evaluate_seed(int(cfg["seed"]), int(cfg["races"]), v1_rule)
        for cfg in rule["batches"]
    ]
    decision = decide(results, int(rule["strata"]["minimum_count_per_seed"]))
    payload = {
        "record": "KEIRIN_SYNTHETIC_COMPONENT_ADEQUACY_RESULT_v5",
        "status": "COMPLETE_SYNTHETIC_COMPONENT_AUDIT",
        "evidence_class": rule["evidence_class"],
        "results": results,
        "decision": decision,
        "model_promotion": False,
        "real_world_claim": False,
        "next_action": (
            "Preregister a separate synthetic spec-aligned conditional-component development experiment; do not tune N1 in place."
            if not decision["n1_W2_component_adequate"]
            else "Only then may a separately preregistered selector/adaptive-mixture experiment be reconsidered."
        ),
        "protected_boundaries": rule["protected_boundaries"],
    }
    dump("01_RESULT.json", payload)
    print(json.dumps({
        "status": payload["status"],
        "classification": decision["classification"],
        "runtime": "OFF",
        "automatic_betting": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
