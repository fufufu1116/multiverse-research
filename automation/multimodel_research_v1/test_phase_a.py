from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.aggregator import aggregate_results
from automation.multimodel_research_v1.model import (
    ResearchContractError,
    result_content_digest,
    validate_result,
    validate_task,
)
from automation.multimodel_research_v1.outcome import classify_review_outcome
from automation.multimodel_research_v1.synthetic_adapter import (
    SyntheticAdvisoryAdapter,
)


def nonauthority() -> dict:
    return {
        "adoption": False,
        "merge": False,
        "main_mutation": False,
        "ruleset_mutation": False,
        "workflow_dispatch_rerun": False,
        "runtime_activation": False,
        "provider_effect": False,
        "production": False,
        "protected_data": False,
        "live_business_effect": False,
        "spend": False,
    }


def task() -> dict:
    return {
        "schema": "MULTIVERSE_RESEARCH_TASK_v1",
        "task_id": "task-001",
        "snapshot_id": "snapshot-001",
        "domain": "core",
        "objective": "Challenge the dispatcher boundary.",
        "source_refs": [
            {
                "kind": "SNAPSHOT_PACKET",
                "ref": "packet-v1",
                "sha256": "a" * 64,
            }
        ],
        "allowed_primitives": [
            "SOURCE_REF",
            "NORMALIZED_JSON_SHA256",
        ],
        "constraints": {
            "network_access": "NONE",
            "max_compute_seconds": 300,
            "max_output_bytes": 100000,
            "max_findings": 20,
        },
        "requested_roles": [
            "architecture_challenge",
            "security_challenge",
        ],
        "nonauthority": nonauthority(),
    }


def finding(
    *,
    finding_id: str,
    claim_key: str,
    position: str,
    assertion: str,
) -> dict:
    return {
        "finding_id": finding_id,
        "claim_key": claim_key,
        "position": position,
        "severity": "HIGH",
        "assertion": assertion,
        "evidence": {
            "primitive": "NORMALIZED_JSON_SHA256",
            "ref": "synthetic-evidence",
            "sha256": "b" * 64,
        },
        "confidence": 0.8,
        "uncertainty": "Synthetic fixture only.",
        "recommendation": "Add a fail-closed test.",
        "validation_plan": "Run the synthetic fixture.",
    }


def result(
    *,
    submission_id: str,
    provider: str = "synthetic",
    model: str = "model-a",
    role: str = "architecture_challenge",
    position: str = "SUPPORT",
    assertion: str = "Boundary should be hardened.",
    status: str = "COMPLETED",
) -> dict:
    findings = []
    if status == "COMPLETED":
        findings = [
            finding(
                finding_id="finding-001",
                claim_key="claim-dispatcher-boundary",
                position=position,
                assertion=assertion,
            )
        ]

    return {
        "schema": "MULTIVERSE_RESEARCH_RESULT_v1",
        "task_id": "task-001",
        "submission_id": submission_id,
        "snapshot_id": "snapshot-001",
        "model_identity": {
            "provider": provider,
            "model": model,
            "role": role,
        },
        "status": status,
        "findings": findings,
        "uncertainty_factors": (
            []
            if status == "COMPLETED"
            else ["synthetic infrastructure unavailable"]
        ),
        "nonauthority": nonauthority(),
    }


