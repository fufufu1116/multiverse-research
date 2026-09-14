from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean

import digital_twin_v1 as twin
from top3_architecture_core_v1 import conditional_top3_from_context_logits, pl_top3_from_runner_utilities

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SYNTHETIC_DEV2000_AVAILABLE_SIBLING_ABLATION_PREREG_20260914_v1.json"
OUT = ROOT / "research_candidates" / "synthetic_dev2000_available_sibling_ablation_v1"
EPS = 1e-15


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def forecast(race: twin.Race, cfg: dict, variant: str) -> dict:
    shrink = float(cfg["posterior_score_shrinkage"])
    cls = cfg["class"]
    sty = cfg["style"]
    rel = cfg["conditional_relation"]
    use_group = variant not in {"ABLATE_LINE_GROUP_ID", "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"}
    use_pos = variant not in {"ABLATE_LINE_POSITION", "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"}
    use_size = variant not in {"ABLATE_LINE_SIZE", "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"}
    use_bank = variant not in {"ABLATE_BANK_LENGTH_M", "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"}
    use_wind = variant not in {"ABLATE_WIND_SPEED_MPS", "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"}

    riders = {r.car_no: r for r in race.riders}
    cars = sorted(riders)
    posterior = {c: shrink * float(riders[c].observed_score) for c in cars}

    line_mean = {}
    if use_group:
        grouped = {}
        for c in cars:
            grouped.setdefault(riders[c].line_id, []).append(posterior[c])
        line_mean = {k: mean(v) for k, v in grouped.items()}

    base = {}
    for c in cars:
        r = riders[c]
        value = posterior[c] + float(cls[r.rider_class]) + float(sty[r.style])
        if use_wind:
            mult = 1.0 if r.style == "逃" else float(cfg["wind_penalty_other_style_multiplier"])
            value -= float(cfg["wind_penalty_self_power_head_style"]) * float(race.wind_speed_mps) * mult
        if use_bank and race.bank_length_m <= 333 and r.style in {"逃", "両"}:
            value += float(cfg["short_bank_self_power_bonus"])
        if use_group:
            value += float(cfg["line_strength"]) * line_mean[r.line_id]
        if use_pos:
            value += float(cfg["line_position"].get(str(r.line_position), 0.0))
        if use_size:
            value += float(cfg["line_size_per_extra"]) * max(0, r.line_size - 1)
        base[c] = value

    if variant == "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL":
        return pl_top3_from_runner_utilities(base)

    p2 = {}
    p3 = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = use_group and rc.line_id == rf.line_id
            follower = same and use_pos and rc.line_position == rf.line_position + 1
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
                same_f = use_group and rc.line_id == rf.line_id
                same_s = use_group and rc.line_id == rs.line_id
                chain = (
                    use_group
                    and use_pos
                    and rf.line_id == rs.line_id == rc.line_id
                    and rf.line_position < rs.line_position < rc.line_position
                )
                p3[(first, second, candidate)] = (
                    base[candidate]
                    + float(rel["p3_same_as_first"]) * float(same_f)
                    + float(rel["p3_same_as_second"]) * float(same_s)
                    + float(rel["p3_ordered_line_chain"]) * float(chain)
                )
    return conditional_top3_from_context_logits(base, p2, p3)


def kl_metric(oracle: dict, pred: dict) -> float:
    value = 0.0
    for key, q in oracle.items():
        p = max(float(pred[key]), EPS)
        qf = float(q)
        if qf > 0.0:
            value += qf * math.log(qf / p)
    return value


def main() -> int:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_SCORING":
        raise RuntimeError("invalid_prereg_status")
    p = rule["protected_boundaries"]
    if p["real_historical_input"] is not False or p["real_PRE_row_values"] is not False:
        raise RuntimeError("real_input_boundary_invalid")
    if p["RESULT_PAYOUT"] != "NOT_ACCESSED" or p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("runtime_boundary_invalid")

    worlds = rule["worlds"]
    models = rule["models"]
    cfg = rule["fixed_coefficients"]
    batches = []
    for batch in rule["batches"]:
        seed = int(batch["seed"])
        n = int(batch["races_per_world"])
        by_world = {}
        for world in worlds:
            acc = {m: [] for m in models}
            for idx in range(n):
                race = twin.generate_race(seed=seed, race_index=idx, event_format="STANDARD_FI_FII_7")
                oracle = twin.world_joint_distribution(race, world)
                for model in models:
                    acc[model].append(kl_metric(oracle, forecast(race, cfg, model)))
            means = {m: mean(acc[m]) for m in models}
            full = means["N2_FULL_FROZEN"]
            ratios = {m: means[m] / full for m in models if m != "N2_FULL_FROZEN"}
            by_world[world] = {"mean_KL": means, "ratio_to_N2_FULL": ratios}
        batches.append({"seed": seed, "races_per_world": n, "worlds": by_world})

    mapping = {
        "line_group_id": "ABLATE_LINE_GROUP_ID",
        "line_position": "ABLATE_LINE_POSITION",
        "line_size": "ABLATE_LINE_SIZE",
        "bank_length_m": "ABLATE_BANK_LENGTH_M",
        "wind_speed_mps": "ABLATE_WIND_SPEED_MPS",
    }
    dependence = {}
    for field, model in mapping.items():
        dependence[field] = {}
        for world in worlds:
            ratios = [b["worlds"][world]["ratio_to_N2_FULL"][model] for b in batches]
            dependence[field][world] = {"ratios": ratios, "material_both_seeds": all(x >= 1.10 for x in ratios)}

    sibling = "S0_DEV2000_AVAILABLE_SCORE_CLASS_STYLE_PL"
    sibling_ratios = {w: [b["worlds"][w]["ratio_to_N2_FULL"][sibling] for b in batches] for w in worlds}
    broad = all(all(x <= 1.25 for x in sibling_ratios[w]) for w in worlds)
    partial = (
        all(x <= 1.15 for x in sibling_ratios["W0"])
        and all(x <= 1.35 for x in sibling_ratios["W3"])
        and all(x <= 1.35 for x in sibling_ratios["W4"])
    )
    if broad:
        classification = "S0_BROAD_SYNTHETIC_VIABLE"
    elif partial:
        classification = "S0_PARTIAL_SYNTHETIC_VIABLE_CONTEXT_DEPENDENT"
    else:
        classification = "S0_SYNTHETIC_NOT_VIABLE_AS_N2_REPLACEMENT"

    result = {
        "record": "KEIRIN_SYNTHETIC_DEV2000_AVAILABLE_SIBLING_ABLATION_RESULT_v1",
        "status": "COMPLETE_SYNTHETIC_ABLATION",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "batches": batches,
        "field_dependence": dependence,
        "sibling_ratios_to_N2_FULL": sibling_ratios,
        "decision": {"broad_synthetic_viability": broad, "partial_synthetic_viability": partial, "classification": classification},
        "frozen_N2_unchanged": True,
        "model_promotion": False,
        "real_world_claim": False,
        "protected_boundaries": p,
    }
    dump("00_GOVERNANCE_AUDIT.json", {
        "status": "PASS_SYNTHETIC_ONLY",
        "real_historical_input": False,
        "real_PRE_row_values": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "runtime": "OFF",
        "automatic_betting": False,
        "frozen_N2_unchanged": True,
    })
    dump("01_RESULT.json", result)
    print(json.dumps({"status": result["status"], "classification": classification, "runtime": "OFF", "automatic_betting": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
