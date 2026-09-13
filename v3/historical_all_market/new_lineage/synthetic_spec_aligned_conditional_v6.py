from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import digital_twin_learnable_regime_v2 as twin2
import digital_twin_v1 as twin1
import synthetic_market_probability_diagnostic_v1 as diag
from top3_architecture_core_v1 import conditional_top3_from_context_logits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_SPEC_ALIGNED_CONDITIONAL_PREREG_20260914_v6.json"
V1_PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_MARKET_PROBABILITY_DIAGNOSTIC_PREREG_20260913_v1.json"
OUT = ROOT / "research_candidates" / "synthetic_spec_aligned_conditional_v6"


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
    if p["real_historical_input"] is not False or p["RESULT_PAYOUT"] != "NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("holdout_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("authority_boundary_invalid")
    return rule, v1_rule


def n2_forecast(pre: dict, rule: dict) -> dict:
    cfg = rule["component"]
    shrink = float(cfg["posterior_score_shrinkage"])
    coeff = cfg["base_utility_coefficients"]
    rel = cfg["conditional_relation_coefficients"]
    riders = {int(r["car_no"]): r for r in pre["riders"]}
    cars = sorted(riders)

    posterior_latent = {
        car: shrink * float(riders[car]["score"])
        for car in cars
    }
    line_values = defaultdict(list)
    for car in cars:
        line_values[int(riders[car]["line_group_id"])].append(posterior_latent[car])
    line_mean = {line: mean(vals) for line, vals in line_values.items()}

    base = {}
    wind = float(pre["wind_speed_mps"])
    bank = float(pre["bank_length_m"])
    for car in cars:
        r = riders[car]
        style = str(r["style"])
        pos = int(r["line_position"])
        size = int(r["line_size"])
        line_id = int(r["line_group_id"])
        value = posterior_latent[car]
        value += float(coeff["class"][str(r["class"])])
        value += float(coeff["style"][style])
        style_mult = 1.0 if style == "逃" else float(coeff["wind_penalty_other_style_multiplier"])
        value -= float(coeff["wind_penalty_self_power_head_style"]) * wind * style_mult
        if bank <= 333.0 and style in {"逃", "両"}:
            value += float(coeff["short_bank_self_power_bonus"])
        value += float(coeff["line_strength"]) * line_mean[line_id]
        value += float(coeff["line_position"].get(str(pos), 0.0))
        value += float(coeff["line_size_per_extra"]) * max(0, size - 1)
        base[car] = value

    p2 = {}
    p3 = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = int(rc["line_group_id"]) == int(rf["line_group_id"])
            follower = same and int(rc["line_position"]) == int(rf["line_position"]) + 1
            p2[(first, candidate)] = (
                base[candidate]
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
                    base[candidate]
                    + float(rel["p3_same_as_first"]) * float(same_f)
                    + float(rel["p3_same_as_second"]) * float(same_s)
                    + float(rel["p3_ordered_line_chain"]) * float(chain)
                )

    return conditional_top3_from_context_logits(base, p2, p3)


def evaluate_seed(seed: int, races: int, rule: dict, v1_rule: dict) -> dict:
    model_names = ("C0_SCORE_PL", "N1_CONDITIONAL", "N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL")
    all_kl = {m: [] for m in model_names}
    stratum_kl = {m: defaultdict(list) for m in model_names}
    counts = Counter()

    for idx in range(races):
        race = twin1.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
        pre = twin1.pre_view(race)
        b = band(twin2.pre_mechanism_signal(pre))
        counts[b] += 1

        frozen = diag.forecasts(pre, v1_rule)
        forecasts = {
            "C0_SCORE_PL": frozen["C0_SCORE_PL"],
            "N1_CONDITIONAL": frozen["N1_CONDITIONAL"],
            "N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL": n2_forecast(pre, rule),
        }
        oracle = twin1.world_joint_distribution(race, "W2")
        for name, joint in forecasts.items():
            _ce, kl = diag.top3_metrics(oracle, joint)
            all_kl[name].append(kl)
            stratum_kl[name][b].append(kl)

    rows = {}
    for name in model_names:
        rows[name] = {
            "mean_KL": mean(all_kl[name]),
            "stratum_mean_KL": {
                b: mean(stratum_kl[name][b])
                for b in ("LOW", "MID", "HIGH")
                if stratum_kl[name][b]
            },
        }
    n2 = rows["N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"]
    n1 = rows["N1_CONDITIONAL"]
    c0 = rows["C0_SCORE_PL"]
    n2["relative_to_N1"] = n2["mean_KL"] / n1["mean_KL"]
    n2["relative_to_C0"] = n2["mean_KL"] / c0["mean_KL"]
    n2["stratum_relative_to_N1"] = {
        b: n2["stratum_mean_KL"][b] / n1["stratum_mean_KL"][b]
        for b in n2["stratum_mean_KL"]
    }
    return {
        "seed": seed,
        "races": races,
        "stratum_counts": dict(counts),
        "models": rows,
    }


def decide(results: list[dict], minimum_count: int) -> dict:
    overall_n1 = []
    overall_c0 = []
    strata = []
    for result in results:
        n2 = result["models"]["N2_SPEC_ALIGNED_POSTERIOR_CONDITIONAL"]
        overall_n1.append(n2["relative_to_N1"] <= 0.90)
        overall_c0.append(n2["relative_to_C0"] <= 0.90)
        ok = True
        for b in ("LOW", "MID", "HIGH"):
            if int(result["stratum_counts"].get(b, 0)) < minimum_count:
                ok = False
                continue
            if n2["stratum_relative_to_N1"][b] > 0.95:
                ok = False
        strata.append(ok)
    passed = all(overall_n1) and all(overall_c0) and all(strata)
    return {
        "N2_vs_N1_seed_passes": overall_n1,
        "N2_vs_C0_seed_passes": overall_c0,
        "N2_stratum_seed_passes": strata,
        "component_adequate": passed,
        "classification": (
            "N2_SPEC_ALIGNED_COMPONENT_ADEQUATE_FOR_W2"
            if passed
            else "N2_SPEC_ALIGNED_COMPONENT_NOT_ADEQUATE"
        ),
    }


def main() -> int:
    rule, v1_rule = load_rules()
    dump("00_GOVERNANCE_AUDIT.json", {
        "record": "KEIRIN_SYNTHETIC_SPEC_ALIGNED_CONDITIONAL_GOVERNANCE_AUDIT_v6",
        "status": "PASS_SYNTHETIC_ONLY",
        "evidence_class": rule["evidence_class"],
        "prediction_inputs": "PRE_ONLY",
        "latent_skill_used_for_prediction": False,
        "hidden_alpha_used_for_prediction": False,
        "oracle_used_for_prediction": False,
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
        evaluate_seed(int(cfg["seed"]), int(cfg["races"]), rule, v1_rule)
        for cfg in rule["batches"]
    ]
    decision = decide(results, int(rule["strata"]["minimum_count_per_seed"]))
    payload = {
        "record": "KEIRIN_SYNTHETIC_SPEC_ALIGNED_CONDITIONAL_RESULT_v6",
        "status": "COMPLETE_SYNTHETIC_COMPONENT_VALIDATION",
        "evidence_class": rule["evidence_class"],
        "results": results,
        "decision": decision,
        "model_promotion": False,
        "real_world_claim": False,
        "next_action": (
            "Preregister a new synthetic adaptive-mixture experiment using C0 and frozen N2; do not use N1 as the W2 component."
            if decision["component_adequate"]
            else "Do not revisit selector tuning; diagnose remaining W2 component misspecification in a separate preregistered experiment."
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
