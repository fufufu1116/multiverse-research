from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
    validate_result_v2_for_assignment,
)
from automation.multimodel_research_v1.model import (
    NONAUTHORITY_KEYS,
    RESULT_STATUSES,
    require,
    sha256_json,
    validate_task,
)

FANOUT_PLAN_SCHEMA = "MULTIVERSE_RESEARCH_FANOUT_PLAN_v1"
BATCH_SUMMARY_SCHEMA = "MULTIVERSE_RESEARCH_BATCH_SUMMARY_v1"

FANOUT_PLAN_KEYS = {
    "schema",
    "plan_id",
    "task_sha256",
    "snapshot_id",
    "created_at",
    "assignment_sha256s",
    "nonauthority",
}


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}",
                value,
            )
        ),
        code,
    )
    return value


def _parse_utc(value: Any, code: str) -> datetime:
    require(
        isinstance(value, str)
        and bool(
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                value,
            )
        ),
        code,
    )
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(code) from exc


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "FANOUT_NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(
            flag is False,
            f"FANOUT_NONAUTHORITY_NOT_FALSE:{key}",
        )
    return value


def validate_fanout_plan(
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    plan: dict[str, Any],
) -> dict[str, Any]:
    validate_task(task)
    require(
        isinstance(assignments, list)
        and bool(assignments),
        "FANOUT_ASSIGNMENTS_REQUIRED",
    )
    require(
        len(assignments) <= 64,
        "FANOUT_ASSIGNMENTS_LIMIT",
    )

    assignment_ids: set[str] = set()
    logical_targets: set[tuple[str, str, str]] = set()
    hashes: list[str] = []
    assignment_created_times: list[datetime] = []

    for item in assignments:
        validate_assignment(task, item)
        assignment_id = item["assignment_id"]
        require(
            assignment_id not in assignment_ids,
            "DUPLICATE_FANOUT_ASSIGNMENT_ID",
        )
        assignment_ids.add(assignment_id)

        logical_target = (
            item["target_provider"],
            item["target_model"],
            item["requested_role"],
        )
        require(
            logical_target not in logical_targets,
            "DUPLICATE_FANOUT_LOGICAL_TARGET",
        )
        logical_targets.add(logical_target)

        hashes.append(assignment_sha256(task, item))
        assignment_created_times.append(
            _parse_utc(
                item["created_at"],
                "ASSIGNMENT_CREATED_AT",
            )
        )

    require(
        len(set(hashes)) == len(hashes),
        "DUPLICATE_FANOUT_ASSIGNMENT_SHA256",
    )
    exact_hashes = sorted(hashes)

    require(
        isinstance(plan, dict)
        and set(plan) == FANOUT_PLAN_KEYS,
        "FANOUT_PLAN_SCHEMA_KEYS",
    )
    require(
        plan["schema"] == FANOUT_PLAN_SCHEMA,
        "FANOUT_PLAN_SCHEMA_VERSION",
    )
    _identifier(plan["plan_id"], "FANOUT_PLAN_ID")
    require(
        plan["task_sha256"] == sha256_json(task),
        "FANOUT_TASK_SHA256_MISMATCH",
    )
    require(
        plan["snapshot_id"] == task["snapshot_id"],
        "FANOUT_SNAPSHOT_ID_MISMATCH",
    )

    plan_hashes = plan["assignment_sha256s"]
    require(
        isinstance(plan_hashes, list)
        and bool(plan_hashes),
        "FANOUT_ASSIGNMENT_SHA256S",
    )
    for digest in plan_hashes:
        require(
            isinstance(digest, str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", digest)),
            "FANOUT_ASSIGNMENT_SHA256",
        )
    require(
        len(set(plan_hashes)) == len(plan_hashes),
        "DUPLICATE_FANOUT_PLAN_SHA256",
    )
    require(
        plan_hashes == sorted(plan_hashes),
        "FANOUT_PLAN_SHA256_ORDER",
    )
    require(
        plan_hashes == exact_hashes,
        "FANOUT_PLAN_ASSIGNMENT_SET_MISMATCH",
    )

    plan_created_at = _parse_utc(
        plan["created_at"],
        "FANOUT_PLAN_CREATED_AT",
    )
    require(
        all(
            plan_created_at >= created_at
            for created_at in assignment_created_times
        ),
        "FANOUT_PLAN_CREATED_BEFORE_ASSIGNMENT",
    )
    _nonauthority(plan["nonauthority"])
    return plan


def fanout_plan_sha256(
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    plan: dict[str, Any],
) -> str:
    validate_fanout_plan(task, assignments, plan)
    return sha256_json(plan)


def summarize_fanout_results(
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_fanout_plan(task, assignments, plan)
    require(
        isinstance(results, list),
        "FANOUT_RESULTS_LIST",
    )

    assignment_by_sha = {
        assignment_sha256(task, item): item
        for item in assignments
    }
    planned_hashes = list(plan["assignment_sha256s"])

    seen_assignment_hashes: set[str] = set()
    seen_submission_ids: set[str] = set()
    observed_hashes: list[str] = []
    completed_hashes: list[str] = []
    status_counts = {
        status: 0
        for status in sorted(RESULT_STATUSES)
    }

    for result in results:
        assignment_digest = result.get(
            "assignment_sha256"
        )
        require(
            assignment_digest in assignment_by_sha,
            "FANOUT_RESULT_NOT_PLANNED",
        )
        require(
            assignment_digest not in seen_assignment_hashes,
            "DUPLICATE_FANOUT_RESULT_FOR_ASSIGNMENT",
        )
        seen_assignment_hashes.add(assignment_digest)

        submission_id = result.get("submission_id")
        require(
            submission_id not in seen_submission_ids,
            "DUPLICATE_FANOUT_SUBMISSION_ID",
        )
        seen_submission_ids.add(submission_id)

        bound_assignment = assignment_by_sha[
            assignment_digest
        ]
        validate_result_v2_for_assignment(
            task,
            bound_assignment,
            result,
        )
        observed_hashes.append(assignment_digest)
        status_counts[result["status"]] += 1
        if result["status"] == "COMPLETED":
            completed_hashes.append(assignment_digest)

    observed_hashes = sorted(observed_hashes)
    completed_hashes = sorted(completed_hashes)
    missing_hashes = sorted(
        set(planned_hashes) - set(observed_hashes)
    )

    summary = {
        "schema": BATCH_SUMMARY_SCHEMA,
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "fanout_plan_sha256": fanout_plan_sha256(
            task,
            assignments,
            plan,
        ),
        "planned_assignment_count": len(planned_hashes),
        "observed_terminal_result_count":
            len(observed_hashes),
        "completed_assignment_count":
            len(completed_hashes),
        "noncompleted_assignment_count":
            len(observed_hashes) - len(completed_hashes),
        "planned_assignment_sha256s": planned_hashes,
        "observed_assignment_sha256s": observed_hashes,
        "completed_assignment_sha256s":
            completed_hashes,
        "missing_assignment_sha256s": missing_hashes,
        "status_counts": status_counts,
        "all_planned_observed": not missing_hashes,
        "all_planned_completed":
            not missing_hashes
            and len(completed_hashes) == len(planned_hashes),
        "adoption_authority": False,
    }
    summary["batch_sha256"] = sha256_json(summary)
    return summary
