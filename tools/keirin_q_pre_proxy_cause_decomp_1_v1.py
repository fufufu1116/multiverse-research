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
PRIOR_EVIDENCE = ROOT / "v3" / "historical_all_market" / "research_candidates" / "KEIRIN_Q_PRE_SHARED_STATE_PROXY_1_EVIDENCE_20260901_v1.json"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(NEW_LINEAGE))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base
import digital_twin_v1 as dt
from top3_architecture_core_v1 import pl_top3_from_runner_utilities

BLOCK_SEED_BASES = (20261001, 20262001, 20263001, 20264001)
CASES_PER_BLOCK = 128
WORLD = "W1"
ALPHA = 0.16
NOISE_SD = 0.55
NOISE_VAR = NOISE_SD ** 2
LATENT_VAR = 1.0
TOL = 1e-12
TOL_BASELINE = 2e-14
TOL_MASS = 1e-10
EXPECTED_C1_LOSS = 4.688863790585787
EXPECTED_N1_LOSS = 4.6877246961344206
EXPECTED_NAIVE_LOSS = 4.71288958756397
EXPECTED_NAIVE_MINUS_C1 = 0.024025796978182967
MODELS = ("C1", "N1", "SELF", "PEER", "NAIVE")


def _assert_pre(pre: Mapping[str, object]) -> None:
    riders = pre.get("riders")
    if not isinstance(riders, list):
        raise AssertionError("invalid_PRE_riders")
    for rider in riders:
        if not isinstance(rider, dict):
            raise AssertionError("invalid_PRE_rider")
        if "latent_skill" in rider:
            raise AssertionError("latent_skill_leaked_into_PRE")


def _group_score_stats(pre: Mapping[str, object]) -> tuple[dict[int, float], dict[int, int]]:
    sums: dict[int, float] = {}
    counts: dict[int, int] = {}
    for rider in pre["riders"]:
        group = int(rider["line_group_id"])
        sums[group] = sums.get(group, 0.0) + float(rider["score"])
        counts[group] = counts.get(group, 0) + 1
    return sums, counts


def _self_component_utilities(pre: Mapping[str, object], c1_params: Mapping[str, float], shrinkage: float) -> Dict[int, float]:
    ordinary = base._c1_utilities(pre, c1_params, shrinkage)
    out: Dict[int, float] = {}
    for rider in pre["riders"]:
        car = int(rider["car_no"])
        n = int(rider["line_size"])
        out[car] = float(ordinary[car]) + ALPHA * float(rider["score"]) / n
    return out


def _peer_component_utilities(pre: Mapping[str, object], c1_params: Mapping[str, float], shrinkage: float) -> Dict[int, float]:
    ordinary = base._c1_utilities(pre, c1_params, shrinkage)
    sums, counts = _group_score_stats(pre)
    out: Dict[int, float] = {}
    for rider in pre["riders"]:
        car = int(rider["car_no"])
        group = int(rider["line_group_id"])
        n = counts[group]
        if n != int(rider["line_size"]):
            raise AssertionError("line_size_PRE_group_count_mismatch")
        peer_sum = sums[group] - float(rider["score"])
        out[car] = float(ordinary[car]) + ALPHA * peer_sum / n
    return out


def _naive_utilities(pre: Mapping[str, object], c1_params: Mapping[str, float], shrinkage: float) -> Dict[int, float]:
    ordinary = base._c1_utilities(pre, c1_params, shrinkage)
    sums, counts = _group_score_stats(pre)
    out: Dict[int, float] = {}
    for rider in pre["riders"]:
        car = int(rider["car_no"])
        group = int(rider["line_group_id"])
        out[car] = float(ordinary[car]) + ALPHA * sums[group] / counts[group]
    return out


def _assert_control_source_boundary() -> None:
    forbidden = ("latent_skill", "world_joint_distribution", "_line_strengths", "_static_utilities")
    for fn in (_group_score_stats, _self_component_utilities, _peer_component_utilities, _naive_utilities):
        source = inspect.getsource(fn)
        hits = [token for token in forbidden if token in source]
        if hits:
            raise AssertionError(f"diagnostic_control_forbidden_source_reference:{fn.__name__}:{hits}")
    peer_source = inspect.getsource(_peer_component_utilities)
    if "line_group_id" not in peer_source or "line_size" not in peer_source:
        raise AssertionError("peer_control_missing_PRE_structure_fields")
    if "score" not in peer_source:
        raise AssertionError("peer_control_missing_PRE_score")


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


