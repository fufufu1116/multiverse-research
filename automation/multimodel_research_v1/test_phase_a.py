from __future__ import annotations

import copy
import unittest

from automation.multimodel_research_v1.aggregator import (
    aggregate_results,
    aggregate_results_v2,
)
from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    result_v2_content_digest,
    validate_assignment,
    validate_result_v2_for_assignment,
)
from automation.multimodel_research_v1.fanout import (
    fanout_plan_sha256,
    summarize_fanout_results,
    validate_fanout_plan,
)
from automation.multimodel_research_v1.model_target import (
    model_target_policy_sha256,
    validate_model_target_policy,
    validate_resolved_model_id,
)
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


def task_v2() -> dict:
    value = copy.deepcopy(task())
    value["schema"] = "MULTIVERSE_RESEARCH_TASK_v2"
    value["evidence_manifest"] = [
        {
            "primitive": "NORMALIZED_JSON_SHA256",
            "ref": "synthetic-evidence",
            "sha256": "b" * 64,
            "observed_at": "2026-09-07T00:00:00Z",
        }
    ]
    return value


def assignment(
    bound_task: dict | None = None,
    *,
    assignment_id: str = "assignment-001",
    provider: str = "synthetic",
    model: str = "model-a",
    role: str = "architecture_challenge",
    execution_mode: str = "SYNTHETIC_OFFLINE",
) -> dict:
    if bound_task is None:
        bound_task = task_v2()
    live = execution_mode == "LIVE_ADVISORY"
    return {
        "schema": "MULTIVERSE_RESEARCH_ASSIGNMENT_v1",
        "assignment_id": assignment_id,
        "task_sha256": sha256_json(bound_task),
        "snapshot_id": bound_task["snapshot_id"],
        "created_at": "2026-09-07T00:00:30Z",
        "target_provider": provider,
        "target_model": model,
        "requested_role": role,
        "adapter_sha256": "9" * 64,
        "execution_mode": execution_mode,
        "research_network_access": "NONE",
        "provider_transport_policy_ref": (
            "provider-transport-001"
            if live
            else "NONE"
        ),
        "max_compute_seconds": 120,
        "max_output_bytes": 50000,
        "attestation_required": live,
        "nonauthority": nonauthority(),
    }


def result_v2(
    bound_task: dict,
    bound_assignment: dict,
    *,
    submission_id: str = "result-v2-001",
    status: str = "COMPLETED",
    position: str = "SUPPORT",
) -> dict:
    value = bind_result_to_task(
        result(
            submission_id=submission_id,
            provider=bound_assignment["target_provider"],
            model=bound_assignment["target_model"],
            role=bound_assignment["requested_role"],
            status=status,
            position=position,
        ),
        bound_task,
    )
    value["schema"] = "MULTIVERSE_RESEARCH_RESULT_v2"
    value["assignment_sha256"] = assignment_sha256(
        bound_task,
        bound_assignment,
    )
    return value


def fanout_plan(
    bound_task: dict,
    assignments: list[dict],
    *,
    plan_id: str = "fanout-plan-001",
) -> dict:
    hashes = sorted(
        assignment_sha256(bound_task, item)
        for item in assignments
    )
    return {
        "schema": "MULTIVERSE_RESEARCH_FANOUT_PLAN_v1",
        "plan_id": plan_id,
        "task_sha256": sha256_json(bound_task),
        "snapshot_id": bound_task["snapshot_id"],
        "created_at": "2026-09-07T00:00:45Z",
        "assignment_sha256s": hashes,
        "nonauthority": nonauthority(),
    }


