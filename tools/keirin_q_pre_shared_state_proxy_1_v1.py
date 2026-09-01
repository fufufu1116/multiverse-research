#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import math
from pathlib import Path
import sys
from typing import Dict, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
NEW_LINEAGE = ROOT / "v3" / "historical_all_market" / "new_lineage"
ORACLE_EVIDENCE = ROOT / "v3" / "historical_all_market" / "research_candidates" / "KEIRIN_Q_ORACLE_SHARED_STATE_1_EVIDENCE_20260901_v1.json"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(NEW_LINEAGE))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base
import digital_twin_v1 as dt
from top3_architecture_core_v1 import pl_top3_from_runner_utilities

BLOCK_SEED_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128
WORLD = "W1"
MODELS = ("C1", "N1", "C1_PRE_LINE_MEAN_PROXY")
PROXY_COEF = 0.16
EXPECTED_PRIOR_N1_MINUS_C1 = -0.0011390944513660628
EXPECTED_ORACLE_MINUS_C1 = -0.016232235048840415
TOL = 1e-12
TOL_BASELINE = 2e-14
TOL_MASS = 1e-10


def _assert_pre_has_no_latent(pre: Mapping[str, object]) -> None:
    riders = pre.get("riders")
    if not isinstance(riders, list):
        raise AssertionError("invalid_PRE_riders")
    for rider in riders:
        if not isinstance(rider, dict):
            raise AssertionError("invalid_PRE_rider")
        if "latent_skill" in rider:
            raise AssertionError("latent_skill_leaked_into_PRE")


def _pre_line_means(pre: Mapping[str, object]) -> Dict[int, float]:
    groups: Dict[int, list[float]] = {}
    for rider in pre["riders"]:
        line_id = int(rider["line_group_id"])
        groups.setdefault(line_id, []).append(float(rider["score"]))
    return {line_id: sum(values) / len(values) for line_id, values in groups.items()}


def _c1_pre_line_mean_proxy(
    pre: Mapping[str, object],
    c1_params: Mapping[str, float],
    shrinkage: float,
) -> Dict[dt.Top3, float]:
    _assert_pre_has_no_latent(pre)
    ordinary_c1_util = base._c1_utilities(pre, c1_params, shrinkage)
    line_mean = _pre_line_means(pre)
    proxy_util: Dict[int, float] = {}
    for rider in pre["riders"]:
        car = int(rider["car_no"])
        line_id = int(rider["line_group_id"])
        proxy_util[car] = float(ordinary_c1_util[car]) + PROXY_COEF * float(line_mean[line_id])
    if set(proxy_util) != set(ordinary_c1_util):
        raise AssertionError("proxy_support_mismatch")
    return pl_top3_from_runner_utilities(proxy_util)


def _assert_proxy_source_boundary() -> None:
    source = inspect.getsource(_c1_pre_line_mean_proxy)
    forbidden = ("latent_skill", "world_joint_distribution", "_static_utilities", "_line_strengths")
    hits = [token for token in forbidden if token in source]
    if hits:
        raise AssertionError(f"proxy_forbidden_source_reference:{hits}")
    if "line_group_id" not in source:
        raise AssertionError("proxy_missing_line_group_id")
    if "_pre_line_means" not in source:
        raise AssertionError("proxy_missing_PRE_line_mean_path")
    helper = inspect.getsource(_pre_line_means)
    if "latent_skill" in helper or "world_joint_distribution" in helper:
        raise AssertionError("proxy_helper_forbidden_source_reference")
    required = ("score", "line_group_id")
    if any(token not in helper for token in required):
        raise AssertionError("proxy_helper_missing_required_PRE_fields")


def _assert_probability_object(name: str, pred: Mapping[dt.Top3, float], support: set[dt.Top3]) -> float:
    if set(pred) != support:
        raise AssertionError(f"support_mismatch:{name}")
    mass_error = abs(sum(float(p) for p in pred.values()) - 1.0)
    if mass_error > TOL_MASS:
        raise AssertionError(f"mass_mismatch:{name}:{mass_error}")
    if any(not math.isfinite(float(p)) or float(p) < 0.0 for p in pred.values()):
        raise AssertionError(f"invalid_probability:{name}")
    return mass_error


def _expected_log_loss(truth: Mapping[dt.Top3, float], pred: Mapping[dt.Top3, float]) -> float:
    eps = 1e-300
    return -sum(float(q) * math.log(max(eps, float(pred[key]))) for key, q in truth.items())


def _chain_cross_entropy(truth: Mapping[dt.Top3, float], pred: Mapping[dt.Top3, float]) -> Dict[str, float]:
    eps = 1e-300
    p1: Dict[int, float] = {}
    p12: Dict[tuple[int, int], float] = {}
    for (i, j, _k), p in pred.items():
        p1[i] = p1.get(i, 0.0) + float(p)
        p12[(i, j)] = p12.get((i, j), 0.0) + float(p)
    rank1 = rank2 = rank3 = 0.0
    for (i, j, k), q_raw in truth.items():
        q = float(q_raw)
        p1_i = max(eps, p1[i])
        p12_ij = max(eps, p12[(i, j)])
        rank1 -= q * math.log(p1_i)
        rank2 -= q * math.log(max(eps, p12_ij / p1_i))
        rank3 -= q * math.log(max(eps, float(pred[(i, j, k)]) / p12_ij))
    return {"rank1": rank1, "rank2": rank2, "rank3": rank3, "total": rank1 + rank2 + rank3}


