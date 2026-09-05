"""Repository-only Runtime convergence guard.

This module does not start Runtime, contact Render, open a network path, or perform
provider/business effects. It validates the exact adopted evidence materialized in
this Candidate and returns an inert convergence receipt.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUTOMATION = ROOT.parent
CANONICAL_MAIN = "a6f56facc80709f2e7b8218d927484d522bfa356"
PROOF = "RUNTIME_CONVERGENCE_REPOSITORY_PREPARATION_ONLY"


class ConvergenceError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ConvergenceError(code)


def _require_false_map(values: dict[str, Any], code: str) -> None:
    _require(type(values) is dict, code)
    for value in values.values():
        _require(type(value) is bool and value is False, code)


def build_convergence_receipt() -> dict[str, Any]:
    contract = _load(ROOT / "CONVERGENCE_CONTRACT_v1.json")
    ledger = _load(ROOT / "PROVENANCE_LEDGER_v1.json")

    runtime_manifest = _load(
        AUTOMATION / "runtime_v1" / "RUNTIME_V1_MANIFEST.json"
    )
    runtime_freeze = _load(
        AUTOMATION / "runtime_v1" / "RUNTIME_V1_CANDIDATE_FREEZE.json"
    )
    deployment_freeze = _load(
        AUTOMATION
        / "deployment_v1"
        / "DEPLOYMENT_EVIDENCE_V1_CANDIDATE_FREEZE.json"
    )
    target_seal = _load(
        AUTOMATION / "target_environment_v1" / "CANDIDATE_SEAL_v1.json"
    )
    infrastructure_seal = _load(
        AUTOMATION
        / "real_infrastructure_prep_v1"
        / "CANDIDATE_SEAL_v1.json"
    )
    remote_single = _load(
        AUTOMATION
        / "remote_preprod_render_v1"
        / "REMOTE_EVIDENCE_RECEIPT_v1.json"
    )
    multi_prep = _load(
        AUTOMATION
        / "multi_host_preprod_noeffect_preparation_v1"
        / "PREPARATION_CONTRACT_v1.json"
    )
    multi_prep_seal = _load(
        AUTOMATION
        / "multi_host_preprod_noeffect_preparation_v1"
        / "CANDIDATE_SEAL_v1.json"
    )
    multi_real = _load(
        AUTOMATION
        / "remote_multihost_render_v1"
        / "REMOTE_EVIDENCE_RECEIPT_v2.json"
    )
    multi_real_seal = _load(
        AUTOMATION
        / "remote_multihost_render_v1"
        / "CANDIDATE_SEAL_v2.json"
    )

    _require(contract["canonical_main"] == CANONICAL_MAIN, "CONTRACT_MAIN_MISMATCH")
    _require(contract["proof_ceiling"] == PROOF, "PROOF_CEILING_MISMATCH")
    _require(contract["runtime"] == "OFF", "RUNTIME_MUST_BE_OFF")
    _require_false_map(contract["authority"], "CONVERGENCE_AUTHORITY_NOT_FALSE")

    _require(
        runtime_manifest["canonical_main"] == CANONICAL_MAIN
        and runtime_manifest["canonical_tree"] == contract["canonical_tree"]
        and runtime_manifest["mode"] == "SEALED_DRY_RUN"
        and runtime_manifest["runtime"] == "OFF",
        "RUNTIME_MANIFEST_BINDING_MISMATCH",
    )
    _require_false_map(runtime_manifest["authority"], "RUNTIME_AUTHORITY_NOT_FALSE")

    _require(
        runtime_freeze["canonical_main"] == CANONICAL_MAIN
        and runtime_freeze["frozen"] is True
        and runtime_freeze["runtime"] == "OFF",
        "RUNTIME_FREEZE_MISMATCH",
    )
    _require_false_map(runtime_freeze["authority"], "RUNTIME_FREEZE_AUTHORITY_NOT_FALSE")

    _require(
        deployment_freeze["adopted_runtime_head"]
        == contract["materialized_subtrees"]["runtime_v1"]["source_commit"]
        and deployment_freeze["canonical_main"] == CANONICAL_MAIN
        and deployment_freeze["frozen"] is True
        and deployment_freeze["runtime"] == "OFF",
        "DEPLOYMENT_BINDING_MISMATCH",
    )
    _require_false_map(
        deployment_freeze["authority"], "DEPLOYMENT_AUTHORITY_NOT_FALSE"
    )
    _require(
        contract["materialized_subtrees"]["deployment_v1"]["source_commit"]
        != contract["materialized_subtrees"]["deployment_v1"][
            "explicitly_excludes_later_pr112_head"
        ],
        "DEPLOYMENT_LATER_HEAD_MUST_NOT_BE_ADOPTED",
    )

    _require(
        target_seal["canonical_main"] == CANONICAL_MAIN
        and target_seal["adopted_runtime_head"]
        == contract["materialized_subtrees"]["runtime_v1"]["source_commit"]
        and target_seal["adopted_deployment_head"]
        == contract["materialized_subtrees"]["deployment_v1"]["source_commit"]
        and target_seal["environment_class"] == "PRE_PRODUCTION"
        and target_seal["runtime"] == "OFF",
        "TARGET_BINDING_MISMATCH",
    )
    for key in (
        "network_enabled",
        "external_effect_enabled",
        "spend_enabled",
        "protected_keirin_data_enabled",
        "production_credentials_enabled",
        "runtime_activation",
    ):
        _require(target_seal[key] is False, "TARGET_AUTHORITY_NOT_FALSE")

    _require(
        infrastructure_seal["canonical_main"] == CANONICAL_MAIN
        and infrastructure_seal["adopted_target_environment_head"]
        == contract["materialized_subtrees"]["target_environment_v1"]["source_commit"]
        and infrastructure_seal["environment_class"] == "PRE_PRODUCTION"
        and infrastructure_seal["runtime"] == "OFF",
        "INFRASTRUCTURE_BINDING_MISMATCH",
    )
    for key in (
        "real_network_execution",
        "live_provider_execution",
        "external_effect_enabled",
        "spend_enabled",
        "protected_keirin_data_enabled",
        "production_credentials_enabled",
        "production_deployment_enabled",
        "runtime_activation",
    ):
        _require(infrastructure_seal[key] is False, "INFRASTRUCTURE_AUTHORITY_NOT_FALSE")

    _require(
        remote_single["issue"] == 122
        and remote_single["target_class"]
        == "RENDER_REMOTE_PREPRODUCTION_SINGLE_SERVICE_NO_EFFECT_v1"
        and remote_single["environment_class"] == "PRE_PRODUCTION"
        and remote_single["postgres_id"] == contract["target_contract"]["shared_postgres_id"]
        and remote_single["spend"]["incremental_monetary_spend_ceiling_usd"] == 0
        and remote_single["runtime"] == "OFF",
        "REMOTE_SINGLE_BINDING_MISMATCH",
    )
    _require_false_map(remote_single["authority"], "REMOTE_SINGLE_AUTHORITY_NOT_FALSE")

    _require(
        multi_prep["canonical_main"] == CANONICAL_MAIN
        and multi_prep["adopted_single_host_head"]
        == contract["materialized_subtrees"]["remote_preprod_render_v1"]["source_commit"]
        and multi_prep["excluded_later_pr123_head"]
        == contract["materialized_subtrees"]["remote_preprod_render_v1"][
            "explicitly_excludes_later_pr123_head"
        ]
        and multi_prep["topology_class"] == contract["target_contract"]["topology_class"]
        and multi_prep["environment_class"] == "PRE_PRODUCTION"
        and multi_prep["runtime"] == "OFF",
        "MULTI_PREP_BINDING_MISMATCH",
    )
    _require_false_map(multi_prep["authority"], "MULTI_PREP_AUTHORITY_NOT_FALSE")
    _require_false_map(
        multi_prep_seal["authority"], "MULTI_PREP_SEAL_AUTHORITY_NOT_FALSE"
    )

    _require(
        multi_real["canonical_main"] == CANONICAL_MAIN
        and multi_real["target_class"] == contract["target_contract"]["topology_class"]
        and multi_real["environment_class"] == "PRE_PRODUCTION"
        and multi_real["shared_postgres"]["id"]
        == contract["target_contract"]["shared_postgres_id"]
        and multi_real["workers"]["worker-a"]["service_id"]
        == contract["target_contract"]["worker_a_service_id"]
        and multi_real["workers"]["worker-b"]["service_id"]
        == contract["target_contract"]["worker_b_service_id"]
        and multi_real["runtime"] == "OFF",
        "MULTI_REAL_BINDING_MISMATCH",
    )
    _require_false_map(multi_real["authority"], "MULTI_REAL_AUTHORITY_NOT_FALSE")
    _require_false_map(
        multi_real_seal["authority"], "MULTI_REAL_SEAL_AUTHORITY_NOT_FALSE"
    )

    drill = multi_real["drill"]
    _require(
        drill["phase"] == "COMPLETE"
        and drill["current_owner"] == "worker-a"
        and drill["current_fence_token"] == 3
        and drill["operation_count"] == 1
        and drill["simulated_effect_count"] == 1
        and drill["duplicate_external_effect"] is False
        and drill["fatal_error_present"] is False,
        "DISTRIBUTED_SAFETY_RECEIPT_MISMATCH",
    )
    _require(
        multi_real_seal["successful_v2"]["fence_sequence"] == [1, 2, 3],
        "FENCE_SEQUENCE_MISMATCH",
    )
    _require(
        all(drill["events"].values()),
        "DISTRIBUTED_SAFETY_EVENT_MISSING",
    )
    _require(
        multi_real["incremental_spend_ceiling_usd"] == 0,
        "SPEND_CEILING_MISMATCH",
    )

    _require(
        ledger["runtime"] == "OFF"
        and ledger["real_multi_host"]["final_auditor_pass"] == 5554934917
        and ledger["real_multi_host"]["final_t2_pass"] == 5554935885,
        "PROVENANCE_LEDGER_MISMATCH",
    )

    integration = contract["integration_boundary"]
    _require(
        integration["convergence_status"] == "PREPARATION_NOT_ACTIVATABLE"
        and integration["runtime_control_store"] == "LOCAL_SQLITE_SEALED"
        and integration["distributed_fencing_evidence_store"] == "RENDER_POSTGRESQL"
        and integration["distributed_state_provider_id"]
        == contract["target_contract"]["shared_postgres_id"]
        and integration["provider_effect_adapter_enabled"] is False
        and integration["runtime_activation_bridge_enabled"] is False
        and integration["canonical_merge_completed"] is False
        and integration["activation_integration_required"] is True,
        "INTEGRATION_BOUNDARY_MISMATCH",
    )
    _require(
        contract["readiness"]["independent_review_ready"] is True
        and contract["readiness"]["runtime_activation_ready"] is False,
        "READINESS_BOUNDARY_MISMATCH",
    )

    return {
        "schema": "MULTIVERSE_RUNTIME_CONVERGENCE_RECEIPT_v1",
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "canonical_main": CANONICAL_MAIN,
        "proof_ceiling": PROOF,
        "runtime": "OFF",
        "activation_ready": False,
        "integration_state": "PREPARATION_NOT_ACTIVATABLE",
        "target": {
            "environment_class": "PRE_PRODUCTION",
            "topology_class": contract["target_contract"]["topology_class"],
            "worker_ids": contract["target_contract"]["worker_ids"],
            "shared_postgres_id": contract["target_contract"]["shared_postgres_id"],
        },
        "distributed_safety": {
            "fence_sequence": [1, 2, 3],
            "operation_count": 1,
            "duplicate_external_effect": False,
        },
        "authority": contract["authority"],
    }
