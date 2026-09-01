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
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(NEW_LINEAGE))

import keirin_synthetic_c0_c1_n1_comparison_v1 as base
import digital_twin_v1 as dt
from top3_architecture_core_v1 import pl_top3_from_runner_utilities

BLOCK_SEED_BASES = (20265001, 20266001, 20267001, 20268001)
CASES_PER_BLOCK = 128
WORLD = "W1"
CANDIDATE = "C1_PEER_LOO_MEAN_PROSPECTIVE"
MODELS = ("C0", "C1", "N1", CANDIDATE)
PEER_COEF = 0.16
TOL = 1e-12
TOL_MASS = 1e-10


def _assert_pre_boundary(pre: Mapping[str, object]) -> None:
    riders = pre.get("riders")
    if not isinstance(riders, list):
        raise AssertionError("invalid_PRE_riders")
    for rider in riders:
        if not isinstance(rider, dict):
            raise AssertionError("invalid_PRE_rider")
        if "latent_skill" in rider:
            raise AssertionError("latent_truth_exposed_to_PRE")


def _peer_mean_scores(pre: Mapping[str, object]) -> Dict[int, float]:
    riders = [dict(r) for r in pre["riders"]]
    groups: Dict[int, list[dict]] = {}
    for rider in riders:
        groups.setdefault(int(rider["line_group_id"]), []).append(rider)

    out: Dict[int, float] = {}
    for rider in riders:
        car = int(rider["car_no"])
        line_id = int(rider["line_group_id"])
        line_size = int(rider["line_size"])
        members = groups[line_id]
        if len(members) != line_size:
            raise AssertionError(f"line_size_membership_mismatch:{car}")
        peers = [p for p in members if int(p["car_no"]) != car]
        if len(peers) != max(0, line_size - 1):
            raise AssertionError(f"peer_count_mismatch:{car}")
        if not peers:
            out[car] = 0.0
        else:
            out[car] = sum(float(p["score"]) for p in peers) / len(peers)
    return out


def _candidate_prediction(
    pre: Mapping[str, object],
    c1_params: Mapping[str, float],
    shrinkage: float,
) -> Dict[dt.Top3, float]:
    _assert_pre_boundary(pre)
    ordinary_c1_util = base._c1_utilities(pre, c1_params, shrinkage)
    peer_mean = _peer_mean_scores(pre)
    candidate_util = {
        int(car): float(value) + PEER_COEF * float(peer_mean[int(car)])
        for car, value in ordinary_c1_util.items()
    }
    if set(candidate_util) != set(ordinary_c1_util):
        raise AssertionError("candidate_support_mismatch")
    return pl_top3_from_runner_utilities(candidate_util)


def _assert_candidate_source_boundary() -> None:
    candidate_source = inspect.getsource(_candidate_prediction)
    helper_source = inspect.getsource(_peer_mean_scores)
    forbidden = ("latent_skill", "world_joint_distribution", "_static_utilities", "_line_strengths")
    for source_name, source in (("candidate", candidate_source), ("helper", helper_source)):
        hits = [token for token in forbidden if token in source]
        if hits:
            raise AssertionError(f"forbidden_candidate_source_reference:{source_name}:{hits}")
    for token in ("score", "line_group_id", "line_size", "car_no"):
        if token not in helper_source:
            raise AssertionError(f"missing_required_PRE_field:{token}")
    if "_c1_utilities" not in candidate_source:
        raise AssertionError("candidate_missing_frozen_C1_base")
    if "pl_top3_from_runner_utilities" not in candidate_source:
        raise AssertionError("candidate_missing_C1_generator")


def _max_prediction_diff(a: Mapping[dt.Top3, float], b: Mapping[dt.Top3, float]) -> float:
    if set(a) != set(b):
        raise AssertionError("prediction_support_mismatch")
    return max(abs(float(a[k]) - float(b[k])) for k in a)


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


