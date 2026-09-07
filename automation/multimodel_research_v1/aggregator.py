from __future__ import annotations

from collections import defaultdict
from typing import Any

from automation.multimodel_research_v1.model import (
    AGGREGATE_SCHEMA,
    RESULT_STATUSES,
    ResearchContractError,
    require,
    result_content_digest,
    sha256_json,
    validate_result_for_task,
    validate_task,
)


def _identity_key(result: dict[str, Any]) -> tuple[str, str, str]:
    identity = result["model_identity"]
    return (
        identity["provider"],
        identity["model"],
        identity["role"],
    )


def aggregate_results(
    task: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_task(task)
    require(isinstance(results, list), "RESULTS_LIST")
    require(bool(results), "RESULTS_REQUIRED")

    validated: list[dict[str, Any]] = []
    grouped: dict[
        tuple[str, str, str],
        list[tuple[str, dict[str, Any]]],
    ] = defaultdict(list)

    for result in results:
        validate_result_for_task(task, result)
        validated.append(result)
        grouped[_identity_key(result)].append(
            (result_content_digest(result), result)
        )

    duplicate_acknowledgements: list[dict[str, str]] = []
    unique_items: list[tuple[str, dict[str, Any]]] = []

    for identity in sorted(grouped):
        entries = grouped[identity]
        digests = {digest for digest, _ in entries}
        if len(digests) != 1:
            raise ResearchContractError(
                "MODEL_IDENTITY_CONTENT_CONFLICT:"
                + ":".join(identity)
            )
        digest = next(iter(digests))
        ordered = sorted(
            entries,
            key=lambda item: item[1]["submission_id"],
        )
        canonical = ordered[0][1]
        unique_items.append((digest, canonical))
        for _, duplicate in ordered[1:]:
            duplicate_acknowledgements.append(
                {
                    "submission_id": duplicate["submission_id"],
                    "duplicate_of_submission_id":
                        canonical["submission_id"],
                    "content_digest": digest,
                }
            )

    duplicate_acknowledgements.sort(
        key=lambda item: (
            item["duplicate_of_submission_id"],
            item["submission_id"],
            item["content_digest"],
        )
    )
    unique_results = [item[1] for item in unique_items]

    claim_positions: dict[
        str,
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: defaultdict(list))

    for result_digest, result in unique_items:
        if result["status"] != "COMPLETED":
            continue

        for finding in result["findings"]:
            claim_positions[
                finding["claim_key"]
            ][
                finding["position"]
            ].append(
                {
                    "submission_id": result["submission_id"],
                    "model_identity": result["model_identity"],
                    "produced_at": result["produced_at"],
                    "result_content_digest": result_digest,
                    "finding_id": finding["finding_id"],
                    "severity": finding["severity"],
                    "assertion": finding["assertion"],
                    "evidence": finding["evidence"],
                    "confidence": finding["confidence"],
                    "uncertainty": finding["uncertainty"],
                    "recommendation": finding["recommendation"],
                    "validation_plan": finding["validation_plan"],
                }
            )

    claims: list[dict[str, Any]] = []
    unresolved_divergences: list[dict[str, Any]] = []

    for claim_key in sorted(claim_positions):
        positions = claim_positions[claim_key]
        counts = {
            position: len(items)
            for position, items in sorted(positions.items())
        }

        support = counts.get("SUPPORT", 0)
        oppose = counts.get("OPPOSE", 0)
        unknown = counts.get("UNKNOWN", 0)

        if support > 0 and oppose > 0:
            descriptive_label = "DIVERGENT"
        elif support > 0:
            descriptive_label = (
                "SUPPORT_WITH_UNKNOWN"
                if unknown > 0
                else "SUPPORT_ONLY"
            )
        elif oppose > 0:
            descriptive_label = (
                "OPPOSE_WITH_UNKNOWN"
                if unknown > 0
                else "OPPOSE_ONLY"
            )
        else:
            descriptive_label = "UNKNOWN_ONLY"

        ordered_positions = {}
        for position, items in sorted(positions.items()):
            ordered_positions[position] = sorted(
                items,
                key=lambda item: (
                    item["model_identity"]["provider"],
                    item["model_identity"]["model"],
                    item["model_identity"]["role"],
                    item["finding_id"],
                    item["submission_id"],
                ),
            )

        claim = {
            "claim_key": claim_key,
            "descriptive_label": descriptive_label,
            "position_counts": counts,
            "positions": ordered_positions,
            "vote_confers_authority": False,
            "majority_confers_truth": False,
        }
        claims.append(claim)

        if descriptive_label == "DIVERGENT":
            unresolved_divergences.append(
                {
                    "claim_key": claim_key,
                    "support_count": support,
                    "oppose_count": oppose,
                    "unknown_count": unknown,
                    "status": "UNRESOLVED_DIVERGENCE",
                    "required_next_action":
                        "MECHANICAL_FALSIFICATION_TASK",
                }
            )

    noncompleted_results = sorted(
        [
            {
                "submission_id": result["submission_id"],
                "model_identity": result["model_identity"],
                "produced_at": result["produced_at"],
                "result_content_digest": result_digest,
                "status": result["status"],
                "uncertainty_factors": result["uncertainty_factors"],
            }
            for result_digest, result in unique_items
            if result["status"] != "COMPLETED"
        ],
        key=lambda item: (
            item["model_identity"]["provider"],
            item["model_identity"]["model"],
            item["model_identity"]["role"],
            item["submission_id"],
        ),
    )

    infra_failures = [
        item
        for item in noncompleted_results
        if item["status"] == "INFRA_FAILURE"
    ]

    status_counts = {
        status: sum(
            1
            for result in unique_results
            if result["status"] == status
        )
        for status in sorted(RESULT_STATUSES)
    }

    requested_role_coverage = {}
    missing_requested_roles = []
    roles_without_completed_result = []
    for role in task["requested_roles"]:
        role_results = [
            result
            for result in unique_results
            if result["model_identity"]["role"] == role
        ]
        completed_count = sum(
            1
            for result in role_results
            if result["status"] == "COMPLETED"
        )
        requested_role_coverage[role] = {
            "unique_identity_count": len(role_results),
            "completed_count": completed_count,
            "noncompleted_count": len(role_results) - completed_count,
            "status_counts": {
                status: sum(
                    1
                    for result in role_results
                    if result["status"] == status
                )
                for status in sorted(RESULT_STATUSES)
            },
        }
        if not role_results:
            missing_requested_roles.append(role)
        if completed_count == 0:
            roles_without_completed_result.append(role)

    aggregate = {
        "schema": AGGREGATE_SCHEMA,
        "task_id": task["task_id"],
        "snapshot_id": task["snapshot_id"],
        "task_sha256": sha256_json(task),
        "unique_model_identity_count": len(unique_results),
        "unique_submission_count": len(unique_results),
        "input_submission_count": len(validated),
        "duplicate_acknowledgements": duplicate_acknowledgements,
        "claims": claims,
        "unresolved_divergences": unresolved_divergences,
        "noncompleted_results": noncompleted_results,
        "infra_failures": infra_failures,
        "status_counts": status_counts,
        "requested_role_coverage": requested_role_coverage,
        "missing_requested_roles": missing_requested_roles,
        "roles_without_completed_result": roles_without_completed_result,
        "requested_role_coverage_complete": not missing_requested_roles,
        "requested_role_completed_coverage_complete":
            not roles_without_completed_result,
        "consensus_is_descriptive_only": True,
        "adoption_authority": False,
    }

    aggregate["aggregate_sha256"] = sha256_json(aggregate)
    return aggregate
