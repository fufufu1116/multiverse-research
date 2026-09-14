from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean

import digital_twin_v1 as twin
from top3_architecture_core_v1 import conditional_top3_from_context_logits, pl_top3_from_runner_utilities

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREREG = ROOT / "research_candidates" / "KEIRIN_SOURCE_WIDE_SIBLING_SYNTHETIC_PREREG_20260914_v1.json"
OUT = ROOT / "research_candidates" / "source_wide_sibling_synthetic_selection_v1"
EPS = 1e-15

SHRINK = 0.7677543186180422
CLASS_COEF = {"A1": 0.05, "A2": -0.03, "A3": 0.0, "S1": 0.08, "S2": -0.03}
STYLE_COEF = {"逃": 0.06, "両": 0.04, "追": 0.0}
LINE_POSITION = {0: 0.04, 1: 0.10, 2: 0.05}


def dump(name: str, obj: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def n2_forecast(race: twin.Race) -> dict:
    riders = {r.car_no: r for r in race.riders}
    cars = sorted(riders)
    posterior = {c: SHRINK * float(riders[c].observed_score) for c in cars}
    grouped = {}
    for c in cars:
        grouped.setdefault(riders[c].line_id, []).append(posterior[c])
    line_mean = {k: mean(v) for k, v in grouped.items()}
    base = {}
    for c in cars:
        r = riders[c]
        value = posterior[c] + CLASS_COEF[r.rider_class] + STYLE_COEF[r.style]
        mult = 1.0 if r.style == "逃" else 0.25
        value -= 0.035 * float(race.wind_speed_mps) * mult
        if race.bank_length_m <= 333 and r.style in {"逃", "両"}:
            value += 0.04
        value += 0.16 * line_mean[r.line_id]
        value += LINE_POSITION.get(r.line_position, 0.0)
        value += 0.025 * max(0, r.line_size - 1)
        base[c] = value
    p2 = {}
    p3 = {}
    for first in cars:
        rf = riders[first]
        for candidate in cars:
            if candidate == first:
                continue
            rc = riders[candidate]
            same = rc.line_id == rf.line_id
            follower = same and rc.line_position == rf.line_position + 1
            p2[(first, candidate)] = base[candidate] + 0.30 * float(same) + 0.28 * float(follower)
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
                same_f = rc.line_id == rf.line_id
                same_s = rc.line_id == rs.line_id
                chain = rf.line_id == rs.line_id == rc.line_id and rf.line_position < rs.line_position < rc.line_position
                p3[(first, second, candidate)] = base[candidate] + 0.17 * float(same_f) + 0.14 * float(same_s) + 0.30 * float(chain)
    return conditional_top3_from_context_logits(base, p2, p3)


def candidate_forecast(race: twin.Race, candidate: str) -> dict:
    util = {}
    for r in race.riders:
        value = SHRINK * float(r.observed_score)
        if candidate == "SW1_SCORE_STYLE_PL":
            value += STYLE_COEF[r.style]
        elif candidate != "SW0_SCORE_ONLY_PL":
            raise ValueError(candidate)
        util[r.car_no] = value
    return pl_top3_from_runner_utilities(util)


def kl_metric(oracle: dict, pred: dict) -> float:
    value = 0.0
    for key, q in oracle.items():
        p = max(float(pred[key]), EPS)
        qf = float(q)
        if qf > 0.0:
            value += qf * math.log(qf / p)
    return value


def sanity(pred: dict) -> dict:
    vals = list(pred.values())
    return {
        "finite": all(math.isfinite(float(x)) for x in vals),
        "nonnegative": all(float(x) >= 0.0 for x in vals),
        "mass_error": abs(sum(float(x) for x in vals) - 1.0),
    }


def format_for_n(n: int) -> str:
    if n == 7:
        return "STANDARD_FI_FII_7"
    if n == 9:
        return "SPECIAL_9"
    return "CUSTOM_TEST_FIXTURE"


def main() -> int:
    rule = json.loads(PREREG.read_text(encoding="utf-8"))
    if rule.get("status") != "PREREGISTERED_BEFORE_SYNTHETIC_CANDIDATE_SCORING":
        raise RuntimeError("invalid_prereg_status")
    p = rule["protected_boundaries"]
    if p["real_PRE_row_values_during_synthetic_selection"] is not False:
        raise RuntimeError("real_pre_boundary_invalid")
    if p["RESULT_PAYOUT"] != "NOT_ACCESSED" or p["ECON_HOLDOUT1000"] != "SEALED_NOT_ACCESSED":
        raise RuntimeError("protected_boundary_invalid")
    if p["runtime"] != "OFF" or p["automatic_betting"] is not False:
        raise RuntimeError("runtime_boundary_invalid")

    candidates = [x["name"] for x in rule["candidate_family"]]
    cells = []
    aggregate_kl = {c: [] for c in candidates}
    worst_ratio = {c: 0.0 for c in candidates}
    sane = {c: True for c in candidates}

    for batch in rule["synthetic_batches"]:
        seed = int(batch["seed"])
        n_races = int(batch["races_per_world_field_size"])
        for n in rule["field_sizes"]:
            n = int(n)
            event_format = format_for_n(n)
            for world in rule["worlds"]:
                n2_vals = []
                cand_vals = {c: [] for c in candidates}
                cell_mass_error = {c: 0.0 for c in candidates}
                for idx in range(n_races):
                    race = twin.generate_race(seed=seed, race_index=idx, n_riders=n, event_format=event_format)
                    oracle = twin.world_joint_distribution(race, world)
                    n2_pred = n2_forecast(race)
                    n2_vals.append(kl_metric(oracle, n2_pred))
                    for c in candidates:
                        pred = candidate_forecast(race, c)
                        s = sanity(pred)
                        sane[c] = sane[c] and s["finite"] and s["nonnegative"] and s["mass_error"] <= 1e-10
                        cell_mass_error[c] = max(cell_mass_error[c], s["mass_error"])
                        cand_vals[c].append(kl_metric(oracle, pred))
                n2_mean = mean(n2_vals)
                means = {c: mean(cand_vals[c]) for c in candidates}
                ratios = {c: means[c] / n2_mean for c in candidates}
                for c in candidates:
                    aggregate_kl[c].extend(cand_vals[c])
                    worst_ratio[c] = max(worst_ratio[c], ratios[c])
                cells.append({
                    "seed": seed,
                    "field_size": n,
                    "world": world,
                    "n_races": n_races,
                    "n2_mean_KL": n2_mean,
                    "candidate_mean_KL": means,
                    "ratio_to_N2": ratios,
                    "max_probability_mass_error": cell_mass_error,
                })

    overall = {c: mean(aggregate_kl[c]) for c in candidates}
    eligible = [c for c in candidates if sane[c] and worst_ratio[c] <= 1.35]
    selected = None
    if eligible:
        eligible = sorted(eligible, key=lambda c: (worst_ratio[c], overall[c], 0 if c == "SW0_SCORE_ONLY_PL" else 1))
        selected = eligible[0]
        if len(eligible) > 1:
            a, b = eligible[0], eligible[1]
            if abs(worst_ratio[a] - worst_ratio[b]) <= 0.005:
                rel = abs(overall[a] - overall[b]) / max(min(overall[a], overall[b]), EPS)
                if rel <= 0.005:
                    selected = "SW0_SCORE_ONLY_PL" if "SW0_SCORE_ONLY_PL" in eligible else a
                else:
                    selected = min([a, b], key=lambda c: overall[c])

    result = {
        "record": "KEIRIN_SOURCE_WIDE_SIBLING_SYNTHETIC_RESULT_v1",
        "status": "COMPLETE_SYNTHETIC_SELECTION" if selected else "NO_ELIGIBLE_SOURCE_WIDE_CANDIDATE_STOP",
        "evidence_class": "SYNTHETIC_ENGINEERING_SOURCE_WIDE_INTERFACE_SELECTION_ONLY",
        "cells": cells,
        "candidate_summary": {
            c: {
                "overall_mean_KL": overall[c],
                "worst_cell_ratio_to_N2": worst_ratio[c],
                "all_probability_sanity_pass": sane[c],
                "eligible": c in eligible,
            }
            for c in candidates
        },
        "decision": {
            "selected": selected,
            "classification": "SOURCE_WIDE_SYNTHETIC_SIBLING_SELECTED_AND_FROZEN" if selected else "NO_SOURCE_WIDE_SYNTHETIC_SIBLING_SELECTED"
        },
        "frozen_N2_unchanged": True,
        "frozen_S0_unchanged": True,
        "real_world_predictive_claim": False,
        "model_promotion": False,
        "protected_boundaries": p,
    }
    dump("00_GOVERNANCE_AUDIT.json", {
        "status": "PASS_SYNTHETIC_ONLY",
        "real_PRE_row_values": False,
        "RESULT_PAYOUT": "NOT_ACCESSED",
        "ECON_HOLDOUT1000": "SEALED_NOT_ACCESSED",
        "runtime": "OFF",
        "automatic_betting": False,
        "frozen_N2_unchanged": True,
        "frozen_S0_unchanged": True,
    })
    dump("01_RESULT.json", result)
    if selected:
        dump("02_FROZEN_CANDIDATE.json", {
            "record": "KEIRIN_SOURCE_WIDE_SYNTHETIC_SIBLING_FROZEN_v1",
            "name": selected,
            "status": "FROZEN_AFTER_SYNTHETIC_SELECTION_NOT_PROMOTED",
            "score_shrinkage": SHRINK,
            "style_coefficients": STYLE_COEF if selected == "SW1_SCORE_STYLE_PL" else None,
            "class_dependency": False,
            "field_size_support": "ANY_N_GE_3",
            "probability_family": "Plackett-Luce ordered top3",
            "real_PRE_fit": False,
            "model_promotion": False,
        })
    print(json.dumps({"status": result["status"], "selected": selected, "worst_ratio": worst_ratio, "overall_mean_KL": overall}, sort_keys=True))
    return 0 if selected else 2


if __name__ == "__main__":
    raise SystemExit(main())