def _peer_sanity(pre: Mapping[str, object], computed: Mapping[int, float]) -> tuple[float, int, int]:
    riders = [dict(r) for r in pre["riders"]]
    max_diff = 0.0
    singleton_count = 0
    non_singleton_count = 0
    for rider in riders:
        car = int(rider["car_no"])
        line_id = int(rider["line_group_id"])
        line_size = int(rider["line_size"])
        peers = [
            p for p in riders
            if int(p["line_group_id"]) == line_id and int(p["car_no"]) != car
        ]
        if len(peers) != max(0, line_size - 1):
            raise AssertionError(f"direct_peer_count_mismatch:{car}")
        if not peers:
            singleton_count += 1
            direct = 0.0
        else:
            non_singleton_count += 1
            direct = sum(float(p["score"]) for p in peers) / len(peers)
        max_diff = max(max_diff, abs(float(computed[car]) - direct))
    return max_diff, singleton_count, non_singleton_count


def _decision(candidate_minus_c1: float, favorable_blocks: int, unfavorable_blocks: int) -> str:
    if candidate_minus_c1 < -TOL and favorable_blocks >= 3:
        return "PASS"
    if candidate_minus_c1 > TOL and unfavorable_blocks >= 3:
        return "FAIL"
    return "INCONCLUSIVE"


