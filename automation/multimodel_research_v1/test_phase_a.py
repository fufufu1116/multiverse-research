from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.aggregator import aggregate_results
from automation.multimodel_research_v1.model import (
    ResearchContractError,
    result_content_digest,
    sha256_json,
    validate_result,
    validate_result_for_task,
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
        "created_at": "2026-09-07T00:00:00Z",
        "domain": "core",
        "objective": "Challenge the dispatcher boundary.",
        "source_refs": [
            {
                "kind": "SNAPSHOT_PACKET",
                "ref": "packet-v1",
                "sha256": "a" * 64,
                "observed_at": "2026-09-07T00:00:00Z",
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
        "task_sha256": sha256_json(task()),
        "submission_id": submission_id,
        "snapshot_id": "snapshot-001",
        "produced_at": "2026-09-07T00:01:00Z",
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


def bind_result_to_task(
    value: dict,
    bound_task: dict,
) -> dict:
    value["task_id"] = bound_task["task_id"]
    value["snapshot_id"] = bound_task["snapshot_id"]
    value["task_sha256"] = sha256_json(bound_task)
    return value


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
        aggregate = aggregate_results(task(), [first, second])

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

        aggregate = aggregate_results(task(), [support, oppose])

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

        aggregate = aggregate_results(task(), values)
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

        aggregate = aggregate_results(task(), [completed, infra])
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
        with self.assertRaises(ResearchContractError):
            adapter.run(broken_task)

    def test_15_result_role_must_be_requested(self):
        value = result(
            submission_id="submission-role",
            role="unrequested-role",
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(task(), value)

    def test_16_evidence_primitive_must_be_task_allowed(self):
        bound_task = task()
        bound_task["allowed_primitives"] = ["SOURCE_REF"]
        value = bind_result_to_task(
            result(submission_id="submission-primitive"),
            bound_task,
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_17_source_ref_evidence_binds_declared_digest(self):
        bound_task = task()
        bound_task["allowed_primitives"] = ["SOURCE_REF"]
        value = bind_result_to_task(
            result(submission_id="submission-source"),
            bound_task,
        )
        evidence = value["findings"][0]["evidence"]
        evidence["primitive"] = "SOURCE_REF"
        evidence["ref"] = "packet-v1"
        evidence["sha256"] = "a" * 64
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

        broken = copy.deepcopy(value)
        broken["findings"][0]["evidence"]["sha256"] = "b" * 64
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, broken)

    def test_18_task_max_findings_is_enforced(self):
        bound_task = task()
        bound_task["constraints"]["max_findings"] = 1
        value = bind_result_to_task(
            result(submission_id="submission-findings"),
            bound_task,
        )
        second = copy.deepcopy(value["findings"][0])
        second["finding_id"] = "finding-002"
        second["claim_key"] = "claim-second"
        value["findings"].append(second)
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_19_task_max_output_bytes_is_enforced(self):
        bound_task = task()
        bound_task["constraints"]["max_output_bytes"] = 1024
        value = bind_result_to_task(
            result(submission_id="submission-output"),
            bound_task,
        )
        value["findings"][0]["assertion"] = "x" * 4000
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_20_aggregate_rejects_mixed_snapshot(self):
        first = result(submission_id="submission-snapshot-a")
        second = result(
            submission_id="submission-snapshot-b",
            provider="provider-b",
            model="model-b",
        )
        second["snapshot_id"] = "snapshot-other"
        with self.assertRaises(ResearchContractError):
            aggregate_results(task(), [first, second])

    def test_21_same_identity_conflicting_resubmission_fails_closed(self):
        first = result(submission_id="submission-first")
        second = result(
            submission_id="submission-second",
            assertion="Changed content from same identity.",
        )
        with self.assertRaises(ResearchContractError):
            aggregate_results(task(), [first, second])

    def test_22_noncompleted_statuses_are_preserved(self):
        values = [
            result(
                submission_id="infra",
                provider="provider-infra",
                model="model-infra",
                status="INFRA_FAILURE",
            ),
            result(
                submission_id="unsupported",
                provider="provider-unsupported",
                model="model-unsupported",
                status="UNSUPPORTED",
            ),
            result(
                submission_id="refused",
                provider="provider-refused",
                model="model-refused",
                status="REFUSED",
            ),
        ]
        aggregate = aggregate_results(task(), values)
        self.assertEqual(len(aggregate["noncompleted_results"]), 3)
        self.assertEqual(
            {
                item["status"]
                for item in aggregate["noncompleted_results"]
            },
            {"INFRA_FAILURE", "UNSUPPORTED", "REFUSED"},
        )
        self.assertEqual(len(aggregate["infra_failures"]), 1)

    def test_23_duplicate_source_ref_is_rejected(self):
        value = task()
        value["source_refs"].append(
            copy.deepcopy(value["source_refs"][0])
        )
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_24_duplicate_requested_role_is_rejected(self):
        value = task()
        value["requested_roles"].append(
            value["requested_roles"][0]
        )
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_25_empty_aggregate_is_rejected(self):
        with self.assertRaises(ResearchContractError):
            aggregate_results(task(), [])

    def test_26_task_digest_rejects_reused_ids_with_changed_task(self):
        changed_task = task()
        changed_task["objective"] = "Changed objective under reused IDs."
        stale_result = result(submission_id="stale-task-result")
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(changed_task, stale_result)

    def test_27_duplicate_claim_key_in_one_result_is_rejected(self):
        value = result(submission_id="duplicate-claim")
        second = copy.deepcopy(value["findings"][0])
        second["finding_id"] = "finding-002"
        second["position"] = "OPPOSE"
        value["findings"].append(second)
        with self.assertRaises(ResearchContractError):
            validate_result(value)

    def test_28_task_source_and_result_timestamps_are_strict_utc(self):
        bad_task = task()
        bad_task["created_at"] = "2026-09-07 00:00:00"
        with self.assertRaises(ResearchContractError):
            validate_task(bad_task)

        bad_source = task()
        bad_source["source_refs"][0]["observed_at"] = "yesterday"
        with self.assertRaises(ResearchContractError):
            validate_task(bad_source)

        bad_result = result(submission_id="bad-time")
        bad_result["produced_at"] = "2026-09-07T00:01:00+09:00"
        with self.assertRaises(ResearchContractError):
            validate_result(bad_result)

    def test_29_claim_provenance_carries_time_and_result_digest(self):
        value = result(submission_id="claim-provenance")
        aggregate = aggregate_results(task(), [value])
        item = aggregate["claims"][0]["positions"]["SUPPORT"][0]
        self.assertEqual(item["produced_at"], value["produced_at"])
        self.assertEqual(
            item["result_content_digest"],
            result_content_digest(value),
        )

    def test_30_aggregate_binds_exact_task_digest(self):
        bound_task = task()
        aggregate = aggregate_results(
            bound_task,
            [result(submission_id="aggregate-task-digest")],
        )
        self.assertEqual(
            aggregate["task_sha256"],
            sha256_json(bound_task),
        )

    def test_31_source_observation_cannot_postdate_task_creation(self):
        value = task()
        value["source_refs"][0]["observed_at"] = "2026-09-07T00:00:01Z"
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_32_result_cannot_predate_task_creation(self):
        bound_task = task()
        value = bind_result_to_task(
            result(submission_id="predates-task"),
            bound_task,
        )
        value["produced_at"] = "2026-09-06T23:59:59Z"
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_33_noncompleted_result_requires_reason(self):
        value = result(
            submission_id="reasonless-infra",
            status="INFRA_FAILURE",
        )
        value["uncertainty_factors"] = []
        with self.assertRaises(ResearchContractError):
            validate_result(value)

    def test_34_unknown_presence_is_visible_in_descriptive_label(self):
        support = result(
            submission_id="support-with-unknown",
            provider="support-provider",
            model="support-model",
            position="SUPPORT",
        )
        unknown = result(
            submission_id="unknown-position",
            provider="unknown-provider",
            model="unknown-model",
            position="UNKNOWN",
        )
        aggregate = aggregate_results(task(), [support, unknown])
        self.assertEqual(
            aggregate["claims"][0]["descriptive_label"],
            "SUPPORT_WITH_UNKNOWN",
        )

    def test_35_status_counts_preserve_advisory_coverage(self):
        values = [
            result(
                submission_id="completed-status",
                provider="provider-completed",
                model="model-completed",
            ),
            result(
                submission_id="infra-status",
                provider="provider-infra-count",
                model="model-infra-count",
                status="INFRA_FAILURE",
            ),
            result(
                submission_id="unsupported-status",
                provider="provider-unsupported-count",
                model="model-unsupported-count",
                status="UNSUPPORTED",
            ),
            result(
                submission_id="refused-status",
                provider="provider-refused-count",
                model="model-refused-count",
                status="REFUSED",
            ),
        ]
        aggregate = aggregate_results(task(), values)
        self.assertEqual(
            aggregate["status_counts"],
            {
                "COMPLETED": 1,
                "INFRA_FAILURE": 1,
                "REFUSED": 1,
                "UNSUPPORTED": 1,
            },
        )

    def test_36_aggregate_is_invariant_to_input_order(self):
        values = [
            result(
                submission_id="z-retry",
                provider="provider-a",
                model="model-a",
            ),
            result(
                submission_id="a-original",
                provider="provider-a",
                model="model-a",
            ),
            result(
                submission_id="middle",
                provider="provider-b",
                model="model-b",
                position="OPPOSE",
                assertion="Contrarian.",
            ),
        ]
        forward = aggregate_results(task(), values)
        reverse = aggregate_results(task(), list(reversed(values)))
        self.assertEqual(forward, reverse)
        self.assertEqual(
            forward["duplicate_acknowledgements"][0][
                "duplicate_of_submission_id"
            ],
            "a-original",
        )

    def test_37_missing_requested_role_is_explicit(self):
        aggregate = aggregate_results(
            task(),
            [result(submission_id="architecture-only")],
        )
        self.assertEqual(
            aggregate["missing_requested_roles"],
            ["security_challenge"],
        )
        self.assertFalse(
            aggregate["requested_role_coverage_complete"]
        )
        self.assertEqual(
            aggregate["roles_without_completed_result"],
            ["security_challenge"],
        )

    def test_38_noncompleted_role_is_observed_but_not_completed(self):
        values = [
            result(submission_id="architecture-complete"),
            result(
                submission_id="security-infra",
                provider="security-provider",
                model="security-model",
                role="security_challenge",
                status="INFRA_FAILURE",
            ),
        ]
        aggregate = aggregate_results(task(), values)
        self.assertEqual(aggregate["missing_requested_roles"], [])
        self.assertTrue(
            aggregate["requested_role_coverage_complete"]
        )
        self.assertEqual(
            aggregate["roles_without_completed_result"],
            ["security_challenge"],
        )
        self.assertFalse(
            aggregate[
                "requested_role_completed_coverage_complete"
            ]
        )


if __name__ == "__main__":
    unittest.main()