def _max_utility_diff(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    if set(a) != set(b):
        raise AssertionError("utility_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


def _empirical_classification(self_delta: float, peer_delta: float, naive_delta: float) -> str:
    self_harm = self_delta > TOL
    peer_harm = peer_delta > TOL
    if self_harm and not peer_harm:
        return "A_B_SELF_DOUBLECOUNTING_DOMINANT"
    if self_harm and peer_harm:
        return "A_B_PLUS_C_OR_E_MIXED"
    if (not self_harm) and peer_harm:
        return "C_OR_D_PEER_FAILURE_WITHOUT_SELF_HARM"
    if (not self_harm) and (not peer_harm) and naive_delta > TOL:
        return "E_NONLINEAR_COMBINATION"
    return "NO_DEGRADATION_REPRODUCED_OR_OTHER"


def _cause_assessment(empirical: str, self_delta: float, peer_delta: float) -> dict:
    self_harm = self_delta > TOL
    peer_harm = peer_delta > TOL
    if self_harm and not peer_harm:
        ab = "SUPPORTED_AS_COUPLED_DOMINANT_EXPLANATION"
    elif self_harm and peer_harm:
        ab = "SUPPORTED_AS_CONTRIBUTOR_BUT_INSUFFICIENT_ALONE"
    else:
        ab = "NOT_SUPPORTED_AS_PRIMARY_EXPLANATION"

    kappa = LATENT_VAR / (LATENT_VAR + NOISE_VAR)
    c_status = "ANALYTIC_MEASUREMENT_ERROR_PRESENT"
    if self_harm or peer_harm:
        c_status = "ANALYTIC_MEASUREMENT_ERROR_PRESENT_AND_EMPIRICALLY_CONSISTENT_WITH_HARM"

    return {
        "A_DOUBLECOUNTING": ab,
        "B_SELF_CONTAMINATION": ab,
        "A_vs_B_separate_identification": "NOT_IDENTIFIABLE_IN_THIS_EXACT_DECOMPOSITION_BY_DESIGN",
        "C_MEASUREMENT_NOISE": c_status,
        "D_AGGREGATION_BIAS": "WRONG_ARITHMETIC_MEAN_FORM_WEAKENED_BY_CANONICAL_GENERATOR; NONLINEAR_PLUGIN_EFFECT_REMAINS_POSSIBLE",
        "E_OTHER_SYNTHETIC_MECHANISM": "RETAIN_AS_OPEN" if empirical in {"A_B_PLUS_C_OR_E_MIXED", "C_OR_D_PEER_FAILURE_WITHOUT_SELF_HARM", "E_NONLINEAR_COMBINATION", "NO_DEGRADATION_REPRODUCED_OR_OTHER"} else "NOT_REQUIRED_TO_EXPLAIN_PRIMARY_PATTERN_BUT_NOT_FALSIFIED",
        "posterior_shrinkage_kappa": kappa,
        "posterior_shared_mean_coefficient_if_linear_Gaussian": ALPHA * kappa,
    }


def main() -> None:
    _assert_control_source_boundary()
    prior = json.loads(PRIOR_EVIDENCE.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS_PROXY_FALSIFIED_AS_SIMPLE_RECOVERY_CONTROL":
        raise AssertionError("prior_proxy_evidence_status_drift")
    if abs(float(prior["aggregate_expected_ordered_top3_log_loss"]["C1"]) - EXPECTED_C1_LOSS) > TOL_BASELINE:
        raise AssertionError("prior_C1_numeric_drift")
    if abs(float(prior["aggregate_expected_ordered_top3_log_loss"]["N1"]) - EXPECTED_N1_LOSS) > TOL_BASELINE:
        raise AssertionError("prior_N1_numeric_drift")
    if abs(float(prior["aggregate_expected_ordered_top3_log_loss"]["C1_PRE_LINE_MEAN_PROXY"]) - EXPECTED_NAIVE_LOSS) > TOL_BASELINE:
        raise AssertionError("prior_naive_numeric_drift")

    frozen = base._load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"] or c1_shrinkage != n1_shrinkage:
        raise AssertionError("frozen_C1_N1_basis_drift")

    aggregate = {m: {k: 0.0 for k in ("rank1", "rank2", "rank3", "total")} for m in MODELS}
    block_results: Dict[str, object] = {}
    line_size_rider_counts: Dict[str, int] = {}
    max_additivity_diff = 0.0
    max_naive_distribution_reconstruction_diff = 0.0
    max_c1_reproduction_diff = 0.0
    max_n1_reproduction_diff = 0.0
    max_prediction_mass_error = 0.0
    max_truth_mass_error = 0.0
    max_chain_residual = 0.0
    weighted_self_noise_increment = 0.0
    weighted_peer_noise_added = 0.0
    weighted_full_noise_increment = 0.0
    rider_observations = 0

    for block_seed in BLOCK_SEED_BASES:
        block = {m: {k: 0.0 for k in ("rank1", "rank2", "rank3", "total")} for m in MODELS}
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = dt.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError("unexpected_fixture_format")
            pre = dt.pre_view(race)
            _assert_pre(pre)

            ordinary_util = base._c1_utilities(pre, c1_params, c1_shrinkage)
            self_util = _self_component_utilities(pre, c1_params, c1_shrinkage)
            peer_util = _peer_component_utilities(pre, c1_params, c1_shrinkage)
            naive_util = _naive_utilities(pre, c1_params, c1_shrinkage)

            reconstructed_naive: Dict[int, float] = {}
            for rider in pre["riders"]:
                car = int(rider["car_no"])
                self_add = float(self_util[car]) - float(ordinary_util[car])
                peer_add = float(peer_util[car]) - float(ordinary_util[car])
                reconstructed_naive[car] = float(ordinary_util[car]) + self_add + peer_add
                max_additivity_diff = max(max_additivity_diff, abs(reconstructed_naive[car] - float(naive_util[car])))
                n = int(rider["line_size"])
                line_size_rider_counts[str(n)] = line_size_rider_counts.get(str(n), 0) + 1
                weighted_self_noise_increment += NOISE_VAR * (2.0 * ALPHA / n + (ALPHA / n) ** 2)
                weighted_peer_noise_added += NOISE_VAR * (ALPHA ** 2) * (n - 1) / (n ** 2)
                weighted_full_noise_increment += NOISE_VAR * (2.0 * ALPHA / n + (ALPHA ** 2) / n)
                rider_observations += 1

            c1 = base._c1(pre, c1_params, c1_shrinkage)
            n1 = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            self_pred = pl_top3_from_runner_utilities(self_util)
            peer_pred = pl_top3_from_runner_utilities(peer_util)
            naive_pred = pl_top3_from_runner_utilities(naive_util)
            reconstructed_pred = pl_top3_from_runner_utilities(reconstructed_naive)
            max_naive_distribution_reconstruction_diff = max(max_naive_distribution_reconstruction_diff, _max_prediction_diff(naive_pred, reconstructed_pred))
            max_c1_reproduction_diff = max(max_c1_reproduction_diff, _max_prediction_diff(c1, base._c1(pre, c1_params, c1_shrinkage)))
            max_n1_reproduction_diff = max(max_n1_reproduction_diff, _max_prediction_diff(n1, base._n1(pre, c1_params, n1_params, n1_shrinkage)))

            truth = dt.world_joint_distribution(race, WORLD)
            support = set(truth)
            truth_mass_error = abs(sum(float(q) for q in truth.values()) - 1.0)
            max_truth_mass_error = max(max_truth_mass_error, truth_mass_error)
            if truth_mass_error > TOL_MASS:
                raise AssertionError("truth_mass_mismatch")

            preds = {"C1": c1, "N1": n1, "SELF": self_pred, "PEER": peer_pred, "NAIVE": naive_pred}
            for model, pred in preds.items():
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

        means = {m: {k: v / CASES_PER_BLOCK for k, v in vals.items()} for m, vals in block.items()}
        block_results[str(block_seed)] = {
            "model_chain_cross_entropy": means,
            "SELF_minus_C1": means["SELF"]["total"] - means["C1"]["total"],
            "PEER_minus_C1": means["PEER"]["total"] - means["C1"]["total"],
            "NAIVE_minus_C1": means["NAIVE"]["total"] - means["C1"]["total"],
            "N1_minus_C1": means["N1"]["total"] - means["C1"]["total"],
        }

    total_cases = len(BLOCK_SEED_BASES) * CASES_PER_BLOCK
    means = {m: {k: v / total_cases for k, v in vals.items()} for m, vals in aggregate.items()}
    c1_loss = means["C1"]["total"]
    n1_loss = means["N1"]["total"]
    self_loss = means["SELF"]["total"]
    peer_loss = means["PEER"]["total"]
    naive_loss = means["NAIVE"]["total"]

    if abs(c1_loss - EXPECTED_C1_LOSS) > TOL_BASELINE:
        raise AssertionError("C1_baseline_not_reproduced")
    if abs(n1_loss - EXPECTED_N1_LOSS) > TOL_BASELINE:
        raise AssertionError("N1_baseline_not_reproduced")
    if abs(naive_loss - EXPECTED_NAIVE_LOSS) > TOL_BASELINE:
        raise AssertionError("NAIVE_baseline_not_reproduced")
    if max_additivity_diff > TOL or max_naive_distribution_reconstruction_diff > TOL:
        raise AssertionError("exact_component_reconstruction_failed")

    self_delta = self_loss - c1_loss
    peer_delta = peer_loss - c1_loss
    naive_delta = naive_loss - c1_loss
    empirical = _empirical_classification(self_delta, peer_delta, naive_delta)
    cause = _cause_assessment(empirical, self_delta, peer_delta)
    kappa = LATENT_VAR / (LATENT_VAR + NOISE_VAR)

    result = {
        "record": "KEIRIN_Q_PRE_PROXY_CAUSE_DECOMP_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "world": WORLD,
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "empirical_classification": empirical,
        "cause_assessment": cause,
        "aggregate_model_chain_cross_entropy": means,
        "aggregate_deltas": {
            "SELF_minus_C1": self_delta,
            "PEER_minus_C1": peer_delta,
            "NAIVE_minus_C1": naive_delta,
            "N1_minus_C1": n1_loss - c1_loss,
            "SELF_minus_NAIVE": self_loss - naive_loss,
            "PEER_minus_NAIVE": peer_loss - naive_loss,
        },
        "block_results": block_results,
        "analytic_measurement_error": {
            "latent_variance": LATENT_VAR,
            "observation_noise_sd": NOISE_SD,
            "observation_noise_variance": NOISE_VAR,
            "posterior_shrinkage_kappa": kappa,
            "raw_C1_score_coefficient": 1.0,
            "posterior_linear_Gaussian_latent_coefficient": kappa,
            "raw_shared_mean_coefficient": ALPHA,
            "posterior_linear_Gaussian_shared_mean_coefficient": ALPHA * kappa,
            "line_mean_signal_to_noise_variance_ratio": LATENT_VAR / NOISE_VAR,
            "mean_self_component_incremental_noise_variance_across_rider_observations": weighted_self_noise_increment / rider_observations,
            "mean_peer_component_added_noise_variance_across_rider_observations": weighted_peer_noise_added / rider_observations,
            "mean_full_naive_incremental_noise_variance_across_rider_observations": weighted_full_noise_increment / rider_observations,
            "arithmetic_line_mean_unbiased_for_hidden_line_mean_at_utility_target_level": True,
            "shrinkage_corrected_control_executed": False,
        },
        "line_size_rider_counts": line_size_rider_counts,
        "diagnostic_controls": {
            "SELF": {"formal_model_candidate": False, "PRE_only": True, "coefficient": ALPHA, "coefficient_fitted": False, "latent_skill_access": False, "truth_access": False},
            "PEER": {"formal_model_candidate": False, "PRE_only": True, "coefficient": ALPHA, "coefficient_fitted": False, "latent_skill_access": False, "truth_access": False, "denominator": "original line_size"},
            "NAIVE": {"role": "REFERENCE_REPRODUCTION_ONLY", "formal_model_candidate": False}
        },
        "mechanical_checks": {
            "control_source_boundary_pass": True,
            "PRE_latent_skill_absent": True,
            "max_SELF_plus_PEER_vs_NAIVE_utility_diff": max_additivity_diff,
            "max_reconstructed_NAIVE_distribution_diff": max_naive_distribution_reconstruction_diff,
            "max_non_diagnostic_C1_reproduction_diff": max_c1_reproduction_diff,
            "max_non_diagnostic_N1_reproduction_diff": max_n1_reproduction_diff,
            "max_prediction_probability_mass_error": max_prediction_mass_error,
            "max_truth_probability_mass_error": max_truth_mass_error,
            "max_chain_decomposition_residual": max_chain_residual,
            "prior_C1_reproduction_error": abs(c1_loss - EXPECTED_C1_LOSS),
            "prior_N1_reproduction_error": abs(n1_loss - EXPECTED_N1_LOSS),
            "prior_NAIVE_reproduction_error": abs(naive_loss - EXPECTED_NAIVE_LOSS),
        },
        "new_seed_selection": False,
        "post_hoc_slice": False,
        "result_adaptive_diagnostic_family_addition": False,
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
        "scientific_decision": "CAUSE_DECOMPOSITION_ONLY_RECORD_DIRECTION_NO_PROXY_SEARCH_NO_COEFFICIENT_SEARCH_NO_AUTO_SCOPE_EXPANSION"
    }
    print(json.dumps(result, sort_keys=True))
    print("KEIRIN_Q_PRE_PROXY_CAUSE_DECOMP_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