def main() -> None:
    _assert_candidate_source_boundary()
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
    max_c0_repro = 0.0
    max_c1_repro = 0.0
    max_n1_repro = 0.0
    max_peer_sanity = 0.0
    total_singletons = 0
    total_non_singletons = 0

    for block_seed in BLOCK_SEED_BASES:
        block = {m: {k: 0.0 for k in ("rank1", "rank2", "rank3", "total")} for m in MODELS}
        for case in range(CASES_PER_BLOCK):
            seed = block_seed + case
            race_index = case % 32
            race = dt.generate_race(seed=seed, race_index=race_index)
            if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
                raise AssertionError(f"unexpected_format:{block_seed}:{case}")
            pre = dt.pre_view(race)
            _assert_pre_boundary(pre)

            peer_mean = _peer_mean_scores(pre)
            sanity, singletons, non_singletons = _peer_sanity(pre, peer_mean)
            max_peer_sanity = max(max_peer_sanity, sanity)
            total_singletons += singletons
            total_non_singletons += non_singletons

            c0 = base._c0(pre)
            c1 = base._c1(pre, c1_params, c1_shrinkage)
            n1 = base._n1(pre, c1_params, n1_params, n1_shrinkage)
            candidate = _candidate_prediction(pre, c1_params, c1_shrinkage)

            max_c0_repro = max(max_c0_repro, _max_prediction_diff(c0, base._c0(pre)))
            max_c1_repro = max(max_c1_repro, _max_prediction_diff(c1, base._c1(pre, c1_params, c1_shrinkage)))
            max_n1_repro = max(max_n1_repro, _max_prediction_diff(n1, base._n1(pre, c1_params, n1_params, n1_shrinkage)))

            truth = dt.world_joint_distribution(race, WORLD)
            support = set(truth)
            truth_mass_error = abs(sum(float(q) for q in truth.values()) - 1.0)
            max_truth_mass_error = max(max_truth_mass_error, truth_mass_error)
            if truth_mass_error > TOL_MASS:
                raise AssertionError("truth_mass_mismatch")

            predictions = {"C0": c0, "C1": c1, "N1": n1, CANDIDATE: candidate}
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

        block_means = {
            m: {k: value / CASES_PER_BLOCK for k, value in metrics.items()}
            for m, metrics in block.items()
        }
        candidate_delta = block_means[CANDIDATE]["total"] - block_means["C1"]["total"]
        block_results[str(block_seed)] = {
            "model_chain_cross_entropy": block_means,
            "candidate_minus_C1": candidate_delta,
            "candidate_minus_N1": block_means[CANDIDATE]["total"] - block_means["N1"]["total"],
            "candidate_minus_C0": block_means[CANDIDATE]["total"] - block_means["C0"]["total"],
            "N1_minus_C1": block_means["N1"]["total"] - block_means["C1"]["total"],
        }

    total_cases = len(BLOCK_SEED_BASES) * CASES_PER_BLOCK
    means = {
        m: {k: value / total_cases for k, value in metrics.items()}
        for m, metrics in aggregate.items()
    }
    candidate_minus_c1 = means[CANDIDATE]["total"] - means["C1"]["total"]
    favorable_blocks = sum(1 for b in block_results.values() if float(b["candidate_minus_C1"]) < -TOL)
    unfavorable_blocks = sum(1 for b in block_results.values() if float(b["candidate_minus_C1"]) > TOL)
    tie_blocks = len(BLOCK_SEED_BASES) - favorable_blocks - unfavorable_blocks
    decision = _decision(candidate_minus_c1, favorable_blocks, unfavorable_blocks)

    result = {
        "record": "KEIRIN_Q_PEER_PRE_PROSPECTIVE_1_RESULT_v1",
        "status": "PASS_EXECUTION_AND_MECHANICAL_INVARIANTS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "world": WORLD,
        "prospective_fixture_role": "NEWLY_PRESPECIFIED_SYNTHETIC_FIXTURES_NOT_REAL_OR_UNTOUCHED_VALIDATION",
        "block_seed_bases": list(BLOCK_SEED_BASES),
        "cases_per_block": CASES_PER_BLOCK,
        "total_cases": total_cases,
        "primary_decision": decision,
        "aggregate_model_chain_cross_entropy": means,
        "aggregate_deltas_lower_is_better": {
            "candidate_minus_C1": candidate_minus_c1,
            "candidate_minus_N1": means[CANDIDATE]["total"] - means["N1"]["total"],
            "candidate_minus_C0": means[CANDIDATE]["total"] - means["C0"]["total"],
            "N1_minus_C1": means["N1"]["total"] - means["C1"]["total"],
            "C1_minus_C0": means["C1"]["total"] - means["C0"]["total"],
        },
        "block_stability": {
            "candidate_better_than_C1_blocks": favorable_blocks,
            "candidate_worse_than_C1_blocks": unfavorable_blocks,
            "candidate_tie_C1_blocks": tie_blocks,
            "total_blocks": len(BLOCK_SEED_BASES),
        },
        "block_results": block_results,
        "candidate_definition": {
            "id": CANDIDATE,
            "formal_model_adoption": False,
            "PRE_only": True,
            "target_excluded": True,
            "normalization": "mean over line_size-1 same-line peers; singleton zero",
            "coefficient": PEER_COEF,
            "coefficient_fitted": False,
            "coefficient_swept": False,
            "residualized": False,
            "measurement_error_shrinkage_applied": False,
            "latent_truth_access": False,
            "truth_distribution_access_by_candidate": False,
        },
        "mechanical_checks": {
            "candidate_source_boundary_pass": True,
            "PRE_latent_truth_absent": True,
            "max_peer_mean_sanity_diff": max_peer_sanity,
            "singleton_feature_zero_by_definition": True,
            "total_singleton_rider_observations": total_singletons,
            "total_non_singleton_rider_observations": total_non_singletons,
            "max_non_diagnostic_C0_reproduction_diff": max_c0_repro,
            "max_non_diagnostic_C1_reproduction_diff": max_c1_repro,
            "max_non_diagnostic_N1_reproduction_diff": max_n1_repro,
            "max_prediction_probability_mass_error": max_prediction_mass_error,
            "max_truth_probability_mass_error": max_truth_mass_error,
            "max_chain_decomposition_residual": max_chain_residual,
        },
        "decision_contract": {
            "PASS": "aggregate candidate_minus_C1 < -1e-12 and candidate better than C1 in >=3/4 blocks",
            "FAIL": "aggregate candidate_minus_C1 > +1e-12 and candidate worse than C1 in >=3/4 blocks",
            "INCONCLUSIVE": "all other valid outcomes",
            "N1_win_required": False,
        },
        "prospective_integrity": {
            "prior_PEER_effect_used_for_coefficient": False,
            "prior_PEER_effect_used_for_normalization": False,
            "prior_PEER_effect_used_for_seed_selection": False,
            "feature_tournament": False,
            "new_seed_selection": True,
            "seed_selection_result_adaptive": False,
            "post_result_seed_extension": False,
            "post_hoc_slice": False,
            "post_result_retuning": False,
            "models_or_frozen_coefficients_changed": False,
            "authorization_auto_expanded": False,
        },
        "scientific_decision": "RECORD_DIRECTION_FREEZE_EVIDENCE_NO_RESCUE_NO_AUTO_SCOPE_EXPANSION",
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
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("KEIRIN_Q_PEER_PRE_PROSPECTIVE_1_EXECUTION_PASS")


if __name__ == "__main__":
    main()
