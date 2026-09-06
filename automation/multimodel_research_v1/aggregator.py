from __future__ import annotations

from collections import defaultdict
from typing import Any

from automation.multimodel_research_v1.model import (
    AGGREGATE_SCHEMA,
    result_content_digest,
    sha256_json,
    validate_result,
)


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    validated: list[dict[str, Any]] = []
    by_digest: dict[str, dict[str, Any]] = {}
    duplicate_acknowledgements: list[dict[str, str]] = []

    for result in results:
        validate_result(result)
        validated.append(result)

        digest = result_content_digest(result)

        if digest in by_digest:
            duplicate_acknowledgements.append(
                {
                    "submission_id": result["submission_id"],
                    "duplicate_of_submission_id":
                        by_digest[digest]["submission_id"],
                    "content_digest": digest,
                }
            )
        else:
            by_digest[digest] = result

    unique_results = list(by_digest.values())

    claim_positions: dict[
        str,
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: defaultdict(list))

    for result in unique_results:
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

    infra_failures = [
        {
            "submission_id": result["submission_id"],
            "model_identity": result["model_identity"],
            "uncertainty_factors": result["uncertainty_factors"],
        }
        for result in unique_results
        if result["status"] == "INFRA_FAILURE"
    ]

    aggregate = {
        "schema": AGGREGATE_SCHEMA,
        "unique_submission_count": len(unique_results),
        "input_submission_count": len(validated),
        "duplicate_acknowledgements": duplicate_acknowledgements,
        "claims": claims,
        "unresolved_divergences": unresolved_divergences,
        "infra_failures": infra_failures,
        "consensus_is_descriptive_only": True,
        "adoption_authority": False,
    }

    aggregate["aggregate_sha256"] = sha256_json(aggregate)
    return aggregate
