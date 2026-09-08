from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.aggregator import (
    aggregate_results_v2,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.pilot_matrix import (
    build_provider_pilot_matrix,
    provider_pilot_matrix_sha256,
)

DUAL_PROVIDER_SCHEMA = "MULTIVERSE_DUAL_PROVIDER_OFFLINE_RESEARCH_v1"

DUAL_PROVIDER_KEYS = {
    "schema",
    "research_id",
    "claim_key",
    "provider_count",
    "provider_model_count",
    "gemini_model_id",
    "claude_model_id",
    "provider_neutral_prompt_sha256",
    "gemini_matrix_sha256",
    "claude_matrix_sha256",
    "gemini_result_sha256",
    "claude_result_sha256",
    "aggregate_sha256",
    "agreement_aggregate_sha256",
    "agreement_descriptive_label",
    "agreement_cross_model_divergence",
    "agreement_cross_provider_divergence",
    "agreement_unresolved_divergence_count",
    "refusal_aggregate_sha256",
    "refusal_descriptive_label",
    "refusal_cross_model_divergence",
    "refusal_cross_provider_divergence",
    "refusal_observed_provider_count",
    "refusal_completed_provider_count",
    "refusal_noncompleted_result_count",
    "refusal_refused_status_count",
    "refusal_unresolved_divergence_count",
    "descriptive_label",
    "cross_model_divergence",
    "cross_provider_divergence",
    "role_conditioned_divergence",
    "unresolved_divergence_status",
    "required_next_action",
    "majority_confers_truth",
    "vote_confers_authority",
    "synthetic_only",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_provider_execution",
    "adoption_authority",
    "runtime",
}


def _synthetic_evidence(task: dict[str, Any]) -> dict[str, Any]:
    manifest = task.get("evidence_manifest")
    require(
        isinstance(manifest, list) and bool(manifest),
        "DUAL_PROVIDER_EVIDENCE_MANIFEST",
    )
    for item in manifest:
        if (
            isinstance(item, dict)
            and item.get("primitive") == "NORMALIZED_JSON_SHA256"
            and isinstance(item.get("ref"), str)
            and isinstance(item.get("sha256"), str)
        ):
            return {
                "primitive": item["primitive"],
                "ref": item["ref"],
                "sha256": item["sha256"],
            }
    raise RuntimeError("DUAL_PROVIDER_SYNTHETIC_EVIDENCE_REQUIRED")


def _result(
    task: dict[str, Any],
    matrix: dict[str, Any],
    *,
    submission_id: str,
    position: str,
    assertion: str,
    claim_key: str,
    status: str = "COMPLETED",
) -> dict[str, Any]:
    assignment = matrix["assignment"]
    return {
        "schema": "MULTIVERSE_RESEARCH_RESULT_v1",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "submission_id": submission_id,
        "snapshot_id": task["snapshot_id"],
        "produced_at": matrix["assignment"]["created_at"],
        "model_identity": {
            "provider": assignment["target_provider"],
            "model": assignment["target_model"],
            "role": assignment["requested_role"],
        },
        "status": status,
        "findings": [
            {
                "finding_id": f"{submission_id}-finding-001",
                "claim_key": claim_key,
                "position": position,
                "severity": "INFO",
                "assertion": assertion,
                "evidence": _synthetic_evidence(task),
                "confidence": 0.5,
                "uncertainty":
                    "Synthetic disagreement fixture only; no live provider.",
                "recommendation":
                    "Route unresolved cross-provider disagreement to mechanical falsification.",
                "validation_plan":
                    "Run an independently specified falsification task.",
            }
        ],
        "uncertainty_factors": [
            "Synthetic provider positions are intentionally opposed."
        ],
        "nonauthority": dict(task["nonauthority"]),
    }


def _refusal_control(
    task: dict[str, Any],
    gemini: dict[str, Any],
    claude: dict[str, Any],
    gemini_result: dict[str, Any],
    claim_key: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claude_refusal_result = _result(
        task,
        claude,
        submission_id="dual-provider-claude-refusal-001",
        position="OPPOSE",
        assertion="Synthetic Claude refusal carries no completed opinion.",
        claim_key=claim_key,
        status="REFUSED",
    )
    refusal_aggregate = aggregate_results_v2(
        task,
        [gemini_result, claude_refusal_result],
    )
    refusal_claims = [
        item
        for item in refusal_aggregate["claims"]
        if item["claim_key"] == claim_key
    ]
    require(len(refusal_claims) == 1, "DUAL_PROVIDER_REFUSAL_CLAIM_COUNT")
    refusal_claim = refusal_claims[0]
    require(
        refusal_claim["descriptive_label"] == "SUPPORT_ONLY",
        "DUAL_PROVIDER_REFUSAL_LABEL",
    )
    require(
        refusal_claim["cross_model_divergence"] is False,
        "DUAL_PROVIDER_REFUSAL_CROSS_MODEL",
    )
    require(
        refusal_claim["cross_provider_divergence"] is False,
        "DUAL_PROVIDER_REFUSAL_CROSS_PROVIDER",
    )
    require(
        refusal_aggregate["observed_unique_provider_count"] == 2,
        "DUAL_PROVIDER_REFUSAL_OBSERVED_PROVIDER_COUNT",
    )
    require(
        refusal_aggregate["completed_unique_provider_count"] == 1,
        "DUAL_PROVIDER_REFUSAL_COMPLETED_PROVIDER_COUNT",
    )
    require(
        len(refusal_aggregate["noncompleted_results"]) == 1,
        "DUAL_PROVIDER_REFUSAL_NONCOMPLETED_COUNT",
    )
    require(
        refusal_aggregate["status_counts"]["REFUSED"] == 1,
        "DUAL_PROVIDER_REFUSAL_STATUS_COUNT",
    )
    require(
        refusal_aggregate["unresolved_divergences"] == [],
        "DUAL_PROVIDER_REFUSAL_UNRESOLVED",
    )
    return claude_refusal_result, refusal_aggregate, refusal_claim


def build_dual_provider_offline_research(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    role = "architecture_challenge"
    require(
        role in task["requested_roles"],
        "DUAL_PROVIDER_ROLE_NOT_REQUESTED",
    )
    gemini = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        "GOOGLE_GEMINI",
        response_schema,
        requested_role=role,
    )
    claude = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        "ANTHROPIC_CLAUDE",
        response_schema,
        requested_role=role,
    )
    require(
        gemini["prompt"] == claude["prompt"],
        "DUAL_PROVIDER_PROMPT_MISMATCH",
    )

    claim_key = "dual-provider-synthetic-disagreement"
    gemini_result = _result(
        task,
        gemini,
        submission_id="dual-provider-gemini-001",
        position="SUPPORT",
        assertion="Synthetic Gemini position supports the test claim.",
        claim_key=claim_key,
    )
    claude_result = _result(
        task,
        claude,
        submission_id="dual-provider-claude-001",
        position="OPPOSE",
        assertion="Synthetic Claude position opposes the test claim.",
        claim_key=claim_key,
    )
    aggregate = aggregate_results_v2(
        task,
        [gemini_result, claude_result],
    )
    require(
        aggregate["completed_unique_provider_count"] == 2,
        "DUAL_PROVIDER_COMPLETED_PROVIDER_COUNT",
    )
    require(
        aggregate["completed_unique_provider_model_count"] == 2,
        "DUAL_PROVIDER_COMPLETED_PROVIDER_MODEL_COUNT",
    )
    claims = [
        item
        for item in aggregate["claims"]
        if item["claim_key"] == claim_key
    ]
    require(len(claims) == 1, "DUAL_PROVIDER_CLAIM_COUNT")
    claim = claims[0]
    require(
        claim["descriptive_label"] == "DIVERGENT",
        "DUAL_PROVIDER_DESCRIPTIVE_LABEL",
    )
    require(
        claim["cross_model_divergence"] is True,
        "DUAL_PROVIDER_CROSS_MODEL_DIVERGENCE",
    )
    require(
        claim["cross_provider_divergence"] is True,
        "DUAL_PROVIDER_CROSS_PROVIDER_DIVERGENCE",
    )
    require(
        claim["role_conditioned_divergence"] is False,
        "DUAL_PROVIDER_ROLE_CONDITIONED_DIVERGENCE",
    )
    unresolved = [
        item
        for item in aggregate["unresolved_divergences"]
        if item["claim_key"] == claim_key
    ]
    require(len(unresolved) == 1, "DUAL_PROVIDER_UNRESOLVED_COUNT")
    divergence = unresolved[0]
    require(
        divergence["status"] == "UNRESOLVED_DIVERGENCE",
        "DUAL_PROVIDER_UNRESOLVED_STATUS",
    )
    require(
        divergence["required_next_action"]
        == "MECHANICAL_FALSIFICATION_TASK",
        "DUAL_PROVIDER_REQUIRED_NEXT_ACTION",
    )
    require(
        claim["majority_confers_truth"] is False,
        "DUAL_PROVIDER_MAJORITY_TRUTH_FORBIDDEN",
    )
    require(
        claim["vote_confers_authority"] is False,
        "DUAL_PROVIDER_VOTE_AUTHORITY_FORBIDDEN",
    )

    claude_agreement_result = _result(
        task,
        claude,
        submission_id="dual-provider-claude-agreement-001",
        position="SUPPORT",
        assertion="Synthetic Claude agreement position supports the test claim.",
        claim_key=claim_key,
    )
    agreement_aggregate = aggregate_results_v2(
        task,
        [gemini_result, claude_agreement_result],
    )
    agreement_claim = [
        item
        for item in agreement_aggregate["claims"]
        if item["claim_key"] == claim_key
    ][0]
    require(
        agreement_claim["descriptive_label"] == "SUPPORT_ONLY",
        "DUAL_PROVIDER_AGREEMENT_LABEL",
    )
    require(
        agreement_claim["cross_model_divergence"] is False,
        "DUAL_PROVIDER_AGREEMENT_CROSS_MODEL",
    )
    require(
        agreement_claim["cross_provider_divergence"] is False,
        "DUAL_PROVIDER_AGREEMENT_CROSS_PROVIDER",
    )
    require(
        agreement_aggregate["unresolved_divergences"] == [],
        "DUAL_PROVIDER_AGREEMENT_UNRESOLVED",
    )

    (
        claude_refusal_result,
        refusal_aggregate,
        refusal_claim,
    ) = _refusal_control(
        task,
        gemini,
        claude,
        gemini_result,
        claim_key,
    )

    record = {
        "schema": DUAL_PROVIDER_SCHEMA,
        "research_id": "dual-provider-offline-research-001",
        "claim_key": claim_key,
        "provider_count": 2,
        "provider_model_count": 2,
        "gemini_model_id": gemini["assignment"]["target_model"],
        "claude_model_id": claude["assignment"]["target_model"],
        "provider_neutral_prompt_sha256":
            sha256_json(gemini["prompt"]),
        "gemini_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                gemini,
            ),
        "claude_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                claude,
            ),
        "gemini_result_sha256": sha256_json(gemini_result),
        "claude_result_sha256": sha256_json(claude_result),
        "aggregate_sha256": aggregate["aggregate_sha256"],
        "agreement_aggregate_sha256":
            agreement_aggregate["aggregate_sha256"],
        "agreement_descriptive_label":
            agreement_claim["descriptive_label"],
        "agreement_cross_model_divergence":
            agreement_claim["cross_model_divergence"],
        "agreement_cross_provider_divergence":
            agreement_claim["cross_provider_divergence"],
        "agreement_unresolved_divergence_count":
            len(agreement_aggregate["unresolved_divergences"]),
        "refusal_aggregate_sha256":
            refusal_aggregate["aggregate_sha256"],
        "refusal_descriptive_label":
            refusal_claim["descriptive_label"],
        "refusal_cross_model_divergence":
            refusal_claim["cross_model_divergence"],
        "refusal_cross_provider_divergence":
            refusal_claim["cross_provider_divergence"],
        "refusal_observed_provider_count":
            refusal_aggregate["observed_unique_provider_count"],
        "refusal_completed_provider_count":
            refusal_aggregate["completed_unique_provider_count"],
        "refusal_noncompleted_result_count":
            len(refusal_aggregate["noncompleted_results"]),
        "refusal_refused_status_count":
            refusal_aggregate["status_counts"]["REFUSED"],
        "refusal_unresolved_divergence_count":
            len(refusal_aggregate["unresolved_divergences"]),
        "refusal_aggregate_sha256":
            refusal_aggregate["aggregate_sha256"],
        "refusal_descriptive_label":
            refusal_claim["descriptive_label"],
        "refusal_cross_model_divergence":
            refusal_claim["cross_model_divergence"],
        "refusal_cross_provider_divergence":
            refusal_claim["cross_provider_divergence"],
        "refusal_observed_provider_count":
            refusal_aggregate["observed_unique_provider_count"],
        "refusal_completed_provider_count":
            refusal_aggregate["completed_unique_provider_count"],
        "refusal_noncompleted_result_count":
            len(refusal_aggregate["noncompleted_results"]),
        "refusal_refused_status_count":
            refusal_aggregate["status_counts"]["REFUSED"],
        "refusal_unresolved_divergence_count":
            len(refusal_aggregate["unresolved_divergences"]),
        "descriptive_label": claim["descriptive_label"],
        "cross_model_divergence": claim["cross_model_divergence"],
        "cross_provider_divergence":
            claim["cross_provider_divergence"],
        "role_conditioned_divergence":
            claim["role_conditioned_divergence"],
        "unresolved_divergence_status": divergence["status"],
        "required_next_action": divergence["required_next_action"],
        "majority_confers_truth": claim["majority_confers_truth"],
        "vote_confers_authority": claim["vote_confers_authority"],
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }
    return validate_dual_provider_offline_research(
        task,
        catalog_snapshot,
        response_schema,
        record,
    )