def _max_prediction_diff(a: Mapping[dt.Top3, float], b: Mapping[dt.Top3, float]) -> float:
    if set(a) != set(b):
        raise AssertionError("prediction_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


def _direct_line_mean_sanity(pre: Mapping[str, object], computed: Mapping[int, float]) -> float:
    groups: Dict[int, list[float]] = {}
    for rider in pre["riders"]:
        groups.setdefault(int(rider["line_group_id"]), []).append(float(rider["score"]))
    direct = {g: sum(v) / len(v) for g, v in groups.items()}
    if set(direct) != set(computed):
        raise AssertionError("line_mean_support_mismatch")
    return max(abs(direct[g] - float(computed[g])) for g in direct)


def _primary_classification(c1: float, n1: float, proxy: float) -> str:
    if proxy <= n1 + TOL:
        return "PROXY_BEATS_OR_TIES_N1"
    if proxy < c1 - TOL and proxy > n1 + TOL:
        return "PROXY_IMPROVES_C1_BUT_N1_REMAINS_BETTER"
    return "PROXY_DOES_NOT_IMPROVE_C1"


def _materiality_label(recovery_fraction: float) -> str:
    if recovery_fraction >= 0.25:
        return "MATERIAL_ORACLE_VALUE_RECOVERY"
    if recovery_fraction > 0.0:
        return "LIMITED_ORACLE_VALUE_RECOVERY"
    return "NO_OR_NEGATIVE_ORACLE_VALUE_RECOVERY"


def main() -> None:
    _assert_proxy_source_boundary()
    oracle_evidence = json.loads(ORACLE_EVIDENCE.read_text(encoding="utf-8"))
    if oracle_evidence.get("status") != "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS_STRONG_SYNTHETIC_SUPPORT":
        raise AssertionError("oracle_reference_status_drift")
    observed_oracle_delta = float(oracle_evidence["aggregate_deltas_lower_is_better"]["C1_ORACLE_minus_C1"]["total"])
    if abs(observed_oracle_delta - EXPECTED_ORACLE_MINUS_C1) > TOL:
        raise AssertionError("oracle_reference_numeric_drift")

    frozen = base._load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"]:
        raise AssertionError("C1_N1_base_parameter_drift")
    if c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_shrinkage_drift")

    aggregate = {m: {k: 0.0 for k in ("rank1", "rank2", "rank3", "total")} for m in MODELS}
    block_results: Dict[str, object] = {}
    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_chain_residual = 0.0
    max_c1_repro = 0.0
    max_n1_repro = 0.0
    max_line_mean_sanity = 0.0

    for block_seed in BLOCK_SEED_BASES:
        block = {m: {k: 0.0 for k in ("rank1", "rank2", "rank3", "total")} for m in MODELS}
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = dt.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block_seed}:{case}")
            pre = dt.pre_view(race)
            _assert_pre_has_no_latent(pre)
            line_means = _pre_line_means(pre)
            max_line_mean_sanity = max(max_line_mean_sanity, _direct_line_mean_sanity(pre, line_means))

            c1 = base._c1(pre, c1_params, c1_shrinkage)
            n1 = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            proxy = _c1_pre_line_mean_proxy(pre, c1_params, c1_shrinkage)
            c1_repeat = base._c1(pre, c1_params, c1_shrinkage)
            n1_repeat = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            max_c1_repro = max(max_c1_repro, _max_prediction_diff(c1, c1_repeat))
            max_n1_repro = max(max_n1_repro, _max_prediction_diff(n1, n1_repeat))

            truth = dt.world_joint_distribution(race, WORLD)
            support = set(truth)
            truth_mass_error = abs(sum(float(q) for q in truth.values()) - 1.0)
            max_truth_mass_error = max(max_truth_mass_error, truth_mass_error)
            if truth_mass_error > TOL_MASS:
                raise AssertionError("truth_mass_mismatch")

            predictions = {"C1": c1, "N1": n1, "C1_PRE_LINE_MEAN_PROXY": proxy}
            for model, pred in predictions.items():
                max_prediction_mass_error = max(max_prediction_mass_error, _assert_probability_object(model, pred, support))
                chain = _chain_cross_entropy(truth, pred)
                direct = _expected_log_loss(truth, pred)
                residual = abs(chain["total"] - direct)
                max_chain_residual = max(max_chain_residual, residual)
                if residual > TOL:
                    raise AssertionError(f"chain_residual:{model}:{residual}")
                for metric in ("rank1", "rank2", "rank3", "total"):
                    block[model][metric] += float(chain[metric])
                    aggregate[model][metric] += float(chain[metric])

        block_means = {m: {k: v / CASES_PER_BLOCK for k, v in vals.items()} for m, vals in block.items()}
        c1_loss = block_means["C1"]["total"]
        n1_loss = block_means["N1"]["total"]
        proxy_loss = block_means["C1_PRE_LINE_MEAN_PROXY"]["total"]
        recovery = max(0.0, min(1.0, (c1_loss - proxy_loss) / abs(EXPECTED_ORACLE_MINUS_C1)))
        block_results[str(block_seed)] = {
            "model_chain_cross_entropy": block_means,
            "N1_minus_C1": n1_loss - c1_loss,
            "C1_PRE_LINE_MEAN_PROXY_minus_C1": proxy_loss - c1_loss,
            "N1_minus_C1_PRE_LINE_MEAN_PROXY": n1_loss - proxy_loss,
            "proxy_recovery_fraction_vs_aggregate_oracle_gain_reference": recovery,
            "classification": _primary_classification(c1_loss, n1_loss, proxy_loss),
        }

    total_cases = len(BLOCK_SEED_BASES) * CASES_PER_BLOCK
    means = {m: {k: v / total_cases for k, v in vals.items()} for m, vals in aggregate.items()}
    c1_loss = means["C1"]["total"]
    n1_loss = means["N1"]["total"]
    proxy_loss = means["C1_PRE_LINE_MEAN_PROXY"]["total"]
    baseline = n1_loss - c1_loss
    baseline_error = abs(baseline - EXPECTED_PRIOR_N1_MINUS_C1)
    if baseline_error > TOL_BASELINE:
        raise AssertionError(f"prior_W1_baseline_not_reproduced:{baseline}:{baseline_error}")

    proxy_delta = proxy_loss - c1_loss
    n1_minus_proxy = n1_loss - proxy_loss
    recovery_fraction = max(0.0, min(1.0, (c1_loss - proxy_loss) / abs(EXPECTED_ORACLE_MINUS_C1)))
    primary = _primary_classification(c1_loss, n1_loss, proxy_loss)
    materiality = _materiality_label(recovery_fraction)

    result = {
        "record": "KEIRIN_Q_PRE_SHARED_STATE_PROXY_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "world": WORLD,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "primary_classification": primary,
        "materiality_label": materiality,
        "proxy_recovery_fraction": recovery_fraction,
        "aggregate_model_chain_cross_entropy": means,
        "aggregate_deltas": {
            "N1_minus_C1": baseline,
            "C1_PRE_LINE_MEAN_PROXY_minus_C1": proxy_delta,
            "N1_minus_C1_PRE_LINE_MEAN_PROXY": n1_minus_proxy,
        },
        "oracle_reference": {
            "C1_ORACLE_minus_C1": observed_oracle_delta,
            "oracle_rerun": False,
        },
        "block_results": block_results,
        "proxy_control": {
            "id": "C1_PRE_LINE_MEAN_PROXY",
            "formal_model_candidate": False,
            "PRE_only": True,
            "coefficient": PROXY_COEF,
            "coefficient_fitted": False,
            "coefficient_swept": False,
            "latent_skill_access": False,
            "truth_distribution_access_by_control": False,
            "normal_C1_or_N1_source_mutated": False,
        },
        "mechanical_checks": {
            "proxy_source_boundary_pass": True,
            "PRE_latent_skill_absent": True,
            "max_line_mean_score_sanity_diff": max_line_mean_sanity,
            "max_nonoracle_C1_reproduction_diff": max_c1_repro,
            "max_nonoracle_N1_reproduction_diff": max_n1_repro,
            "max_prediction_probability_mass_error": max_prediction_mass_error,
            "max_truth_probability_mass_error": max_truth_mass_error,
            "max_chain_decomposition_residual": max_chain_residual,
            "prior_W1_N1_minus_C1_reproduction_error": baseline_error,
        },
        "new_seed_selection": False,
        "result_adaptive_condition_selection": False,
        "post_result_retuning": False,
        "models_or_frozen_coefficients_changed": False,
        "authorization_auto_expanded": False,
        "protected_or_quarantined_input_access": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "econ_holdout1000_access": False,
        "dev2000_c_rescue": False,
        "same_lineage_b_c_rescue_tuning": False,
        "real_or_untouched_validation": False,
        "real_live_input_collection": False,
        "economics_bankroll_roi": False,
        "model_promotion_or_freeze": False,
        "external_provider_contact": False,
        "core_phase_c_main_ruleset_runtime_production_authority_change": False,
        "real_world_edge_or_roi_evidence": False,
        "scientific_segment_c_scoring_count": 0,
        "scientific_decision": "DIAGNOSTIC_ONLY_RECORD_DIRECTION_NO_TUNING_NO_PROMOTION_NO_AUTO_SCOPE_EXPANSION",
    }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    print("KEIRIN_Q_PRE_SHARED_STATE_PROXY_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