class ContractTests(unittest.TestCase):
    def test_01_valid_task(self):
        value = task()
        self.assertEqual(validate_task(value), value)

    def test_02_task_rejects_dynamic_command_key(self):
        value = task()
        value["constraints"]["shell_command"] = "echo unsafe"
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_03_task_network_is_bounded(self):
        value = task()
        value["constraints"]["network_access"] = "FULL"
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_04_valid_completed_result(self):
        value = result(submission_id="submission-001")
        self.assertEqual(validate_result(value), value)

    def test_05_noncompleted_result_has_no_findings(self):
        value = result(
            submission_id="submission-002",
            status="INFRA_FAILURE",
        )
        self.assertEqual(validate_result(value), value)

        broken = copy.deepcopy(value)
        broken["findings"] = [
            finding(
                finding_id="finding-bad",
                claim_key="claim-bad",
                position="SUPPORT",
                assertion="Should not exist on infra failure.",
            )
        ]
        with self.assertRaises(ResearchContractError):
            validate_result(broken)

    def test_06_result_digest_ignores_submission_id_only(self):
        first = result(submission_id="submission-001")
        second = result(submission_id="submission-002")
        self.assertEqual(
            result_content_digest(first),
            result_content_digest(second),
        )

    def test_07_exact_duplicate_is_acknowledged(self):
        first = result(submission_id="submission-001")
        second = result(submission_id="submission-002")
        aggregate = aggregate_results([first, second])

        self.assertEqual(aggregate["input_submission_count"], 2)
        self.assertEqual(aggregate["unique_submission_count"], 1)
        self.assertEqual(len(aggregate["duplicate_acknowledgements"]), 1)
        self.assertFalse(aggregate["adoption_authority"])

    def test_08_contrarian_is_preserved_as_divergence(self):
        support = result(
            submission_id="submission-support",
            provider="provider-a",
            model="model-a",
            position="SUPPORT",
            assertion="Boundary is sufficient.",
        )
        oppose = result(
            submission_id="submission-oppose",
            provider="provider-b",
            model="model-b",
            position="OPPOSE",
            assertion="Boundary has a bypass.",
        )

        aggregate = aggregate_results([support, oppose])

        self.assertEqual(
            aggregate["claims"][0]["descriptive_label"],
            "DIVERGENT",
        )
        self.assertEqual(
            aggregate["unresolved_divergences"][0]["status"],
            "UNRESOLVED_DIVERGENCE",
        )
        self.assertEqual(
            aggregate["unresolved_divergences"][0][
                "required_next_action"
            ],
            "MECHANICAL_FALSIFICATION_TASK",
        )

    def test_09_majority_never_confers_truth_or_authority(self):
        values = [
            result(
                submission_id=f"support-{index}",
                provider=f"provider-{index}",
                model=f"model-{index}",
                position="SUPPORT",
            )
            for index in range(3)
        ]
        values.append(
            result(
                submission_id="oppose-1",
                provider="contrarian-provider",
                model="contrarian-model",
                position="OPPOSE",
                assertion="Contrarian finding.",
            )
        )

        aggregate = aggregate_results(values)
        claim = aggregate["claims"][0]

        self.assertFalse(claim["vote_confers_authority"])
        self.assertFalse(claim["majority_confers_truth"])
        self.assertFalse(aggregate["adoption_authority"])
        self.assertEqual(
            aggregate["unresolved_divergences"][0]["oppose_count"],
            1,
        )

    def test_10_infra_failure_is_preserved_separately(self):
        completed = result(
            submission_id="submission-completed",
        )
        infra = result(
            submission_id="submission-infra",
            provider="provider-infra",
            model="model-infra",
            status="INFRA_FAILURE",
        )

        aggregate = aggregate_results([completed, infra])
        self.assertEqual(len(aggregate["infra_failures"]), 1)
        self.assertEqual(
            aggregate["infra_failures"][0]["submission_id"],
            "submission-infra",
        )

    def test_11_review_outcome_pass_requires_complete_review(self):
        value = classify_review_outcome(
            candidate_findings=[],
            infrastructure_errors=[],
            required_review_complete=True,
        )
        self.assertEqual(value["outcome"], "PASS")
        self.assertTrue(value["authoritative_pass"])

    def test_12_review_outcome_infra_failure_is_not_candidate_fix(self):
        value = classify_review_outcome(
            candidate_findings=[],
            infrastructure_errors=["runner unavailable"],
            required_review_complete=False,
        )
        self.assertEqual(value["outcome"], "INFRA_FAILURE")
        self.assertFalse(value["authoritative_pass"])

    def test_13_candidate_finding_outranks_infra_failure(self):
        value = classify_review_outcome(
            candidate_findings=["exact test failed"],
            infrastructure_errors=["runner later failed"],
            required_review_complete=False,
        )
        self.assertEqual(value["outcome"], "FIX_REQUIRED")
        self.assertFalse(value["authoritative_pass"])

    def test_14_synthetic_adapter_is_offline_and_exact_bound(self):
        value = result(submission_id="submission-adapter")
        adapter = SyntheticAdvisoryAdapter(value)
        self.assertEqual(
            adapter.run(task())["submission_id"],
            "submission-adapter",
        )

        broken_task = task()
        broken_task["task_id"] = "task-other"
        with self.assertRaises(ValueError):
            adapter.run(broken_task)


if __name__ == "__main__":
    unittest.main()