def build_dual_provider_offline_research_unchecked(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    role = "architecture_challenge"
    gemini = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        "GOOGLE_GEMINI",
        response_schema,
        requested_role=role,
    )
    claude = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        "ANTHROPIC_CLAUDE",
        response_schema,
        requested_role=role,
    )
    require(
        gemini["prompt"] == claude["prompt"],
        "DUAL_PROVIDER_PROMPT_MISMATCH",
    )
    claim_key = "dual-provider-synthetic-disagreement"
    gemini_result = _result(
        task,
        gemini,
        submission_id="dual-provider-gemini-001",
        position="SUPPORT",
        assertion="Synthetic Gemini position supports the test claim.",
        claim_key=claim_key,
    )
    claude_result = _result(
        task,
        claude,
        submission_id="dual-provider-claude-001",
        position="OPPOSE",
        assertion="Synthetic Claude position opposes the test claim.",
        claim_key=claim_key,
    )
    aggregate = aggregate_results_v2(
        task,
        [gemini_result, claude_result],
    )
    claim = [
        item for item in aggregate["claims"]
        if item["claim_key"] == claim_key
    ][0]
    divergence = [
        item for item in aggregate["unresolved_divergences"]
        if item["claim_key"] == claim_key
    ][0]
    claude_agreement_result = _result(
        task,
        claude,
        submission_id="dual-provider-claude-agreement-001",
        position="SUPPORT",
        assertion="Synthetic Claude agreement position supports the test claim.",
        claim_key=claim_key,
    )
    agreement_aggregate = aggregate_results_v2(
        task,
        [gemini_result, claude_agreement_result],
    )
    agreement_claim = [
        item for item in agreement_aggregate["claims"]
        if item["claim_key"] == claim_key
    ][0]
    (
        claude_refusal_result,
        refusal_aggregate,
        refusal_claim,
    ) = _refusal_control(
        task,
        gemini,
        claude,
        gemini_result,
        claim_key,
    )
    return {
        "schema": DUAL_PROVIDER_SCHEMA,
        "research_id": "dual-provider-offline-research-001",
        "claim_key": claim_key,
        "provider_count":
            aggregate["completed_unique_provider_count"],
        "provider_model_count":
            aggregate["completed_unique_provider_model_count"],
        "gemini_model_id": gemini["assignment"]["target_model"],
        "claude_model_id": claude["assignment"]["target_model"],
        "provider_neutral_prompt_sha256":
            sha256_json(gemini["prompt"]),
        "gemini_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                gemini,
            ),
        "claude_matrix_sha256":
            provider_pilot_matrix_sha256(
                task,
                catalog_snapshot,
                response_schema,
                claude,
            ),
        "gemini_result_sha256": sha256_json(gemini_result),
        "claude_result_sha256": sha256_json(claude_result),
        "aggregate_sha256": aggregate["aggregate_sha256"],
        "agreement_aggregate_sha256":
            agreement_aggregate["aggregate_sha256"],
        "agreement_descriptive_label":
            agreement_claim["descriptive_label"],
        "agreement_cross_model_divergence":
            agreement_claim["cross_model_divergence"],
        "agreement_cross_provider_divergence":
            agreement_claim["cross_provider_divergence"],
        "agreement_unresolved_divergence_count":
            len(agreement_aggregate["unresolved_divergences"]),
        "descriptive_label": claim["descriptive_label"],
        "cross_model_divergence": claim["cross_model_divergence"],
        "cross_provider_divergence":
            claim["cross_provider_divergence"],
        "role_conditioned_divergence":
            claim["role_conditioned_divergence"],
        "unresolved_divergence_status": divergence["status"],
        "required_next_action": divergence["required_next_action"],
        "majority_confers_truth": claim["majority_confers_truth"],
        "vote_confers_authority": claim["vote_confers_authority"],
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


def validate_dual_provider_offline_research(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(record, dict)
        and set(record) == DUAL_PROVIDER_KEYS,
        "DUAL_PROVIDER_SCHEMA_KEYS",
    )
    require(
        record["schema"] == DUAL_PROVIDER_SCHEMA,
        "DUAL_PROVIDER_SCHEMA_VERSION",
    )
    expected = build_dual_provider_offline_research_unchecked(
        task,
        catalog_snapshot,
        response_schema,
    )
    require(
        record == expected,
        "DUAL_PROVIDER_EXACT_MISMATCH",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_provider_execution",
        "adoption_authority",
    ):
        require(
            record[key] is False,
            f"DUAL_PROVIDER_FORBIDDEN_TRUE:{key}",
        )
    require(
        record["runtime"] == "OFF",
        "DUAL_PROVIDER_RUNTIME_NOT_OFF",
    )
    return record


def dual_provider_offline_research_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_dual_provider_offline_research(
        task,
        catalog_snapshot,
        response_schema,
        record,
    )
    return sha256_json(record)
