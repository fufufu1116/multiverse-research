from __future__ import annotations

from collections import defaultdict
from typing import Any

from automation.multimodel_research_v1.model import (
    AGGREGATE_SCHEMA,
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
    by_identity: dict[
        tuple[str, str, str],
        tuple[str, dict[str, Any]],
    ] = {}
    duplicate_acknowledgements: list[dict[str, str]] = []

    for result in results:
        validate_result_for_task(task, result)
        validated.append(result)

        digest = result_content_digest(result)
        identity = _identity_key(result)

        if identity in by_identity:
            prior_digest, prior_result = by_identity[identity]
            if digest != prior_digest:
                raise ResearchContractError(
                    "MODEL_IDENTITY_CONTENT_CONFLICT:"
                    + ":".join(identity)
                )
            duplicate_acknowledgements.append(
                {
                    "submission_id": result["submission_id"],
                    "duplicate_of_submission_id":
                        prior_result["submission_id"],
                    "content_digest": digest,
                }
            )
        else:
            by_identity[identity] = (digest, result)

    unique_items = list(by_identity.values())
    unique_results = [
        item[1]
        for item in unique_items
    ]

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
        elif support > 0 and oppose == 0:
            descriptive_label = "SUPPORT_ONLY"
        elif oppose > 0 and support == 0:
            descriptive_label = "OPPOSE_ONLY"
        else:
            descriptive_label = "UNKNOWN_ONLY"

        claim = {
            "claim_key": claim_key,
            "descriptive_label": descriptive_label,
            "position_counts": counts,
            "positions": {
                position: items
                for position, items in sorted(positions.items())
            },
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

    noncompleted_results = [
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
    ]

    infra_failures = [
        item
        for item in noncompleted_results
        if item["status"] == "INFRA_FAILURE"
    ]

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
        "consensus_is_descriptive_only": True,
        "adoption_authority": False,
    }

    aggregate["aggregate_sha256"] = sha256_json(aggregate)
    return aggregate
