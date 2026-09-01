#!/usr/bin/env python3
from __future__ import annotations

import ast
from dataclasses import replace
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from typing import Dict, Mapping, Tuple

ROOT = Path(__file__).resolve().parents[1]
CMP_PATH = ROOT / "tools" / "keirin_synthetic_c0_c1_n1_comparison_v1.py"
ARCH_PATH = ROOT / "v3" / "historical_all_market" / "new_lineage" / "top3_architecture_core_v1.py"

# Prespecified regression fixtures only. These are not a validation sample and
# are never selected or changed as a function of model-comparison outcomes.
TEST_CASES = tuple((20260821 + i, i % 32) for i in range(24))
MODELS = ("C0", "C1", "N1")
WORLDS = ("W0", "W1", "W2", "W3", "W4")
TOL = 1e-12

spec = importlib.util.spec_from_file_location("keirin_cmp_gate_source", CMP_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("comparison_harness_import_spec_failed")
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)
dt = sys.modules.get("digital_twin_v1")
if dt is None:
    raise RuntimeError("digital_twin_module_not_loaded")


def _predictions(pre: Mapping[str, object]) -> Dict[str, Mapping[Tuple[int, int, int], float]]:
    frozen = cmp._load_frozen_params()
    c1_params = frozen["C1"]["train_params"]
    n1_params = frozen["N1"]["conditional_train_params"]
    c1_shrinkage = float(frozen["C1"]["cal_shrinkage"])
    n1_shrinkage = float(frozen["N1"]["cal_shrinkage"])
    if c1_params != frozen["N1"]["c1_base_train_params"]:
        raise AssertionError("C1_N1_P1_parameter_basis_mismatch")
    if c1_shrinkage != n1_shrinkage:
        raise AssertionError("C1_N1_P1_shrinkage_mismatch")
    return {
        "C0": cmp._c0(pre),
        "C1": cmp._c1(pre, c1_params, c1_shrinkage),
        "N1": cmp._n1(pre, c1_params, n1_params, n1_shrinkage),
    }


def _max_abs_map_diff(a, b) -> float:
    if set(a) != set(b):
        raise AssertionError("support_mismatch")
    return max((abs(float(a[k]) - float(b[k])) for k in a), default=0.0)


def _relabel_joint(joint, mapping: Mapping[int, int]):
    return {
        (mapping[i], mapping[j], mapping[k]): float(p)
        for (i, j, k), p in joint.items()
    }


def _permute_car_ids(pre: Mapping[str, object], mapping: Mapping[int, int]) -> dict:
    out = dict(pre)
    out["riders"] = [
        {**dict(rider), "car_no": mapping[int(rider["car_no"])]}
        for rider in pre["riders"]
    ]
    return out


def _rename_line_groups(pre: Mapping[str, object], mapping: Mapping[int, int]) -> dict:
    out = dict(pre)
    out["riders"] = [
        {**dict(rider), "line_group_id": mapping[int(rider["line_group_id"])]}
        for rider in pre["riders"]
    ]
    return out


def _reverse_container(pre: Mapping[str, object]) -> dict:
    out = dict(pre)
    out["riders"] = list(reversed([dict(r) for r in pre["riders"]]))
    return out