def model_target_policy(
    bound_task: dict,
    bound_assignment: dict,
    *,
    classification: str = "PINNED_OR_STABLE",
) -> dict:
    return {
        "schema": "MULTIVERSE_MODEL_TARGET_POLICY_v1",
        "policy_id": "model-target-policy-001",
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "provider": bound_assignment["target_provider"],
        "requested_model_id": bound_assignment["target_model"],
        "model_id_classification": classification,
        "classification_evidence_ref":
            "provider-model-catalog-snapshot-001",
        "classification_evidence_sha256": "8" * 64,
        "alias_allowed": False,
        "preview_allowed": False,
        "experimental_allowed": False,
        "resolved_model_id_required": True,
        "stable_provider_api_required": True,
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


    def test_39_duplicate_submission_id_is_rejected(self):
        first = result(
            submission_id="shared-submission",
            provider="provider-a",
            model="model-a",
        )
        second = result(
            submission_id="shared-submission",
            provider="provider-b",
            model="model-b",
        )
        with self.assertRaises(ResearchContractError):
            aggregate_results(task(), [first, second])

    def test_40_source_ref_evidence_requires_task_digest(self):
        bound_task = task()
        bound_task["allowed_primitives"] = ["SOURCE_REF"]
        bound_task["source_refs"][0]["sha256"] = None
        value = bind_result_to_task(
            result(submission_id="undigested-source"),
            bound_task,
        )
        evidence = value["findings"][0]["evidence"]
        evidence["primitive"] = "SOURCE_REF"
        evidence["ref"] = "packet-v1"
        evidence["sha256"] = None
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_41_public_evidence_must_be_declared_and_digested(self):
        bound_task = task()
        bound_task["allowed_primitives"] = ["PUBLIC_EVIDENCE_REF"]
        value = bind_result_to_task(
            result(submission_id="public-evidence"),
            bound_task,
        )
        evidence = value["findings"][0]["evidence"]
        evidence["primitive"] = "PUBLIC_EVIDENCE_REF"
        evidence["ref"] = "packet-v1"
        evidence["sha256"] = "a" * 64
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

        undeclared = copy.deepcopy(value)
        undeclared["findings"][0]["evidence"]["ref"] = "other-ref"
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, undeclared)



    def test_42_valid_task_v2_exact_manifest(self):
        value = task_v2()
        self.assertEqual(validate_task(value), value)

    def test_43_task_v2_manifest_unknown_primitive_rejected(self):
        value = task_v2()
        value["evidence_manifest"][0]["primitive"] = "NOT_ALLOWED"
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_44_task_v2_duplicate_primitive_ref_rejected(self):
        value = task_v2()
        duplicate = copy.deepcopy(value["evidence_manifest"][0])
        duplicate["sha256"] = "c" * 64
        value["evidence_manifest"].append(duplicate)
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_45_task_v2_manifest_null_digest_rejected(self):
        value = task_v2()
        value["evidence_manifest"][0]["sha256"] = None
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_46_task_v2_manifest_cannot_postdate_task(self):
        value = task_v2()
        value["evidence_manifest"][0][
            "observed_at"
        ] = "2026-09-07T00:00:01Z"
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_47_task_v2_exact_normalized_json_evidence_passes(self):
        bound_task = task_v2()
        value = bind_result_to_task(
            result(submission_id="v2-exact-json"),
            bound_task,
        )
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

    def test_48_task_v2_undeclared_evidence_ref_rejected(self):
        bound_task = task_v2()
        value = bind_result_to_task(
            result(submission_id="v2-undeclared-ref"),
            bound_task,
        )
        value["findings"][0]["evidence"]["ref"] = "other-evidence"
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_49_task_v2_evidence_digest_mismatch_rejected(self):
        bound_task = task_v2()
        value = bind_result_to_task(
            result(submission_id="v2-digest-mismatch"),
            bound_task,
        )
        value["findings"][0]["evidence"]["sha256"] = "c" * 64
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_50_task_v2_same_ref_wrong_primitive_rejected(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"].append("UNITTEST_RESULT")
        value = bind_result_to_task(
            result(submission_id="v2-wrong-primitive"),
            bound_task,
        )
        value["findings"][0]["evidence"]["primitive"] = "UNITTEST_RESULT"
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_51_task_v2_exact_synthetic_fixture_passes(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"] = ["SYNTHETIC_FIXTURE"]
        bound_task["evidence_manifest"][0][
            "primitive"
        ] = "SYNTHETIC_FIXTURE"
        value = bind_result_to_task(
            result(submission_id="v2-synthetic"),
            bound_task,
        )
        value["findings"][0]["evidence"][
            "primitive"
        ] = "SYNTHETIC_FIXTURE"
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

    def test_52_task_v2_undeclared_unittest_result_rejected(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"].append("UNITTEST_RESULT")
        value = bind_result_to_task(
            result(submission_id="v2-unittest"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "UNITTEST_RESULT",
                "ref": "unittest-run-001",
                "sha256": "d" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_53_task_v2_undeclared_validator_result_rejected(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"].append("VALIDATOR_RESULT")
        value = bind_result_to_task(
            result(submission_id="v2-validator"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "VALIDATOR_RESULT",
                "ref": "validator-run-001",
                "sha256": "e" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_54_task_v2_undeclared_subtree_hash_rejected(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"].append("SUBTREE_HASH")
        value = bind_result_to_task(
            result(submission_id="v2-subtree"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "SUBTREE_HASH",
                "ref": "subtree-001",
                "sha256": "f" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_55_task_v2_undeclared_exact_lineage_rejected(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"].append("EXACT_LINEAGE")
        value = bind_result_to_task(
            result(submission_id="v2-lineage"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "EXACT_LINEAGE",
                "ref": "lineage-001",
                "sha256": "1" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_56_task_v1_historical_evidence_semantics_unchanged(self):
        bound_task = task()
        value = bind_result_to_task(
            result(submission_id="v1-historical"),
            bound_task,
        )
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

    def test_57_v1_result_cannot_replay_against_task_v2(self):
        stale = result(submission_id="v1-stale-against-v2")
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(task_v2(), stale)

    def test_58_task_v2_manifest_mutation_changes_task_digest(self):
        first = task_v2()
        second = copy.deepcopy(first)
        second["evidence_manifest"][0]["sha256"] = "c" * 64
        self.assertNotEqual(
            sha256_json(first),
            sha256_json(second),
        )

    def test_59_task_v2_aggregation_remains_input_order_invariant(self):
        bound_task = task_v2()
        first = bind_result_to_task(
            result(
                submission_id="v2-order-a",
                provider="provider-a",
                model="model-a",
            ),
            bound_task,
        )
        second = bind_result_to_task(
            result(
                submission_id="v2-order-b",
                provider="provider-b",
                model="model-b",
                position="OPPOSE",
                assertion="Contrarian v2 result.",
            ),
            bound_task,
        )
        forward = aggregate_results(bound_task, [first, second])
        reverse = aggregate_results(bound_task, [second, first])
        self.assertEqual(forward, reverse)


    def test_60_task_v2_source_ref_requires_declared_source_provenance(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"] = ["SOURCE_REF"]
        bound_task["evidence_manifest"][0].update(
            {
                "primitive": "SOURCE_REF",
                "ref": "manifest-only-source",
                "sha256": "b" * 64,
            }
        )
        value = bind_result_to_task(
            result(submission_id="v2-source-not-in-source-refs"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "SOURCE_REF",
                "ref": "manifest-only-source",
                "sha256": "b" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, value)

    def test_61_task_v2_public_evidence_requires_manifest_and_source_digest(self):
        bound_task = task_v2()
        bound_task["allowed_primitives"] = ["PUBLIC_EVIDENCE_REF"]
        bound_task["evidence_manifest"][0].update(
            {
                "primitive": "PUBLIC_EVIDENCE_REF",
                "ref": "packet-v1",
                "sha256": "a" * 64,
            }
        )
        value = bind_result_to_task(
            result(submission_id="v2-public-exact"),
            bound_task,
        )
        value["findings"][0]["evidence"].update(
            {
                "primitive": "PUBLIC_EVIDENCE_REF",
                "ref": "packet-v1",
                "sha256": "a" * 64,
            }
        )
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

        broken = copy.deepcopy(value)
        broken["findings"][0]["evidence"]["sha256"] = "c" * 64
        with self.assertRaises(ResearchContractError):
            validate_result_for_task(bound_task, broken)


    def test_62_task_v2_source_manifest_must_reference_source_refs(self):
        value = task_v2()
        value["allowed_primitives"] = ["SOURCE_REF"]
        value["evidence_manifest"][0].update(
            {
                "primitive": "SOURCE_REF",
                "ref": "manifest-only-source",
                "sha256": "b" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_63_task_v2_source_manifest_digest_must_match_source_refs(self):
        value = task_v2()
        value["allowed_primitives"] = ["SOURCE_REF"]
        value["evidence_manifest"][0].update(
            {
                "primitive": "SOURCE_REF",
                "ref": "packet-v1",
                "sha256": "b" * 64,
            }
        )
        with self.assertRaises(ResearchContractError):
            validate_task(value)

    def test_64_task_v2_exact_source_manifest_validates_at_task_time(self):
        value = task_v2()
        value["allowed_primitives"] = ["SOURCE_REF"]
        value["evidence_manifest"][0].update(
            {
                "primitive": "SOURCE_REF",
                "ref": "packet-v1",
                "sha256": "a" * 64,
            }
        )
        self.assertEqual(validate_task(value), value)


    def test_65_aggregate_v1_shape_remains_unchanged(self):
        value = aggregate_results(
            task(),
            [result(submission_id="v1-shape")],
        )
        self.assertEqual(
            value["schema"],
            "MULTIVERSE_RESEARCH_AGGREGATE_v1",
        )
        self.assertIn("unique_model_identity_count", value)
        self.assertNotIn(
            "observed_unique_provider_model_count",
            value,
        )

    def test_66_v2_same_model_two_roles_not_two_models(self):
        values = [
            result(
                submission_id="same-model-architecture",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
            ),
            result(
                submission_id="same-model-security",
                provider="provider-a",
                model="model-a",
                role="security_challenge",
            ),
        ]
        value = aggregate_results_v2(task(), values)
        claim = value["claims"][0]
        self.assertEqual(
            value["observed_unique_advisory_identity_count"],
            2,
        )
        self.assertEqual(
            value["observed_unique_provider_model_count"],
            1,
        )
        self.assertEqual(
            value["observed_unique_provider_count"],
            1,
        )
        self.assertEqual(
            claim["advisory_identity_position_counts"][
                "SUPPORT"
            ],
            2,
        )
        self.assertEqual(
            claim["provider_model_position_presence_counts"][
                "SUPPORT"
            ],
            1,
        )

    def test_67_v2_observed_and_completed_diversity_are_separate(self):
        values = [
            result(
                submission_id="completed-provider",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
            ),
            result(
                submission_id="failed-provider",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
                status="INFRA_FAILURE",
            ),
        ]
        value = aggregate_results_v2(task(), values)
        self.assertEqual(
            value["observed_unique_provider_model_count"],
            2,
        )
        self.assertEqual(
            value["completed_unique_provider_model_count"],
            1,
        )
        self.assertEqual(
            value["observed_unique_provider_count"],
            2,
        )
        self.assertEqual(
            value["completed_unique_provider_count"],
            1,
        )

    def test_68_v2_role_conditioned_divergence_is_not_cross_model(self):
        values = [
            result(
                submission_id="same-model-support",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
                position="SUPPORT",
            ),
            result(
                submission_id="same-model-oppose",
                provider="provider-a",
                model="model-a",
                role="security_challenge",
                position="OPPOSE",
                assertion="Role-conditioned opposition.",
            ),
        ]
        claim = aggregate_results_v2(
            task(),
            values,
        )["claims"][0]
        self.assertTrue(
            claim["role_conditioned_divergence"]
        )
        self.assertFalse(
            claim["cross_model_divergence"]
        )
        self.assertFalse(
            claim["cross_provider_divergence"]
        )

    def test_69_v2_two_models_same_provider_are_cross_model_only(self):
        values = [
            result(
                submission_id="model-a-support",
                provider="provider-a",
                model="model-a",
                position="SUPPORT",
            ),
            result(
                submission_id="model-b-oppose",
                provider="provider-a",
                model="model-b",
                position="OPPOSE",
                assertion="Second model opposes.",
            ),
        ]
        claim = aggregate_results_v2(
            task(),
            values,
        )["claims"][0]
        self.assertTrue(
            claim["cross_model_divergence"]
        )
        self.assertFalse(
            claim["cross_provider_divergence"]
        )

    def test_70_v2_two_providers_are_cross_provider_divergent(self):
        values = [
            result(
                submission_id="provider-a-support",
                provider="provider-a",
                model="model-a",
                position="SUPPORT",
            ),
            result(
                submission_id="provider-b-oppose",
                provider="provider-b",
                model="model-b",
                position="OPPOSE",
                assertion="Second provider opposes.",
            ),
        ]
        claim = aggregate_results_v2(
            task(),
            values,
        )["claims"][0]
        self.assertTrue(
            claim["cross_model_divergence"]
        )
        self.assertTrue(
            claim["cross_provider_divergence"]
        )

    def test_71_v2_unknown_second_model_does_not_fake_cross_model_divergence(self):
        values = [
            result(
                submission_id="role-support",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
                position="SUPPORT",
            ),
            result(
                submission_id="role-oppose",
                provider="provider-a",
                model="model-a",
                role="security_challenge",
                position="OPPOSE",
                assertion="Same model role opposition.",
            ),
            result(
                submission_id="unknown-second-model",
                provider="provider-a",
                model="model-b",
                role="architecture_challenge",
                position="UNKNOWN",
                assertion="Second model is uncertain.",
            ),
        ]
        claim = aggregate_results_v2(
            task(),
            values,
        )["claims"][0]
        self.assertTrue(
            claim["role_conditioned_divergence"]
        )
        self.assertFalse(
            claim["cross_model_divergence"]
        )

    def test_72_v2_exact_retry_duplicate_does_not_inflate_diversity(self):
        first = result(
            submission_id="retry-original",
            provider="provider-a",
            model="model-a",
        )
        second = result(
            submission_id="retry-copy",
            provider="provider-a",
            model="model-a",
        )
        value = aggregate_results_v2(
            task(),
            [first, second],
        )
        self.assertEqual(
            value["observed_unique_advisory_identity_count"],
            1,
        )
        self.assertEqual(
            value["observed_unique_provider_model_count"],
            1,
        )
        self.assertEqual(
            value["observed_unique_provider_count"],
            1,
        )

    def test_73_v2_aggregate_is_input_order_invariant(self):
        values = [
            result(
                submission_id="order-a",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
                position="SUPPORT",
            ),
            result(
                submission_id="order-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
                position="OPPOSE",
                assertion="Order invariant opposition.",
            ),
        ]
        forward = aggregate_results_v2(task(), values)
        reverse = aggregate_results_v2(
            task(),
            list(reversed(values)),
        )
        self.assertEqual(forward, reverse)

    def test_74_v2_has_distinct_schema_and_digest(self):
        values = [
            result(
                submission_id="schema-digest",
            )
        ]
        v1 = aggregate_results(task(), values)
        v2 = aggregate_results_v2(task(), values)
        self.assertEqual(
            v2["schema"],
            "MULTIVERSE_RESEARCH_AGGREGATE_v2",
        )
        self.assertNotIn(
            "unique_model_identity_count",
            v2,
        )
        self.assertNotEqual(
            v1["aggregate_sha256"],
            v2["aggregate_sha256"],
        )


    def test_75_valid_synthetic_assignment(self):
        bound_task = task_v2()
        value = assignment(bound_task)
        self.assertEqual(
            validate_assignment(bound_task, value),
            value,
        )

    def test_76_assignment_requires_task_v2(self):
        bound_task = task()
        value = assignment(task_v2())
        value["task_sha256"] = sha256_json(bound_task)
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_77_assignment_binds_exact_task_digest(self):
        bound_task = task_v2()
        value = assignment(bound_task)
        value["task_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_78_assignment_role_must_be_requested(self):
        bound_task = task_v2()
        value = assignment(
            bound_task,
            role="unrequested-role",
        )
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_79_assignment_snapshot_must_match_task(self):
        bound_task = task_v2()
        value = assignment(bound_task)
        value["snapshot_id"] = "snapshot-other"
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_80_assignment_cannot_widen_compute_or_output(self):
        bound_task = task_v2()
        too_much_compute = assignment(bound_task)
        too_much_compute["max_compute_seconds"] = (
            bound_task["constraints"]["max_compute_seconds"] + 1
        )
        with self.assertRaises(ResearchContractError):
            validate_assignment(
                bound_task,
                too_much_compute,
            )

        too_much_output = assignment(bound_task)
        too_much_output["max_output_bytes"] = (
            bound_task["constraints"]["max_output_bytes"] + 1
        )
        with self.assertRaises(ResearchContractError):
            validate_assignment(
                bound_task,
                too_much_output,
            )

    def test_81_assignment_cannot_widen_research_network(self):
        bound_task = task_v2()
        bound_task["constraints"]["network_access"] = "NONE"
        value = assignment(bound_task)
        value["research_network_access"] = "PUBLIC_READ_ONLY"
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_82_synthetic_assignment_forbids_provider_transport(self):
        bound_task = task_v2()
        value = assignment(bound_task)
        value[
            "provider_transport_policy_ref"
        ] = "provider-transport-001"
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_83_live_assignment_requires_transport_and_attestation(self):
        bound_task = task_v2()
        valid = assignment(
            bound_task,
            provider="provider-a",
            model="model-a",
            execution_mode="LIVE_ADVISORY",
        )
        self.assertEqual(
            validate_assignment(bound_task, valid),
            valid,
        )

        missing_transport = copy.deepcopy(valid)
        missing_transport[
            "provider_transport_policy_ref"
        ] = "NONE"
        with self.assertRaises(ResearchContractError):
            validate_assignment(
                bound_task,
                missing_transport,
            )

        missing_attestation = copy.deepcopy(valid)
        missing_attestation["attestation_required"] = False
        with self.assertRaises(ResearchContractError):
            validate_assignment(
                bound_task,
                missing_attestation,
            )

    def test_84_assignment_cannot_predate_task(self):
        bound_task = task_v2()
        value = assignment(bound_task)
        value["created_at"] = "2026-09-06T23:59:59Z"
        with self.assertRaises(ResearchContractError):
            validate_assignment(bound_task, value)

    def test_85_valid_result_v2_binds_exact_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        self.assertEqual(
            validate_result_v2_for_assignment(
                bound_task,
                bound_assignment,
                value,
            ),
            value,
        )

    def test_86_result_v2_rejects_wrong_assignment_digest(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        value["assignment_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_result_v2_for_assignment(
                bound_task,
                bound_assignment,
                value,
            )

    def test_87_result_v2_identity_must_match_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        for key, replacement in (
            ("provider", "provider-other"),
            ("model", "model-other"),
            ("role", "security_challenge"),
        ):
            value = result_v2(
                bound_task,
                bound_assignment,
                submission_id=f"identity-{key}",
            )
            value["model_identity"][key] = replacement
            with self.assertRaises(ResearchContractError):
                validate_result_v2_for_assignment(
                    bound_task,
                    bound_assignment,
                    value,
                )

    def test_88_result_v2_cannot_predate_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        value["produced_at"] = "2026-09-07T00:00:29Z"
        with self.assertRaises(ResearchContractError):
            validate_result_v2_for_assignment(
                bound_task,
                bound_assignment,
                value,
            )

    def test_89_assignment_mutation_invalidates_bound_result(self):
        bound_task = task_v2()
        first_assignment = assignment(bound_task)
        value = result_v2(
            bound_task,
            first_assignment,
        )
        changed_assignment = copy.deepcopy(
            first_assignment
        )
        changed_assignment["target_model"] = "model-b"
        self.assertNotEqual(
            assignment_sha256(
                bound_task,
                first_assignment,
            ),
            assignment_sha256(
                bound_task,
                changed_assignment,
            ),
        )
        with self.assertRaises(ResearchContractError):
            validate_result_v2_for_assignment(
                bound_task,
                changed_assignment,
                value,
            )

    def test_90_result_v1_historical_path_remains_unchanged(self):
        bound_task = task_v2()
        value = bind_result_to_task(
            result(submission_id="historical-v1-result"),
            bound_task,
        )
        self.assertEqual(
            validate_result_for_task(bound_task, value),
            value,
        )

    def test_91_result_v2_digest_ignores_submission_id_but_binds_assignment(self):
        bound_task = task_v2()
        first_assignment = assignment(bound_task)
        first = result_v2(
            bound_task,
            first_assignment,
            submission_id="result-v2-first",
        )
        second = result_v2(
            bound_task,
            first_assignment,
            submission_id="result-v2-second",
        )
        self.assertEqual(
            result_v2_content_digest(
                bound_task,
                first_assignment,
                first,
            ),
            result_v2_content_digest(
                bound_task,
                first_assignment,
                second,
            ),
        )

        second_assignment = assignment(
            bound_task,
            assignment_id="assignment-002",
            model="model-b",
        )
        changed = result_v2(
            bound_task,
            second_assignment,
            submission_id="result-v2-third",
        )
        self.assertNotEqual(
            result_v2_content_digest(
                bound_task,
                first_assignment,
                first,
            ),
            result_v2_content_digest(
                bound_task,
                second_assignment,
                changed,
            ),
        )


    def test_92_valid_fanout_plan_binds_valid_assignments(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="fanout-a",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
            ),
            assignment(
                bound_task,
                assignment_id="fanout-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        self.assertEqual(
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            ),
            plan,
        )

    def test_93_fanout_plan_hashes_must_be_canonical_order(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="order-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="order-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        plan["assignment_sha256s"] = list(
            reversed(plan["assignment_sha256s"])
        )
        if plan["assignment_sha256s"] != sorted(
            plan["assignment_sha256s"]
        ):
            with self.assertRaises(ResearchContractError):
                validate_fanout_plan(
                    bound_task,
                    assignments,
                    plan,
                )

    def test_94_fanout_rejects_duplicate_assignment_ids(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="same-assignment",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="same-assignment",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        with self.assertRaises(ResearchContractError):
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            )

    def test_95_fanout_rejects_duplicate_logical_target(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="sample-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="sample-b",
                provider="provider-a",
                model="model-a",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        with self.assertRaises(ResearchContractError):
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            )

    def test_96_fanout_allows_same_model_in_different_roles(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="role-a",
                provider="provider-a",
                model="model-a",
                role="architecture_challenge",
            ),
            assignment(
                bound_task,
                assignment_id="role-b",
                provider="provider-a",
                model="model-a",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        self.assertEqual(
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            ),
            plan,
        )

    def test_97_fanout_plan_binds_exact_assignment_set(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="exact-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="exact-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        plan["assignment_sha256s"] = plan[
            "assignment_sha256s"
        ][:-1]
        with self.assertRaises(ResearchContractError):
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            )

    def test_98_fanout_plan_cannot_predate_assignment(self):
        bound_task = task_v2()
        assignments = [assignment(bound_task)]
        assignments[0]["created_at"] = (
            "2026-09-07T00:00:50Z"
        )
        plan = fanout_plan(bound_task, assignments)
        with self.assertRaises(ResearchContractError):
            validate_fanout_plan(
                bound_task,
                assignments,
                plan,
            )

    def test_99_fanout_missing_assignment_is_explicit(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="missing-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="missing-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        first_result = result_v2(
            bound_task,
            assignments[0],
            submission_id="only-first",
        )
        summary = summarize_fanout_results(
            bound_task,
            assignments,
            plan,
            [first_result],
        )
        self.assertEqual(
            summary["planned_assignment_count"],
            2,
        )
        self.assertEqual(
            summary["observed_terminal_result_count"],
            1,
        )
        self.assertEqual(
            len(summary["missing_assignment_sha256s"]),
            1,
        )
        self.assertFalse(summary["all_planned_observed"])
        self.assertFalse(summary["all_planned_completed"])

    def test_100_fanout_all_planned_completed_is_explicit(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="complete-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="complete-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        results = [
            result_v2(
                bound_task,
                assignments[0],
                submission_id="complete-result-a",
            ),
            result_v2(
                bound_task,
                assignments[1],
                submission_id="complete-result-b",
            ),
        ]
        summary = summarize_fanout_results(
            bound_task,
            assignments,
            plan,
            results,
        )
        self.assertTrue(summary["all_planned_observed"])
        self.assertTrue(summary["all_planned_completed"])
        self.assertEqual(
            summary["completed_assignment_count"],
            2,
        )

    def test_101_fanout_infra_failure_is_observed_not_completed(self):
        bound_task = task_v2()
        assignments = [assignment(bound_task)]
        plan = fanout_plan(bound_task, assignments)
        failed = result_v2(
            bound_task,
            assignments[0],
            submission_id="fanout-infra",
            status="INFRA_FAILURE",
        )
        summary = summarize_fanout_results(
            bound_task,
            assignments,
            plan,
            [failed],
        )
        self.assertTrue(summary["all_planned_observed"])
        self.assertFalse(summary["all_planned_completed"])
        self.assertEqual(
            summary["completed_assignment_count"],
            0,
        )
        self.assertEqual(
            summary["status_counts"]["INFRA_FAILURE"],
            1,
        )

    def test_102_fanout_rejects_unplanned_result(self):
        bound_task = task_v2()
        planned = assignment(
            bound_task,
            assignment_id="planned",
            provider="provider-a",
            model="model-a",
        )
        unplanned = assignment(
            bound_task,
            assignment_id="unplanned",
            provider="provider-b",
            model="model-b",
        )
        plan = fanout_plan(bound_task, [planned])
        value = result_v2(
            bound_task,
            unplanned,
            submission_id="unplanned-result",
        )
        with self.assertRaises(ResearchContractError):
            summarize_fanout_results(
                bound_task,
                [planned],
                plan,
                [value],
            )

    def test_103_fanout_rejects_duplicate_result_for_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        plan = fanout_plan(
            bound_task,
            [bound_assignment],
        )
        results = [
            result_v2(
                bound_task,
                bound_assignment,
                submission_id="duplicate-a",
            ),
            result_v2(
                bound_task,
                bound_assignment,
                submission_id="duplicate-b",
            ),
        ]
        with self.assertRaises(ResearchContractError):
            summarize_fanout_results(
                bound_task,
                [bound_assignment],
                plan,
                results,
            )

    def test_104_fanout_batch_summary_is_input_order_invariant(self):
        bound_task = task_v2()
        assignments = [
            assignment(
                bound_task,
                assignment_id="batch-a",
                provider="provider-a",
                model="model-a",
            ),
            assignment(
                bound_task,
                assignment_id="batch-b",
                provider="provider-b",
                model="model-b",
                role="security_challenge",
            ),
        ]
        plan = fanout_plan(bound_task, assignments)
        results = [
            result_v2(
                bound_task,
                assignments[0],
                submission_id="batch-result-a",
            ),
            result_v2(
                bound_task,
                assignments[1],
                submission_id="batch-result-b",
                status="REFUSED",
            ),
        ]
        forward = summarize_fanout_results(
            bound_task,
            assignments,
            plan,
            results,
        )
        reverse = summarize_fanout_results(
            bound_task,
            assignments,
            plan,
            list(reversed(results)),
        )
        self.assertEqual(forward, reverse)

    def test_105_assignment_mutation_invalidates_fanout_plan(self):
        bound_task = task_v2()
        assignments = [assignment(bound_task)]
        plan = fanout_plan(bound_task, assignments)
        original_plan_sha = fanout_plan_sha256(
            bound_task,
            assignments,
            plan,
        )
        changed = [copy.deepcopy(assignments[0])]
        changed[0]["target_model"] = "model-b"
        with self.assertRaises(ResearchContractError):
            validate_fanout_plan(
                bound_task,
                changed,
                plan,
            )
        changed_plan = fanout_plan(
            bound_task,
            changed,
            plan_id="fanout-plan-002",
        )
        self.assertNotEqual(
            original_plan_sha,
            fanout_plan_sha256(
                bound_task,
                changed,
                changed_plan,
            ),
        )


    def test_106_valid_model_target_policy(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
        )
        policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        self.assertEqual(
            validate_model_target_policy(
                bound_task,
                bound_assignment,
                policy,
            ),
            policy,
        )

    def test_107_model_target_policy_binds_exact_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy["assignment_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_model_target_policy(
                bound_task,
                bound_assignment,
                policy,
            )

    def test_108_model_target_provider_and_model_match_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        for key, value in (
            ("provider", "provider-other"),
            ("requested_model_id", "model-other"),
        ):
            policy = model_target_policy(
                bound_task,
                bound_assignment,
            )
            policy[key] = value
            with self.assertRaises(ResearchContractError):
                validate_model_target_policy(
                    bound_task,
                    bound_assignment,
                    policy,
                )

    def test_109_model_target_alias_is_rejected(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        policy = model_target_policy(
            bound_task,
            bound_assignment,
            classification="ALIAS",
        )
        with self.assertRaises(ResearchContractError):
            validate_model_target_policy(
                bound_task,
                bound_assignment,
                policy,
            )

    def test_110_model_target_preview_experimental_unknown_rejected(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        for classification in (
            "PREVIEW",
            "EXPERIMENTAL",
            "UNKNOWN",
        ):
            policy = model_target_policy(
                bound_task,
                bound_assignment,
                classification=classification,
            )
            with self.assertRaises(ResearchContractError):
                validate_model_target_policy(
                    bound_task,
                    bound_assignment,
                    policy,
                )

    def test_111_model_target_policy_cannot_weaken_first_pilot_flags(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        for key, weakened in (
            ("alias_allowed", True),
            ("preview_allowed", True),
            ("experimental_allowed", True),
            ("resolved_model_id_required", False),
            ("stable_provider_api_required", False),
        ):
            policy = model_target_policy(
                bound_task,
                bound_assignment,
            )
            policy[key] = weakened
            with self.assertRaises(ResearchContractError):
                validate_model_target_policy(
                    bound_task,
                    bound_assignment,
                    policy,
                )

    def test_112_model_target_classification_evidence_digest_required(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy["classification_evidence_sha256"] = None
        with self.assertRaises(ResearchContractError):
            validate_model_target_policy(
                bound_task,
                bound_assignment,
                policy,
            )

    def test_113_resolved_model_id_must_match_requested_model(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
        )
        policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        self.assertEqual(
            validate_resolved_model_id(
                bound_task,
                bound_assignment,
                policy,
                "model-stable-001",
            ),
            "model-stable-001",
        )
        with self.assertRaises(ResearchContractError):
            validate_resolved_model_id(
                bound_task,
                bound_assignment,
                policy,
                "model-other",
            )

    def test_114_model_target_policy_digest_binds_evidence(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        first = model_target_policy(
            bound_task,
            bound_assignment,
        )
        second = copy.deepcopy(first)
        second["classification_evidence_sha256"] = "7" * 64
        self.assertNotEqual(
            model_target_policy_sha256(
                bound_task,
                bound_assignment,
                first,
            ),
            model_target_policy_sha256(
                bound_task,
                bound_assignment,
                second,
            ),
        )


if __name__ == "__main__":
    unittest.main()
