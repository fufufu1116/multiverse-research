from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
)
from automation.multimodel_research_v1.fanout import (
    fanout_plan_sha256,
    summarize_fanout_results,
    validate_fanout_plan,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.pilot_matrix import (
    build_provider_pilot_matrix,
    provider_pilot_matrix_sha256,
)

DUAL_FANOUT_SCHEMA = "MULTIVERSE_DUAL_PROVIDER_FANOUT_REHEARSAL_v1"

DUAL_FANOUT_KEYS = {
    "schema",
    "rehearsal_id",
    "provider_count",
    "provider_model_count",
    "gemini_model_id",
    "claude_model_id",
    "provider_neutral_prompt_sha256",
    "gemini_matrix_sha256",
    "claude_matrix_sha256",
    "gemini_assignment_sha256",
    "claude_assignment_sha256",
    "fanout_plan_sha256",
    "full_batch_sha256",
    "full_planned_assignment_count",
    "full_observed_terminal_result_count",
    "full_completed_assignment_count",
    "full_missing_assignment_count",
    "full_all_planned_observed",
    "full_all_planned_completed",
    "missing_demo_batch_sha256",
    "missing_demo_observed_terminal_result_count",
    "missing_demo_completed_assignment_count",
    "missing_demo_missing_assignment_count",
    "missing_demo_all_planned_observed",
    "missing_demo_all_planned_completed",
    "failure_demo_batch_sha256",
    "failure_demo_observed_terminal_result_count",
    "failure_demo_completed_assignment_count",
    "failure_demo_noncompleted_assignment_count",
    "failure_demo_missing_assignment_count",
    "failure_demo_refused_count",
    "failure_demo_all_planned_observed",
    "failure_demo_all_planned_completed",
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
        "DUAL_FANOUT_EVIDENCE_MANIFEST",
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
    raise RuntimeError("DUAL_FANOUT_SYNTHETIC_EVIDENCE_REQUIRED")


def _result_v2(
    task: dict[str, Any],
    assignment: dict[str, Any],
    *,
    submission_id: str,
    status: str = "COMPLETED",
) -> dict[str, Any]:
    return {
        "schema": "MULTIVERSE_RESEARCH_RESULT_v2",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "submission_id": submission_id,
        "snapshot_id": task["snapshot_id"],
        "produced_at": assignment["created_at"],
        "model_identity": {
            "provider": assignment["target_provider"],
            "model": assignment["target_model"],
            "role": assignment["requested_role"],
        },
        "status": status,
        "findings": (
            [
                {
                    "finding_id": f"{submission_id}-finding-001",
                    "claim_key": "dual-provider-fanout-completion",
                    "position": "UNKNOWN",
                    "severity": "INFO",
                    "assertion":
                        "Synthetic terminal result returned for planned assignment.",
                    "evidence": _synthetic_evidence(task),
                    "confidence": 0.5,
                    "uncertainty":
                        "Synthetic completion fixture only; no live provider.",
                    "recommendation":
                        "Require all planned assignments before complete-batch claims.",
                    "validation_plan":
                        "Compare planned and observed assignment SHA256 sets.",
                }
            ]
            if status == "COMPLETED"
            else []
        ),
        "uncertainty_factors": [
            "Synthetic result used only to exercise fanout accounting."
        ],
        "nonauthority": dict(task["nonauthority"]),
        "assignment_sha256": assignment_sha256(task, assignment),
    }


def _build_inputs(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    role = "architecture_challenge"
    require(
        role in task["requested_roles"],
        "DUAL_FANOUT_ROLE_NOT_REQUESTED",
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
        "DUAL_FANOUT_PROMPT_MISMATCH",
    )
    assignments = [
        gemini["assignment"],
        claude["assignment"],
    ]
    plan = {
        "schema": "MULTIVERSE_RESEARCH_FANOUT_PLAN_v1",
        "plan_id": "dual-provider-fanout-001",
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "created_at": catalog_snapshot["observed_at"],
        "assignment_sha256s": sorted(
            assignment_sha256(task, item)
            for item in assignments
        ),
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_fanout_plan(task, assignments, plan)

    gemini_result = _result_v2(
        task,
        gemini["assignment"],
        submission_id="dual-fanout-gemini-result-001",
    )
    claude_result = _result_v2(
        task,
        claude["assignment"],
        submission_id="dual-fanout-claude-result-001",
    )

    full_summary = summarize_fanout_results(
        task,
        assignments,
        plan,
        [gemini_result, claude_result],
    )
    missing_summary = summarize_fanout_results(
        task,
        assignments,
        plan,
        [gemini_result],
    )
    claude_refused_result = _result_v2(
        task,
        claude["assignment"],
        submission_id="dual-fanout-claude-refused-001",
        status="REFUSED",
    )
    failure_summary = summarize_fanout_results(
        task,
        assignments,
        plan,
        [gemini_result, claude_refused_result],
    )

    require(
        full_summary["planned_assignment_count"] == 2,
        "DUAL_FANOUT_FULL_PLANNED_COUNT",
    )
    require(
        full_summary["observed_terminal_result_count"] == 2,
        "DUAL_FANOUT_FULL_OBSERVED_COUNT",
    )
    require(
        full_summary["completed_assignment_count"] == 2,
        "DUAL_FANOUT_FULL_COMPLETED_COUNT",
    )
    require(
        full_summary["missing_assignment_sha256s"] == [],
        "DUAL_FANOUT_FULL_MISSING",
    )
    require(
        full_summary["all_planned_observed"] is True,
        "DUAL_FANOUT_FULL_OBSERVED_FLAG",
    )
    require(
        full_summary["all_planned_completed"] is True,
        "DUAL_FANOUT_FULL_COMPLETED_FLAG",
    )

    require(
        missing_summary["observed_terminal_result_count"] == 1,
        "DUAL_FANOUT_MISSING_OBSERVED_COUNT",
    )
    require(
        missing_summary["completed_assignment_count"] == 1,
        "DUAL_FANOUT_MISSING_COMPLETED_COUNT",
    )
    require(
        len(missing_summary["missing_assignment_sha256s"]) == 1,
        "DUAL_FANOUT_MISSING_ASSIGNMENT_COUNT",
    )
    require(
        missing_summary["all_planned_observed"] is False,
        "DUAL_FANOUT_MISSING_OBSERVED_FLAG",
    )
    require(
        missing_summary["all_planned_completed"] is False,
        "DUAL_FANOUT_MISSING_COMPLETED_FLAG",
    )
    require(
        failure_summary["observed_terminal_result_count"] == 2,
        "DUAL_FANOUT_FAILURE_OBSERVED_COUNT",
    )
    require(
        failure_summary["completed_assignment_count"] == 1,
        "DUAL_FANOUT_FAILURE_COMPLETED_COUNT",
    )
    require(
        failure_summary["noncompleted_assignment_count"] == 1,
        "DUAL_FANOUT_FAILURE_NONCOMPLETED_COUNT",
    )
    require(
        failure_summary["missing_assignment_sha256s"] == [],
        "DUAL_FANOUT_FAILURE_MISSING",
    )
    require(
        failure_summary["status_counts"]["REFUSED"] == 1,
        "DUAL_FANOUT_FAILURE_REFUSED_COUNT",
    )
    require(
        failure_summary["all_planned_observed"] is True,
        "DUAL_FANOUT_FAILURE_OBSERVED_FLAG",
    )
    require(
        failure_summary["all_planned_completed"] is False,
        "DUAL_FANOUT_FAILURE_COMPLETED_FLAG",
    )
    return {
        "gemini": gemini,
        "claude": claude,
        "assignments": assignments,
        "plan": plan,
        "full_summary": full_summary,
        "missing_summary": missing_summary,
        "failure_summary": failure_summary,
    }


def build_dual_provider_fanout_rehearsal(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    values = _build_inputs(
        task,
        catalog_snapshot,
        response_schema,
    )
    gemini = values["gemini"]
    claude = values["claude"]
    plan = values["plan"]
    full = values["full_summary"]
    missing = values["missing_summary"]
    failure = values["failure_summary"]
    record = {
        "schema": DUAL_FANOUT_SCHEMA,
        "rehearsal_id": "dual-provider-fanout-rehearsal-001",
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
        "gemini_assignment_sha256":
            assignment_sha256(task, gemini["assignment"]),
        "claude_assignment_sha256":
            assignment_sha256(task, claude["assignment"]),
        "fanout_plan_sha256":
            fanout_plan_sha256(
                task,
                values["assignments"],
                plan,
            ),
        "full_batch_sha256": full["batch_sha256"],
        "full_planned_assignment_count":
            full["planned_assignment_count"],
        "full_observed_terminal_result_count":
            full["observed_terminal_result_count"],
        "full_completed_assignment_count":
            full["completed_assignment_count"],
        "full_missing_assignment_count":
            len(full["missing_assignment_sha256s"]),
        "full_all_planned_observed":
            full["all_planned_observed"],
        "full_all_planned_completed":
            full["all_planned_completed"],
        "missing_demo_batch_sha256": missing["batch_sha256"],
        "missing_demo_observed_terminal_result_count":
            missing["observed_terminal_result_count"],
        "missing_demo_completed_assignment_count":
            missing["completed_assignment_count"],
        "missing_demo_missing_assignment_count":
            len(missing["missing_assignment_sha256s"]),
        "missing_demo_all_planned_observed":
            missing["all_planned_observed"],
        "missing_demo_all_planned_completed":
            missing["all_planned_completed"],
        "failure_demo_batch_sha256": failure["batch_sha256"],
        "failure_demo_observed_terminal_result_count":
            failure["observed_terminal_result_count"],
        "failure_demo_completed_assignment_count":
            failure["completed_assignment_count"],
        "failure_demo_noncompleted_assignment_count":
            failure["noncompleted_assignment_count"],
        "failure_demo_missing_assignment_count":
            len(failure["missing_assignment_sha256s"]),
        "failure_demo_refused_count":
            failure["status_counts"]["REFUSED"],
        "failure_demo_all_planned_observed":
            failure["all_planned_observed"],
        "failure_demo_all_planned_completed":
            failure["all_planned_completed"],
        "failure_demo_batch_sha256": failure["batch_sha256"],
        "failure_demo_observed_terminal_result_count":
            failure["observed_terminal_result_count"],
        "failure_demo_completed_assignment_count":
            failure["completed_assignment_count"],
        "failure_demo_noncompleted_assignment_count":
            failure["noncompleted_assignment_count"],
        "failure_demo_missing_assignment_count":
            len(failure["missing_assignment_sha256s"]),
        "failure_demo_refused_count":
            failure["status_counts"]["REFUSED"],
        "failure_demo_all_planned_observed":
            failure["all_planned_observed"],
        "failure_demo_all_planned_completed":
            failure["all_planned_completed"],
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }
    return validate_dual_provider_fanout_rehearsal(
        task,
        catalog_snapshot,
        response_schema,
        record,
    )


def build_dual_provider_fanout_rehearsal_unchecked(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    values = _build_inputs(task, catalog_snapshot, response_schema)
    gemini = values["gemini"]
    claude = values["claude"]
    full = values["full_summary"]
    missing = values["missing_summary"]
    failure = values["failure_summary"]
    return {
        "schema": DUAL_FANOUT_SCHEMA,
        "rehearsal_id": "dual-provider-fanout-rehearsal-001",
        "provider_count": 2,
        "provider_model_count": 2,
        "gemini_model_id": gemini["assignment"]["target_model"],
        "claude_model_id": claude["assignment"]["target_model"],
        "provider_neutral_prompt_sha256":
            sha256_json(gemini["prompt"]),
        "gemini_matrix_sha256":
            provider_pilot_matrix_sha256(
                task, catalog_snapshot, response_schema, gemini
            ),
        "claude_matrix_sha256":
            provider_pilot_matrix_sha256(
                task, catalog_snapshot, response_schema, claude
            ),
        "gemini_assignment_sha256":
            assignment_sha256(task, gemini["assignment"]),
        "claude_assignment_sha256":
            assignment_sha256(task, claude["assignment"]),
        "fanout_plan_sha256":
            fanout_plan_sha256(
                task, values["assignments"], values["plan"]
            ),
        "full_batch_sha256": full["batch_sha256"],
        "full_planned_assignment_count":
            full["planned_assignment_count"],
        "full_observed_terminal_result_count":
            full["observed_terminal_result_count"],
        "full_completed_assignment_count":
            full["completed_assignment_count"],
        "full_missing_assignment_count":
            len(full["missing_assignment_sha256s"]),
        "full_all_planned_observed":
            full["all_planned_observed"],
        "full_all_planned_completed":
            full["all_planned_completed"],
        "missing_demo_batch_sha256": missing["batch_sha256"],
        "missing_demo_observed_terminal_result_count":
            missing["observed_terminal_result_count"],
        "missing_demo_completed_assignment_count":
            missing["completed_assignment_count"],
        "missing_demo_missing_assignment_count":
            len(missing["missing_assignment_sha256s"]),
        "missing_demo_all_planned_observed":
            missing["all_planned_observed"],
        "missing_demo_all_planned_completed":
            missing["all_planned_completed"],
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


def validate_dual_provider_fanout_rehearsal(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(record, dict)
        and set(record) == DUAL_FANOUT_KEYS,
        "DUAL_FANOUT_SCHEMA_KEYS",
    )
    require(
        record["schema"] == DUAL_FANOUT_SCHEMA,
        "DUAL_FANOUT_SCHEMA_VERSION",
    )
    expected = build_dual_provider_fanout_rehearsal_unchecked(
        task,
        catalog_snapshot,
        response_schema,
    )
    require(
        record == expected,
        "DUAL_FANOUT_EXACT_MISMATCH",
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
            f"DUAL_FANOUT_FORBIDDEN_TRUE:{key}",
        )
    require(record["runtime"] == "OFF", "DUAL_FANOUT_RUNTIME_NOT_OFF")
    return record


def dual_provider_fanout_rehearsal_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_dual_provider_fanout_rehearsal(
        task,
        catalog_snapshot,
        response_schema,
        record,
    )
    return sha256_json(record)