def _recursive_keys(obj: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= _recursive_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            keys |= _recursive_keys(v)
    return keys


def _prediction_function_truth_separation() -> dict:
    tree = ast.parse(CMP_PATH.read_text(encoding="utf-8"))
    target_names = {"_c0", "_c1_utilities", "_c1", "_n1"}
    forbidden = {
        "world_joint_distribution",
        "generate_race",
        "_expected_log_loss",
        "_truth_entropy",
        "_joint_brier",
    }
    seen = set()
    violations = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_names:
            seen.add(node.name)
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id in forbidden:
                    violations.append(f"{node.name}:{child.id}")
                if isinstance(child, ast.Attribute) and child.attr in forbidden:
                    violations.append(f"{node.name}:{child.attr}")
    if seen != target_names:
        raise AssertionError(f"missing_prediction_functions:{sorted(target_names - seen)}")
    arch_tree = ast.parse(ARCH_PATH.read_text(encoding="utf-8"))
    arch_forbidden_hits = []
    for child in ast.walk(arch_tree):
        if isinstance(child, ast.ImportFrom) and child.module == "digital_twin_v1":
            arch_forbidden_hits.append("importfrom:digital_twin_v1")
        if isinstance(child, ast.Import):
            for alias in child.names:
                if alias.name == "digital_twin_v1":
                    arch_forbidden_hits.append("import:digital_twin_v1")
        if isinstance(child, ast.Name) and child.id == "world_joint_distribution":
            arch_forbidden_hits.append("name:world_joint_distribution")
        if isinstance(child, ast.Attribute) and child.attr == "world_joint_distribution":
            arch_forbidden_hits.append("attribute:world_joint_distribution")
    if violations or arch_forbidden_hits:
        raise AssertionError(
            f"truth_prediction_path_violation:{violations}:{arch_forbidden_hits}"
        )
    return {
        "prediction_functions_checked": sorted(seen),
        "forbidden_call_hits": violations,
        "architecture_forbidden_import_or_token_hits": arch_forbidden_hits,
    }


def _runtime_nonadaptive_selection_evidence() -> dict:
    source = inspect.getsource(cmp.main)
    required_fragments = (
        "for case in range(CASE_COUNT)",
        "seed = 20260821 + case",
        "race_index = case % 32",
        "for world in WORLDS",
        '"result_adaptive_sampling_or_retuning": False',
        '"model_promotion": False',
    )
    missing = [fragment for fragment in required_fragments if fragment not in source]
    if missing:
        raise AssertionError(f"runtime_nonadaptive_contract_missing:{missing}")
    if tuple(cmp.WORLDS) != WORLDS or int(cmp.CASE_COUNT) != 128:
        raise AssertionError("comparison_condition_constants_drift")
    return {
        "comparison_case_count": int(cmp.CASE_COUNT),
        "comparison_worlds": list(cmp.WORLDS),
        "seed_formula": "20260821 + case",
        "race_index_formula": "case % 32",
        "runtime_result_adaptive_sampling_or_retuning": False,
        "classification": "RUNTIME_NONADAPTIVITY_PASS_NOT_UNTOUCHED_VALIDATION",
    }


def main() -> None:
    max_car_id_diff = {m: 0.0 for m in MODELS}
    max_line_id_pred_diff = {m: 0.0 for m in MODELS}
    max_line_id_truth_diff = {w: 0.0 for w in WORLDS}
    max_order_pred_diff = {m: 0.0 for m in MODELS}
    max_order_truth_diff = {w: 0.0 for w in WORLDS}
    latent_barrier_cases = 0

    for seed, race_index in TEST_CASES:
        race = dt.generate_race(seed=seed, race_index=race_index)
        if race.event_format != "STANDARD_FI_FII_7" or len(race.riders) != 7:
            raise AssertionError(f"unexpected_fixture_format:{seed}:{race_index}")
        pre = dt.pre_view(race)
        original = _predictions(pre)

        # Gate 1: Car-ID permutation equivariance.
        car_map = {1: 4, 2: 7, 3: 1, 4: 6, 5: 2, 6: 5, 7: 3}
        car_pre = _permute_car_ids(pre, car_map)
        car_pred = _predictions(car_pre)
        for model in MODELS:
            relabeled = _relabel_joint(original[model], car_map)
            diff = _max_abs_map_diff(relabeled, car_pred[model])
            max_car_id_diff[model] = max(max_car_id_diff[model], diff)
            if diff > TOL:
                raise AssertionError(
                    f"car_id_permutation_equivariance_failed:{seed}:{race_index}:{model}:{diff}"
                )

        # Gate 2: Line-group-ID permutation invariance in prediction and truth.
        groups = sorted({int(r["line_group_id"]) for r in pre["riders"]})
        line_map = {group: 1000 + groups[-1 - idx] for idx, group in enumerate(groups)}
        line_pre = _rename_line_groups(pre, line_map)
        line_pred = _predictions(line_pre)
        line_race = replace(
            race,
            riders=tuple(replace(r, line_id=line_map[int(r.line_id)]) for r in race.riders),
        )
        for model in MODELS:
            diff = _max_abs_map_diff(original[model], line_pred[model])
            max_line_id_pred_diff[model] = max(max_line_id_pred_diff[model], diff)
            if diff > TOL:
                raise AssertionError(
                    f"line_group_id_prediction_invariance_failed:{seed}:{race_index}:{model}:{diff}"
                )
        for world in WORLDS:
            truth_a = dt.world_joint_distribution(race, world)
            truth_b = dt.world_joint_distribution(line_race, world)
            diff = _max_abs_map_diff(truth_a, truth_b)
            max_line_id_truth_diff[world] = max(max_line_id_truth_diff[world], diff)
            if diff > TOL:
                raise AssertionError(
                    f"line_group_id_truth_invariance_failed:{seed}:{race_index}:{world}:{diff}"
                )

        # Gate 3: Container/order invariance.
        order_pre = _reverse_container(pre)
        order_pred = _predictions(order_pre)
        order_race = replace(race, riders=tuple(reversed(race.riders)))
        for model in MODELS:
            diff = _max_abs_map_diff(original[model], order_pred[model])
            max_order_pred_diff[model] = max(max_order_pred_diff[model], diff)
            if diff > TOL:
                raise AssertionError(
                    f"container_order_prediction_invariance_failed:{seed}:{race_index}:{model}:{diff}"
                )
        for world in WORLDS:
            truth_a = dt.world_joint_distribution(race, world)
            truth_b = dt.world_joint_distribution(order_race, world)
            diff = _max_abs_map_diff(truth_a, truth_b)
            max_order_truth_diff[world] = max(max_order_truth_diff[world], diff)
            if diff > TOL:
                raise AssertionError(
                    f"container_order_truth_invariance_failed:{seed}:{race_index}:{world}:{diff}"
                )

        # Gate 4: PRE / latent barrier.
        keys = _recursive_keys(pre)
        if "latent_skill" in keys:
            raise AssertionError(f"latent_skill_key_exposed_in_PRE:{seed}:{race_index}")
        if "latent_skill" in json.dumps(pre, ensure_ascii=False, sort_keys=True):
            raise AssertionError(f"latent_skill_serialized_into_PRE:{seed}:{race_index}")
        latent_barrier_cases += 1

    # Gate 5: Truth / prediction code-path separation.
    separation = _prediction_function_truth_separation()

    # Gate 6: no adaptive seed / condition selection at runtime.
    nonadaptive = _runtime_nonadaptive_selection_evidence()

    result = {
        "record": "KEIRIN_PARALLEL_MECHANICAL_INVARIANCE_GATE_v1",
        "status": "PASS",
        "classification": "RESEARCH_CANDIDATE_NOT_CANONICAL_NOT_ACCEPTED_NOT_PROMOTED",
        "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
        "fixture_count": len(TEST_CASES),
        "fixture_rule": "seed=20260821+i,race_index=i%32 for i in [0,23]; fixed in source before execution",
        "tolerance": TOL,
        "gates": {
            "1_car_id_permutation_equivariance": {
                "status": "PASS",
                "max_abs_probability_diff_by_model": max_car_id_diff,
            },
            "2_line_group_id_permutation_invariance": {
                "status": "PASS",
                "max_abs_prediction_diff_by_model": max_line_id_pred_diff,
                "max_abs_truth_diff_by_world": max_line_id_truth_diff,
            },
            "3_container_order_invariance": {
                "status": "PASS",
                "max_abs_prediction_diff_by_model": max_order_pred_diff,
                "max_abs_truth_diff_by_world": max_order_truth_diff,
            },
            "4_pre_latent_barrier_regression": {
                "status": "PASS",
                "cases_checked": latent_barrier_cases,
                "latent_skill_exposed": False,
            },
            "5_truth_prediction_code_path_separation": {
                "status": "PASS",
                **separation,
            },
            "6_no_adaptive_seed_condition_selection_evidence": {
                "status": "PASS",
                **nonadaptive,
            },
        },
        "material_failure_in_gates_1_to_5": False,
        "downstream_synthetic_comparison_interpretability_gate": "GREEN",
        "protected_or_quarantined_input_access": False,
        "pr15_metrics_access": False,
        "result_payout_access": False,
        "econ_holdout1000_access": False,
        "dev2000_c_rescue": False,
        "scientific_segment_c_scoring_count": 0,
        "real_live_input_collection": False,
        "economics": False,
        "model_or_coefficient_change": False,
        "model_promotion": False,
        "external_provider_contact": False,
        "real_money_wagering": False,
        "real_world_edge_or_roi_evidence": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("KEIRIN_PARALLEL_MECHANICAL_INVARIANCE_GATE_PASS")


if __name__ == "__main__":
    main()
