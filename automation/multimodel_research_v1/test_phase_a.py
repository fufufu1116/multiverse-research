from __future__ import annotations

import copy
import json
from pathlib import Path
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
from automation.multimodel_research_v1.capability import (
    capability_policy_sha256,
    validate_capability_policy,
)
from automation.multimodel_research_v1.prompting import (
    build_provider_neutral_prompt,
    provider_neutral_prompt_sha256,
    validate_provider_neutral_prompt,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)
from automation.multimodel_research_v1.termination import (
    termination_record_sha256,
    validate_termination_record,
)
from automation.multimodel_research_v1.receipt import (
    execution_receipt_sha256,
    validate_execution_receipt,
)
from automation.multimodel_research_v1.smoke_profile import (
    live_smoke_profile_sha256,
    validate_live_smoke_profile,
)
from automation.multimodel_research_v1.gemini_adapter import (
    gemini_render_sha256,
    parse_gemini_interactions_v1_response,
    render_gemini_interactions_v1,
)
from automation.multimodel_research_v1.claude_adapter import (
    claude_render_sha256,
    parse_claude_messages_response,
    render_claude_messages_request,
)
from automation.multimodel_research_v1.transport_binding import (
    transport_binding_sha256,
    validate_transport_binding,
)
from automation.multimodel_research_v1.observation_binding import (
    provider_observation_binding_sha256,
    validate_provider_observation_binding,
)
from automation.multimodel_research_v1.execution_prep import (
    live_execution_prep_sha256,
    validate_live_execution_prep,
)
from automation.multimodel_research_v1.readiness import (
    build_live_provider_readiness_report,
    live_provider_readiness_sha256,
    validate_live_provider_readiness_report,
)
from automation.multimodel_research_v1.provider_catalog import (
    catalog_entry,
    catalog_entry_sha256,
    estimate_smoke_cost_usd_micros,
    validate_first_smoke_candidate,
    validate_provider_catalog,
)
from automation.multimodel_research_v1.pilot_dry_run import (
    build_first_provider_pilot_dry_run,
    build_pilot_candidate_matrix,
    first_provider_pilot_dry_run_sha256,
    validate_first_provider_pilot_dry_run,
)
from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
    build_pilot_freshness_binding,
    catalog_freshness_sha256,
    pilot_freshness_binding_sha256,
    validate_catalog_freshness_receipt,
    validate_pilot_freshness_binding,
)
from automation.multimodel_research_v1.time_attestation import (
    build_catalog_freshness_time_binding,
    catalog_freshness_time_binding_sha256,
    execution_time_attestation_sha256,
    validate_catalog_freshness_time_binding,
    validate_execution_time_attestation,
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


def capability_policy(
    bound_task: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
) -> dict:
    return {
        "schema": "MULTIVERSE_PROVIDER_CAPABILITY_POLICY_v1",
        "policy_id": "capability-policy-001",
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
            ),
        "tools": "NONE",
        "provider_retrieval_search": "NONE",
        "code_execution": "NONE",
        "file_access": "NONE",
        "provider_memory": "NONE",
        "function_calling": "NONE",
        "structured_output": "JSON_ONLY",
        "streaming": False,
        "nonauthority": nonauthority(),
    }


def provider_neutral_prompt(
    bound_task: dict,
    role: str = "architecture_challenge",
) -> dict:
    return build_provider_neutral_prompt(
        bound_task,
        role,
        "6" * 64,
    )


def request_envelope(
    bound_task: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
    bound_capability_policy: dict,
    bound_prompt: dict,
) -> dict:
    return {
        "schema": "MULTIVERSE_PROVIDER_REQUEST_ENVELOPE_v1",
        "request_id": "provider-request-001",
        "task_sha256": sha256_json(bound_task),
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
            ),
        "capability_policy_sha256":
            capability_policy_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
            ),
        "provider_neutral_prompt_sha256":
            provider_neutral_prompt_sha256(
                bound_task,
                bound_prompt,
            ),
        "provider_transport_policy_ref":
            bound_assignment[
                "provider_transport_policy_ref"
            ],
        "created_at": "2026-09-07T00:00:40Z",
        "objective_classification": "SYNTHETIC",
        "classification_evidence_ref":
            "synthetic-data-attestation-001",
        "classification_evidence_sha256": "5" * 64,
        "egress_items": sorted(
            [
                {
                    "primitive": item["primitive"],
                    "ref": item["ref"],
                    "sha256": item["sha256"],
                    "classification": "SYNTHETIC",
                }
                for item in bound_task["evidence_manifest"]
            ],
            key=lambda item: (
                item["primitive"],
                item["ref"],
                item["sha256"],
            ),
        ),
        "outbound_payload_sha256": "4" * 64,
        "nonauthority": nonauthority(),
    }


def termination_record(
    bound_task: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
    bound_capability_policy: dict,
    bound_prompt: dict,
    bound_request_envelope: dict,
    *,
    normalized_state: str = "COMPLETED",
) -> dict:
    response_id = (
        None
        if normalized_state == "TRANSPORT_FAILURE"
        else "provider-response-001"
    )
    return {
        "schema": "MULTIVERSE_PROVIDER_TERMINATION_RECORD_v1",
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "request_envelope_sha256":
            request_envelope_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
                bound_prompt,
                bound_request_envelope,
            ),
        "provider_response_id": response_id,
        "native_reason": normalized_state.lower(),
        "normalized_state": normalized_state,
        "input_tokens": 10,
        "output_tokens": 20,
        "usage_metadata_sha256": "2" * 64,
        "response_received_at": "2026-09-07T00:00:55Z",
        "nonauthority": nonauthority(),
    }


def execution_receipt(
    bound_task: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
    bound_capability_policy: dict,
    bound_prompt: dict,
    bound_request_envelope: dict,
    bound_termination_record: dict,
    bound_result: dict,
    *,
    attestation_state: str = "LIVE_ATTESTED",
    observed_model_id: str | None = None,
) -> dict:
    if observed_model_id is None and (
        attestation_state == "LIVE_ATTESTED"
    ):
        observed_model_id = bound_assignment["target_model"]
    return {
        "schema": "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1",
        "receipt_id": "provider-receipt-001",
        "task_sha256": sha256_json(bound_task),
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "request_envelope_sha256":
            request_envelope_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
                bound_prompt,
                bound_request_envelope,
            ),
        "termination_record_sha256":
            termination_record_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
                bound_prompt,
                bound_request_envelope,
                bound_termination_record,
            ),
        "submission_id": bound_result["submission_id"],
        "observed_provider":
            bound_assignment["target_provider"],
        "observed_model_id": observed_model_id,
        "provider_response_id":
            bound_termination_record[
                "provider_response_id"
            ],
        "provider_response_sha256": "1" * 64,
        "result_sha256": sha256_json(bound_result),
        "adapter_sha256":
            bound_assignment["adapter_sha256"],
        "request_started_at": "2026-09-07T00:00:45Z",
        "response_received_at":
            bound_termination_record[
                "response_received_at"
            ],
        "receipt_created_at": "2026-09-07T00:01:05Z",
        "attestation_state": attestation_state,
        "nonauthority": nonauthority(),
    }


def live_smoke_profile(
    bound_task: dict,
    assignments: list[dict],
    bound_fanout_plan: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
    bound_capability_policy: dict,
    bound_prompt: dict,
    bound_request_envelope: dict,
) -> dict:
    return {
        "schema": "MULTIVERSE_LIVE_PROVIDER_SMOKE_PROFILE_v1",
        "profile_id": "live-smoke-profile-001",
        "fanout_plan_sha256": fanout_plan_sha256(
            bound_task,
            assignments,
            bound_fanout_plan,
        ),
        "assignment_sha256": assignment_sha256(
            bound_task,
            bound_assignment,
        ),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
            ),
        "capability_policy_sha256":
            capability_policy_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
            ),
        "request_envelope_sha256":
            request_envelope_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
                bound_prompt,
                bound_request_envelope,
            ),
        "planned_provider_count": 1,
        "planned_assignment_count": 1,
        "max_attempts_per_assignment": 1,
        "data_ceiling": "SYNTHETIC_ONLY",
        "structured_output": "JSON_ONLY",
        "streaming": False,
        "protected_data": False,
        "live_business_effect": False,
        "runtime_activation": False,
        "adoption_authority": False,
        "nonauthority": nonauthority(),
    }


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
        },
        "required": ["status"],
        "additionalProperties": False,
    }


def gemini_response(
    *,
    status: str = "completed",
    model: str = "model-stable-001",
    text: str = '{"status":"ok"}',
) -> dict:
    return {
        "id": "gemini-response-001",
        "status": status,
        "model": model,
        "usage": {
            "total_tokens": 30,
            "total_input_tokens": 10,
            "total_output_tokens": 20,
        },
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    }


def claude_response(
    *,
    stop_reason: str = "end_turn",
    model: str = "model-stable-001",
    text: str = '{"status":"ok"}',
) -> dict:
    return {
        "id": "claude-response-001",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [
            {
                "type": "text",
                "text": text,
            }
        ],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "stop_details": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
        },
    }


def live_execution_prep(
    bound_task: dict,
    assignments: list[dict],
    bound_fanout_plan: dict,
    bound_assignment: dict,
    bound_model_target_policy: dict,
    bound_capability_policy: dict,
    bound_prompt: dict,
    bound_request_envelope: dict,
    bound_smoke_profile: dict,
    schema: dict,
    render: dict,
) -> dict:
    provider = render["provider"]
    target = {
        "GOOGLE_GEMINI": (
            "generativelanguage.googleapis.com",
            "INTERACTIONS_CREATE_V1",
            "credential-handle-gemini-smoke",
        ),
        "ANTHROPIC_CLAUDE": (
            "api.anthropic.com",
            "MESSAGES_CREATE_V1",
            "credential-handle-claude-smoke",
        ),
    }[provider]
    return {
        "schema": "MULTIVERSE_LIVE_PROVIDER_EXECUTION_PREP_v1",
        "prep_id": "live-execution-prep-001",
        "provider": provider,
        "smoke_profile_sha256": live_smoke_profile_sha256(
            bound_task,
            assignments,
            bound_fanout_plan,
            bound_assignment,
            bound_model_target_policy,
            bound_capability_policy,
            bound_prompt,
            bound_request_envelope,
            bound_smoke_profile,
        ),
        "transport_binding_sha256":
            transport_binding_sha256(
                bound_task,
                bound_assignment,
                bound_model_target_policy,
                bound_capability_policy,
                bound_prompt,
                bound_request_envelope,
                schema,
                render,
            ),
        "allowed_host": target[0],
        "allowed_operation": target[1],
        "network_scope": "PROVIDER_API_ONLY",
        "credential_handle_ref": target[2],
        "credential_material_in_repository": False,
        "max_attempts": 1,
        "max_input_tokens": 32768,
        "max_output_tokens": 4096,
        "proposed_max_cost_usd_micros": 1_000_000,
        "provider_call_authority_required": True,
        "credential_authority_required": True,
        "spend_authority_required": True,
        "runtime_activation": False,
        "live_business_effect": False,
        "protected_data": False,
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


    def test_115_valid_capability_policy(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        self.assertEqual(
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            ),
            policy,
        )

    def test_116_capability_binds_exact_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["assignment_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_117_capability_binds_exact_model_target_policy(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["model_target_policy_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_118_capability_tools_are_forbidden(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["tools"] = "ENABLED"
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_119_capability_provider_retrieval_is_forbidden(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["provider_retrieval_search"] = "ENABLED"
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_120_capability_code_execution_is_forbidden(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["code_execution"] = "ENABLED"
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_121_capability_file_memory_function_surfaces_are_forbidden(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        for key in (
            "file_access",
            "provider_memory",
            "function_calling",
        ):
            policy = capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
            )
            policy[key] = "ENABLED"
            with self.assertRaises(ResearchContractError):
                validate_capability_policy(
                    bound_task,
                    bound_assignment,
                    target_policy,
                    policy,
                )

    def test_122_capability_requires_json_only_structured_output(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["structured_output"] = "TEXT"
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_123_capability_streaming_is_forbidden(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        policy["streaming"] = True
        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                target_policy,
                policy,
            )

    def test_124_model_target_change_invalidates_capability_policy(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        original_digest = capability_policy_sha256(
            bound_task,
            bound_assignment,
            target_policy,
            policy,
        )

        changed_target = copy.deepcopy(target_policy)
        changed_target[
            "classification_evidence_sha256"
        ] = "7" * 64

        with self.assertRaises(ResearchContractError):
            validate_capability_policy(
                bound_task,
                bound_assignment,
                changed_target,
                policy,
            )

        changed_policy = capability_policy(
            bound_task,
            bound_assignment,
            changed_target,
        )
        self.assertNotEqual(
            original_digest,
            capability_policy_sha256(
                bound_task,
                bound_assignment,
                changed_target,
                changed_policy,
            ),
        )


    def test_125_provider_neutral_prompt_is_provider_independent(self):
        bound_task = task_v2()
        first_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-a",
        )
        second_assignment = assignment(
            bound_task,
            assignment_id="assignment-provider-b",
            provider="provider-b",
            model="model-b",
        )
        first_prompt = provider_neutral_prompt(
            bound_task,
            first_assignment["requested_role"],
        )
        second_prompt = provider_neutral_prompt(
            bound_task,
            second_assignment["requested_role"],
        )
        self.assertEqual(first_prompt, second_prompt)
        self.assertEqual(
            provider_neutral_prompt_sha256(
                bound_task,
                first_prompt,
            ),
            provider_neutral_prompt_sha256(
                bound_task,
                second_prompt,
            ),
        )

    def test_126_prompt_role_must_be_requested(self):
        bound_task = task_v2()
        with self.assertRaises(ResearchContractError):
            build_provider_neutral_prompt(
                bound_task,
                "unrequested-role",
                "6" * 64,
            )

    def test_127_prompt_binds_exact_task_objective_and_digest(self):
        bound_task = task_v2()
        prompt = provider_neutral_prompt(bound_task)
        self.assertEqual(
            prompt["task_sha256"],
            sha256_json(bound_task),
        )
        self.assertEqual(
            prompt["objective"],
            bound_task["objective"],
        )
        changed = copy.deepcopy(bound_task)
        changed["objective"] = "Changed objective."
        changed_prompt = provider_neutral_prompt(changed)
        self.assertNotEqual(
            provider_neutral_prompt_sha256(
                bound_task,
                prompt,
            ),
            provider_neutral_prompt_sha256(
                changed,
                changed_prompt,
            ),
        )

    def test_128_prompt_response_schema_digest_is_bound(self):
        bound_task = task_v2()
        first = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            "6" * 64,
        )
        second = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            "7" * 64,
        )
        self.assertNotEqual(
            provider_neutral_prompt_sha256(
                bound_task,
                first,
            ),
            provider_neutral_prompt_sha256(
                bound_task,
                second,
            ),
        )

    def test_129_prompt_contains_exact_sorted_evidence_manifest(self):
        bound_task = task_v2()
        prompt = provider_neutral_prompt(bound_task)
        expected = sorted(
            copy.deepcopy(bound_task["evidence_manifest"]),
            key=lambda item: (
                item["primitive"],
                item["ref"],
                item["sha256"],
                item["observed_at"],
            ),
        )
        self.assertEqual(
            prompt["evidence_manifest"],
            expected,
        )

    def test_130_prompt_has_no_provider_or_model_target_fields(self):
        bound_task = task_v2()
        prompt = provider_neutral_prompt(bound_task)
        self.assertNotIn("provider", prompt)
        self.assertNotIn("model", prompt)
        self.assertNotIn("assignment_sha256", prompt)

    def test_131_prompt_exact_binding_rejects_mutation(self):
        bound_task = task_v2()
        prompt = provider_neutral_prompt(bound_task)
        prompt["objective"] = "Tampered."
        with self.assertRaises(ResearchContractError):
            validate_provider_neutral_prompt(
                bound_task,
                prompt,
            )

    def test_132_prompt_nonauthority_is_preserved(self):
        bound_task = task_v2()
        prompt = provider_neutral_prompt(bound_task)
        self.assertEqual(
            prompt["nonauthority"],
            bound_task["nonauthority"],
        )

    def test_133_valid_synthetic_only_request_envelope(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        self.assertEqual(
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            ),
            envelope,
        )

    def test_134_request_envelope_requires_live_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(bound_task)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_135_request_envelope_binds_exact_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["assignment_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_136_request_envelope_binds_model_and_capability_policies(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        for key in (
            "model_target_policy_sha256",
            "capability_policy_sha256",
        ):
            envelope = request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
            )
            envelope[key] = "0" * 64
            with self.assertRaises(ResearchContractError):
                validate_request_envelope(
                    bound_task,
                    bound_assignment,
                    target_policy,
                    cap_policy,
                    prompt,
                    envelope,
                )

    def test_137_request_envelope_binds_exact_prompt(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope[
            "provider_neutral_prompt_sha256"
        ] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_138_request_transport_policy_must_match_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope[
            "provider_transport_policy_ref"
        ] = "provider-transport-other"
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_139_request_cannot_predate_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["created_at"] = "2026-09-07T00:00:29Z"
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_140_request_first_smoke_requires_synthetic_classification(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["objective_classification"] = "PUBLIC"
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_141_request_classification_evidence_digest_required(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope[
            "classification_evidence_sha256"
        ] = None
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_142_request_egress_must_exactly_match_task_manifest(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["egress_items"][0]["ref"] = "other-ref"
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_143_request_outbound_payload_digest_required(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = None
        with self.assertRaises(ResearchContractError):
            validate_request_envelope(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
            )

    def test_144_request_digest_binds_exact_outbound_payload(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(bound_task)
        first = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        second = copy.deepcopy(first)
        second["outbound_payload_sha256"] = "3" * 64
        self.assertNotEqual(
            request_envelope_sha256(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                first,
            ),
            request_envelope_sha256(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                second,
            ),
        )


    def test_145_valid_completed_termination_record(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        self.assertEqual(
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            ),
            record,
        )

    def test_146_termination_binds_exact_request_envelope(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["request_envelope_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            )

    def test_147_termination_response_cannot_predate_request(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["response_received_at"] = "2026-09-07T00:00:39Z"
        with self.assertRaises(ResearchContractError):
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            )

    def test_148_transport_failure_may_have_no_provider_response_id(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            normalized_state="TRANSPORT_FAILURE",
        )
        self.assertIsNone(record["provider_response_id"])
        self.assertEqual(
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            ),
            record,
        )

    def test_149_completed_termination_requires_provider_response_id(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = None
        with self.assertRaises(ResearchContractError):
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            )

    def test_150_termination_usage_cannot_be_negative(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["input_tokens"] = -1
        with self.assertRaises(ResearchContractError):
            validate_termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
            )

    def test_151_valid_live_attested_execution_receipt(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="receipt-completed",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        self.assertEqual(
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            ),
            receipt,
        )

    def test_152_receipt_binds_exact_result_digest(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="receipt-result-digest",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        receipt["result_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_153_receipt_provider_response_digest_required(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        receipt["provider_response_sha256"] = None
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_154_receipt_adapter_must_match_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        receipt["adapter_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_155_receipt_timestamps_are_monotonic(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        receipt["receipt_created_at"] = "2026-09-07T00:00:59Z"
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_156_live_attested_receipt_requires_exact_model_id(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id="model-other",
        )
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_157_unverified_receipt_preserves_but_does_not_attest_model(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            attestation_state="LIVE_PROVIDER_ID_UNVERIFIED",
            observed_model_id="model-other",
        )
        self.assertEqual(
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            ),
            receipt,
        )
        self.assertEqual(
            receipt["attestation_state"],
            "LIVE_PROVIDER_ID_UNVERIFIED",
        )

    def test_158_termination_state_must_match_result_status(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        cases = (
            ("PROVIDER_BLOCKED", "REFUSED"),
            ("TRANSPORT_FAILURE", "INFRA_FAILURE"),
            ("PROVIDER_TRUNCATED", "INFRA_FAILURE"),
        )
        for termination_state, result_status in cases:
            record = termination_record(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                normalized_state=termination_state,
            )
            value = result_v2(
                bound_task,
                bound_assignment,
                submission_id=f"mapping-{termination_state}",
                status=result_status,
            )
            receipt = execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                attestation_state="LIVE_PROVIDER_ID_UNVERIFIED",
                observed_model_id=None,
            )
            self.assertEqual(
                validate_execution_receipt(
                    bound_task,
                    bound_assignment,
                    target_policy,
                    cap_policy,
                    prompt,
                    envelope,
                    record,
                    value,
                    receipt,
                ),
                receipt,
            )

    def test_159_receipt_response_id_must_match_termination(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
        )
        receipt["provider_response_id"] = "provider-response-other"
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            )

    def test_160_result_substitution_changes_receipt_binding(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        first = result_v2(
            bound_task,
            bound_assignment,
            submission_id="receipt-first",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            first,
        )
        original_receipt_digest = execution_receipt_sha256(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            first,
            receipt,
        )
        second = copy.deepcopy(first)
        second["submission_id"] = "receipt-second"
        with self.assertRaises(ResearchContractError):
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                second,
                receipt,
            )
        second_receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            second,
        )
        self.assertNotEqual(
            original_receipt_digest,
            execution_receipt_sha256(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                second,
                second_receipt,
            ),
        )


    def test_161_valid_live_smoke_profile(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        self.assertEqual(
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            ),
            profile,
        )

    def test_162_smoke_requires_exactly_one_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        second = assignment(
            bound_task,
            assignment_id="smoke-second",
            provider="provider-b",
            model="model-b",
            role="security_challenge",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment, second]
        plan = fanout_plan(bound_task, assignments)
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            )

    def test_163_smoke_requires_one_provider_and_one_assignment_count(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        profile["planned_provider_count"] = 2
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            )

        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        profile["planned_assignment_count"] = 2
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            )

    def test_164_smoke_requires_single_attempt(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        profile["max_attempts_per_assignment"] = 2
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            )

    def test_165_smoke_requires_synthetic_only_data(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        profile["data_ceiling"] = "PUBLIC"
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            )

    def test_166_smoke_binds_exact_fanout_and_assignment(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        for key in (
            "fanout_plan_sha256",
            "assignment_sha256",
        ):
            broken = copy.deepcopy(profile)
            broken[key] = "0" * 64
            with self.assertRaises(ResearchContractError):
                validate_live_smoke_profile(
                    bound_task,
                    assignments,
                    plan,
                    bound_assignment,
                    target_policy,
                    cap_policy,
                    prompt,
                    envelope,
                    broken,
                )

    def test_167_smoke_binds_exact_policies_and_request(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        for key in (
            "model_target_policy_sha256",
            "capability_policy_sha256",
            "request_envelope_sha256",
        ):
            broken = copy.deepcopy(profile)
            broken[key] = "0" * 64
            with self.assertRaises(ResearchContractError):
                validate_live_smoke_profile(
                    bound_task,
                    assignments,
                    plan,
                    bound_assignment,
                    target_policy,
                    cap_policy,
                    prompt,
                    envelope,
                    broken,
                )

    def test_168_smoke_requires_json_and_nonstreaming(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        broken = copy.deepcopy(profile)
        broken["structured_output"] = "TEXT"
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                broken,
            )

        broken = copy.deepcopy(profile)
        broken["streaming"] = True
        with self.assertRaises(ResearchContractError):
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                broken,
            )

    def test_169_smoke_forbids_protected_business_runtime_adoption_effects(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        for key in (
            "protected_data",
            "live_business_effect",
            "runtime_activation",
            "adoption_authority",
        ):
            broken = copy.deepcopy(profile)
            broken[key] = True
            with self.assertRaises(ResearchContractError):
                validate_live_smoke_profile(
                    bound_task,
                    assignments,
                    plan,
                    bound_assignment,
                    target_policy,
                    cap_policy,
                    prompt,
                    envelope,
                    broken,
                )

    def test_170_smoke_profile_digest_binds_request_envelope(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        original_digest = live_smoke_profile_sha256(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            profile,
        )
        changed_envelope = copy.deepcopy(envelope)
        changed_envelope[
            "outbound_payload_sha256"
        ] = "3" * 64
        changed_profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            changed_envelope,
        )
        self.assertNotEqual(
            original_digest,
            live_smoke_profile_sha256(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                changed_envelope,
                changed_profile,
            ),
        )

    def test_171_end_to_end_contract_chain_validates_without_provider_call(self):
        bound_task = task_v2()
        bound_assignment = assignment(
            bound_task,
            provider="provider-a",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        prompt = provider_neutral_prompt(
            bound_task,
            bound_assignment["requested_role"],
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        profile = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="e2e-contract-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            attestation_state="LIVE_PROVIDER_ID_UNVERIFIED",
            observed_model_id=None,
        )

        self.assertEqual(
            validate_live_smoke_profile(
                bound_task,
                assignments,
                plan,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                profile,
            ),
            profile,
        )
        self.assertEqual(
            validate_execution_receipt(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                record,
                value,
                receipt,
            ),
            receipt,
        )
        self.assertEqual(
            receipt["attestation_state"],
            "LIVE_PROVIDER_ID_UNVERIFIED",
        )


    def test_172_valid_gemini_v1_render(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertEqual(rendered["api_version"], "v1")
        self.assertEqual(
            rendered["sdk_surface"],
            "interactions.create",
        )

    def test_173_gemini_render_requires_live_assignment(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        offline_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="SYNTHETIC_OFFLINE",
        )
        offline_target = model_target_policy(
            bound_task,
            offline_assignment,
        )
        offline_cap = capability_policy(
            bound_task,
            offline_assignment,
            offline_target,
        )
        with self.assertRaises(ResearchContractError):
            render_gemini_interactions_v1(
                bound_task,
                offline_assignment,
                offline_target,
                offline_cap,
                prompt,
                schema,
            )

    def test_174_gemini_render_is_stateless_nonstreaming_background_false(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertIs(body["store"], False)
        self.assertIs(body["stream"], False)
        self.assertIs(body["background"], False)

    def test_175_gemini_render_contains_no_tools(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertNotIn("tools", body)

    def test_176_gemini_render_requires_json_response_format(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        response_format = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]["response_format"]
        self.assertEqual(
            response_format["mime_type"],
            "application/json",
        )
        self.assertEqual(
            response_format["schema"],
            schema,
        )

    def test_177_gemini_response_schema_must_match_prompt_digest(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        changed = copy.deepcopy(schema)
        changed["properties"]["extra"] = {
            "type": "string"
        }
        with self.assertRaises(ResearchContractError):
            render_gemini_interactions_v1(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                changed,
            )

    def test_178_gemini_render_uses_exact_assignment_model(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertEqual(
            rendered["body"]["model"],
            bound_assignment["target_model"],
        )

    def test_179_gemini_render_input_is_exact_canonical_prompt(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertEqual(
            rendered["body"]["input"],
            json.dumps(
                prompt,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )

    def test_180_gemini_render_contains_no_credential_material(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertIs(
            rendered["credential_material_included"],
            False,
        )
        rendered_text = json.dumps(rendered)
        self.assertNotIn("api_key", rendered_text.lower())
        self.assertNotIn("authorization", rendered_text.lower())

    def test_181_gemini_render_digest_changes_with_prompt_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        bound_task["requested_roles"] = [
            "architecture_challenge",
            "security_challenge",
        ]
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        first = gemini_render_sha256(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        changed_task = copy.deepcopy(bound_task)
        changed_task["objective"] = "Changed objective."
        changed_prompt = build_provider_neutral_prompt(
            changed_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        changed_assignment = assignment(
            changed_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        changed_target = model_target_policy(
            changed_task,
            changed_assignment,
        )
        changed_cap = capability_policy(
            changed_task,
            changed_assignment,
            changed_target,
        )
        second = gemini_render_sha256(
            changed_task,
            changed_assignment,
            changed_target,
            changed_cap,
            changed_prompt,
            schema,
        )
        self.assertNotEqual(first, second)

    def test_182_parse_completed_gemini_response(self):
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        self.assertEqual(
            observation["normalized_state"],
            "COMPLETED",
        )
        self.assertEqual(
            observation["provider_response_id"],
            "gemini-response-001",
        )
        self.assertEqual(
            observation["observed_model_id"],
            "model-stable-001",
        )
        self.assertEqual(observation["input_tokens"], 10)
        self.assertEqual(observation["output_tokens"], 20)

    def test_183_parse_completed_empty_gemini_response(self):
        observation = parse_gemini_interactions_v1_response(
            gemini_response(text="")
        )
        self.assertEqual(
            observation["normalized_state"],
            "PROVIDER_EMPTY",
        )

    def test_184_parse_incomplete_gemini_response(self):
        observation = parse_gemini_interactions_v1_response(
            gemini_response(status="incomplete")
        )
        self.assertEqual(
            observation["normalized_state"],
            "PROVIDER_TRUNCATED",
        )

    def test_185_parse_failed_or_cancelled_gemini_response(self):
        for status in ("failed", "cancelled"):
            observation = (
                parse_gemini_interactions_v1_response(
                    gemini_response(status=status)
                )
            )
            self.assertEqual(
                observation["normalized_state"],
                "TRANSPORT_FAILURE",
            )

    def test_186_parse_rejects_nonterminal_gemini_status(self):
        for status in ("in_progress", "requires_action"):
            with self.assertRaises(ResearchContractError):
                parse_gemini_interactions_v1_response(
                    gemini_response(status=status)
                )

    def test_187_parse_requires_response_id_and_model(self):
        for key in ("id", "model"):
            response = gemini_response()
            response.pop(key)
            with self.assertRaises(ResearchContractError):
                parse_gemini_interactions_v1_response(
                    response
                )

    def test_188_parse_rejects_negative_usage(self):
        response = gemini_response()
        response["usage"]["total_output_tokens"] = -1
        with self.assertRaises(ResearchContractError):
            parse_gemini_interactions_v1_response(response)

    def test_189_parse_preserves_observed_model_drift_for_receipt_check(self):
        observation = parse_gemini_interactions_v1_response(
            gemini_response(model="model-other")
        )
        self.assertEqual(
            observation["observed_model_id"],
            "model-other",
        )

    def test_190_parse_digests_exact_provider_response_and_usage(self):
        response = gemini_response()
        observation = parse_gemini_interactions_v1_response(
            response
        )
        self.assertEqual(
            observation["provider_response_sha256"],
            sha256_json(response),
        )
        self.assertEqual(
            observation["usage_metadata_sha256"],
            sha256_json(response["usage"]),
        )


    def test_191_valid_claude_messages_render(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertEqual(
            rendered["sdk_surface"],
            "messages.create",
        )
        self.assertIs(rendered["stateless"], True)

    def test_192_claude_render_requires_live_assignment(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        offline_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="SYNTHETIC_OFFLINE",
        )
        offline_target = model_target_policy(
            bound_task,
            offline_assignment,
        )
        offline_cap = capability_policy(
            bound_task,
            offline_assignment,
            offline_target,
        )
        with self.assertRaises(ResearchContractError):
            render_claude_messages_request(
                bound_task,
                offline_assignment,
                offline_target,
                offline_cap,
                prompt,
                schema,
            )

    def test_193_claude_render_is_nonstreaming_and_has_no_tools(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertIs(body["stream"], False)
        self.assertNotIn("tools", body)
        self.assertNotIn("mcp_servers", body)

    def test_194_claude_render_uses_json_schema_output_config(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertEqual(
            body["output_config"]["format"]["type"],
            "json_schema",
        )
        self.assertEqual(
            body["output_config"]["format"]["schema"],
            schema,
        )

    def test_195_claude_response_schema_must_match_prompt_digest(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        changed = copy.deepcopy(schema)
        changed["properties"]["extra"] = {
            "type": "string"
        }
        with self.assertRaises(ResearchContractError):
            render_claude_messages_request(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                changed,
            )

    def test_196_claude_render_uses_exact_assignment_model(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertEqual(
            body["model"],
            bound_assignment["target_model"],
        )

    def test_197_claude_render_message_is_exact_canonical_prompt(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        body = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )["body"]
        self.assertEqual(
            body["messages"],
            [
                {
                    "role": "user",
                    "content": json.dumps(
                        prompt,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                }
            ],
        )

    def test_198_claude_render_contains_no_credential_material(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        rendered = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        self.assertIs(
            rendered["credential_material_included"],
            False,
        )
        rendered_text = json.dumps(rendered)
        self.assertNotIn("api_key", rendered_text.lower())
        self.assertNotIn("authorization", rendered_text.lower())

    def test_199_claude_render_digest_changes_with_prompt_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        first = claude_render_sha256(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        changed_task = copy.deepcopy(bound_task)
        changed_task["objective"] = "Changed objective."
        changed_prompt = build_provider_neutral_prompt(
            changed_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        changed_assignment = assignment(
            changed_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        changed_target = model_target_policy(
            changed_task,
            changed_assignment,
        )
        changed_cap = capability_policy(
            changed_task,
            changed_assignment,
            changed_target,
        )
        second = claude_render_sha256(
            changed_task,
            changed_assignment,
            changed_target,
            changed_cap,
            changed_prompt,
            schema,
        )
        self.assertNotEqual(first, second)

    def test_200_parse_completed_claude_response(self):
        observation = parse_claude_messages_response(
            claude_response()
        )
        self.assertEqual(
            observation["normalized_state"],
            "COMPLETED",
        )
        self.assertEqual(
            observation["provider_response_id"],
            "claude-response-001",
        )
        self.assertEqual(observation["input_tokens"], 10)
        self.assertEqual(observation["output_tokens"], 20)

    def test_201_parse_empty_claude_end_turn(self):
        observation = parse_claude_messages_response(
            claude_response(text="")
        )
        self.assertEqual(
            observation["normalized_state"],
            "PROVIDER_EMPTY",
        )

    def test_202_parse_claude_refusal_stop_reason(self):
        observation = parse_claude_messages_response(
            claude_response(stop_reason="refusal")
        )
        self.assertEqual(
            observation["normalized_state"],
            "PROVIDER_REFUSED",
        )

    def test_203_parse_claude_refusal_stop_details(self):
        response = claude_response()
        response["stop_details"] = {
            "type": "refusal",
            "category": "policy",
        }
        observation = parse_claude_messages_response(
            response
        )
        self.assertEqual(
            observation["normalized_state"],
            "PROVIDER_REFUSED",
        )

    def test_204_parse_claude_truncation_reasons(self):
        for reason in (
            "max_tokens",
            "model_context_window_exceeded",
            "stop_sequence",
        ):
            observation = parse_claude_messages_response(
                claude_response(stop_reason=reason)
            )
            self.assertEqual(
                observation["normalized_state"],
                "PROVIDER_TRUNCATED",
            )

    def test_205_parse_claude_tool_or_pause_stop_fails_closed(self):
        for reason in ("tool_use", "pause_turn"):
            with self.assertRaises(RuntimeError):
                parse_claude_messages_response(
                    claude_response(stop_reason=reason)
                )

    def test_206_parse_claude_rejects_unexpected_server_tool_use(self):
        response = claude_response()
        response["usage"]["server_tool_use"] = {
            "web_search_requests": 1,
        }
        with self.assertRaises(ResearchContractError):
            parse_claude_messages_response(response)

    def test_207_parse_claude_allows_zero_server_tool_use_metadata(self):
        response = claude_response()
        response["usage"]["server_tool_use"] = {
            "web_search_requests": 0,
            "web_fetch_requests": 0,
        }
        observation = parse_claude_messages_response(
            response
        )
        self.assertEqual(
            observation["normalized_state"],
            "COMPLETED",
        )

    def test_208_parse_claude_requires_id_model_and_nonnegative_usage(self):
        for key in ("id", "model"):
            response = claude_response()
            response.pop(key)
            with self.assertRaises(ResearchContractError):
                parse_claude_messages_response(response)

        response = claude_response()
        response["usage"]["output_tokens"] = -1
        with self.assertRaises(ResearchContractError):
            parse_claude_messages_response(response)

    def test_209_parse_claude_preserves_model_and_exact_digests(self):
        response = claude_response(
            model="model-other"
        )
        observation = parse_claude_messages_response(
            response
        )
        self.assertEqual(
            observation["observed_model_id"],
            "model-other",
        )
        self.assertEqual(
            observation["provider_response_sha256"],
            sha256_json(response),
        )
        self.assertEqual(
            observation["usage_metadata_sha256"],
            sha256_json(response["usage"]),
        )


    def test_210_valid_gemini_transport_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        binding = validate_transport_binding(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            schema,
            render,
        )
        self.assertEqual(
            binding["provider"],
            "GOOGLE_GEMINI",
        )
        self.assertEqual(
            binding["outbound_payload_sha256"],
            sha256_json(render["body"]),
        )

    def test_211_valid_claude_transport_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        binding = validate_transport_binding(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            schema,
            render,
        )
        self.assertEqual(
            binding["provider"],
            "ANTHROPIC_CLAUDE",
        )

    def test_212_transport_binding_rejects_payload_digest_mismatch(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        envelope["outbound_payload_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_transport_binding(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                schema,
                render,
            )

    def test_213_transport_binding_rejects_tampered_render(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        render["body"]["max_tokens"] = 999
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        with self.assertRaises(ResearchContractError):
            validate_transport_binding(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                schema,
                render,
            )

    def test_214_transport_binding_rejects_unknown_provider(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        render["provider"] = "UNKNOWN_PROVIDER"
        with self.assertRaises(ResearchContractError):
            validate_transport_binding(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                schema,
                render,
            )

    def test_215_cross_provider_canonical_prompt_bytes_match(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        gemini_assignment = assignment(
            bound_task,
            assignment_id="cross-gemini",
            provider="google-gemini",
            model="gemini-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        claude_assignment = assignment(
            bound_task,
            assignment_id="cross-claude",
            provider="anthropic-claude",
            model="claude-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        gemini_target = model_target_policy(
            bound_task,
            gemini_assignment,
        )
        claude_target = model_target_policy(
            bound_task,
            claude_assignment,
        )
        gemini_cap = capability_policy(
            bound_task,
            gemini_assignment,
            gemini_target,
        )
        claude_cap = capability_policy(
            bound_task,
            claude_assignment,
            claude_target,
        )
        gemini_render = render_gemini_interactions_v1(
            bound_task,
            gemini_assignment,
            gemini_target,
            gemini_cap,
            prompt,
            schema,
        )
        claude_render = render_claude_messages_request(
            bound_task,
            claude_assignment,
            claude_target,
            claude_cap,
            prompt,
            schema,
        )
        self.assertEqual(
            gemini_render["body"]["input"],
            claude_render["body"]["messages"][0]["content"],
        )

    def test_216_cross_provider_response_schema_matches_exactly(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        gemini_assignment = assignment(
            bound_task,
            assignment_id="schema-gemini",
            provider="google-gemini",
            model="gemini-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        claude_assignment = assignment(
            bound_task,
            assignment_id="schema-claude",
            provider="anthropic-claude",
            model="claude-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        gt = model_target_policy(bound_task, gemini_assignment)
        ct = model_target_policy(bound_task, claude_assignment)
        gc = capability_policy(bound_task, gemini_assignment, gt)
        cc = capability_policy(bound_task, claude_assignment, ct)
        gr = render_gemini_interactions_v1(
            bound_task, gemini_assignment, gt, gc, prompt, schema
        )
        cr = render_claude_messages_request(
            bound_task, claude_assignment, ct, cc, prompt, schema
        )
        self.assertEqual(
            gr["body"]["response_format"]["schema"],
            cr["body"]["output_config"]["format"]["schema"],
        )

    def test_217_cross_provider_both_are_nonstreaming_tool_free(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        ga = assignment(
            bound_task,
            assignment_id="policy-gemini",
            provider="google-gemini",
            model="gemini-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        ca = assignment(
            bound_task,
            assignment_id="policy-claude",
            provider="anthropic-claude",
            model="claude-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        gt = model_target_policy(bound_task, ga)
        ct = model_target_policy(bound_task, ca)
        gc = capability_policy(bound_task, ga, gt)
        cc = capability_policy(bound_task, ca, ct)
        gr = render_gemini_interactions_v1(
            bound_task, ga, gt, gc, prompt, schema
        )
        cr = render_claude_messages_request(
            bound_task, ca, ct, cc, prompt, schema
        )
        self.assertIs(gr["body"]["stream"], False)
        self.assertIs(cr["body"]["stream"], False)
        self.assertNotIn("tools", gr["body"])
        self.assertNotIn("tools", cr["body"])

    def test_218_provider_render_sha_differs_while_prompt_is_same(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        ga = assignment(
            bound_task,
            assignment_id="digest-gemini",
            provider="google-gemini",
            model="gemini-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        ca = assignment(
            bound_task,
            assignment_id="digest-claude",
            provider="anthropic-claude",
            model="claude-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        gt = model_target_policy(bound_task, ga)
        ct = model_target_policy(bound_task, ca)
        gc = capability_policy(bound_task, ga, gt)
        cc = capability_policy(bound_task, ca, ct)
        gr = render_gemini_interactions_v1(
            bound_task, ga, gt, gc, prompt, schema
        )
        cr = render_claude_messages_request(
            bound_task, ca, ct, cc, prompt, schema
        )
        self.assertNotEqual(
            sha256_json(gr),
            sha256_json(cr),
        )
        self.assertEqual(
            gr["body"]["input"],
            cr["body"]["messages"][0]["content"],
        )

    def test_219_schema_change_invalidates_stale_transport_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        changed_schema = copy.deepcopy(schema)
        changed_schema["properties"]["extra"] = {
            "type": "string"
        }
        with self.assertRaises(ResearchContractError):
            validate_transport_binding(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                envelope,
                changed_schema,
                render,
            )

    def test_220_transport_binding_digest_changes_with_exact_envelope(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        first = transport_binding_sha256(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            schema,
            render,
        )
        changed_render = copy.deepcopy(render)
        changed_render["body"]["messages"][0]["content"] = (
            changed_render["body"]["messages"][0]["content"] + " "
        )
        changed_envelope = copy.deepcopy(envelope)
        changed_envelope["outbound_payload_sha256"] = sha256_json(
            changed_render["body"]
        )
        with self.assertRaises(ResearchContractError):
            transport_binding_sha256(
                bound_task,
                bound_assignment,
                target_policy,
                cap_policy,
                prompt,
                changed_envelope,
                schema,
                changed_render,
            )
        self.assertIsInstance(first, str)
        self.assertEqual(len(first), 64)


    def test_221_valid_gemini_observation_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        binding = validate_provider_observation_binding(
            provider="GOOGLE_GEMINI",
            observation=observation,
            task=bound_task,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            termination_record=record,
            result=value,
            receipt=receipt,
        )
        self.assertEqual(
            binding["provider"],
            "GOOGLE_GEMINI",
        )

    def test_222_valid_claude_observation_binding(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_claude_messages_response(
            claude_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="claude-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        binding = validate_provider_observation_binding(
            provider="ANTHROPIC_CLAUDE",
            observation=observation,
            task=bound_task,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            termination_record=record,
            result=value,
            receipt=receipt,
        )
        self.assertEqual(
            binding["provider"],
            "ANTHROPIC_CLAUDE",
        )

    def test_223_observation_normalized_state_must_match_termination(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["normalized_state"] = "PROVIDER_EMPTY"
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="GOOGLE_GEMINI",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_224_observation_response_id_must_match_records(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_claude_messages_response(
            claude_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="claude-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["provider_response_id"] = "other-response"
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="ANTHROPIC_CLAUDE",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_225_observation_usage_counts_must_match_termination(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["input_tokens"] += 1
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="GOOGLE_GEMINI",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_226_observation_usage_digest_must_match_termination(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_claude_messages_response(
            claude_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="claude-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["usage_metadata_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="ANTHROPIC_CLAUDE",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_227_observation_response_digest_must_match_receipt(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["provider_response_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="GOOGLE_GEMINI",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_228_observation_model_must_match_receipt(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_claude_messages_response(
            claude_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="claude-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["observed_model_id"] = "model-other"
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="ANTHROPIC_CLAUDE",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_229_observation_provider_schema_must_match(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        with self.assertRaises(ResearchContractError):
            validate_provider_observation_binding(
                provider="ANTHROPIC_CLAUDE",
                observation=observation,
                task=bound_task,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                termination_record=record,
                result=value,
                receipt=receipt,
            )

    def test_230_live_attested_gemini_chain_is_exactly_bound(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        digest = provider_observation_binding_sha256(
            provider="GOOGLE_GEMINI",
            observation=observation,
            task=bound_task,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            termination_record=record,
            result=value,
            receipt=receipt,
        )
        self.assertEqual(len(digest), 64)

    def test_231_live_attested_claude_chain_is_exactly_bound(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_claude_messages_response(
            claude_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="claude-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        digest = provider_observation_binding_sha256(
            provider="ANTHROPIC_CLAUDE",
            observation=observation,
            task=bound_task,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            termination_record=record,
            result=value,
            receipt=receipt,
        )
        self.assertEqual(len(digest), 64)

    def test_232_unverified_receipt_must_preserve_observed_model_exactly(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        observation = parse_gemini_interactions_v1_response(
            gemini_response()
        )
        record = termination_record(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        record["provider_response_id"] = observation[
            "provider_response_id"
        ]
        record["normalized_state"] = observation[
            "normalized_state"
        ]
        record["input_tokens"] = observation["input_tokens"]
        record["output_tokens"] = observation["output_tokens"]
        record["usage_metadata_sha256"] = observation[
            "usage_metadata_sha256"
        ]
        value = result_v2(
            bound_task,
            bound_assignment,
            submission_id="gemini-observation-result",
        )
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            observed_model_id=observation["observed_model_id"],
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        receipt = execution_receipt(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            record,
            value,
            attestation_state="LIVE_PROVIDER_ID_UNVERIFIED",
            observed_model_id="model-other",
        )
        receipt["provider_response_sha256"] = observation[
            "provider_response_sha256"
        ]
        observation["observed_model_id"] = "model-other"
        binding = validate_provider_observation_binding(
            provider="GOOGLE_GEMINI",
            observation=observation,
            task=bound_task,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            termination_record=record,
            result=value,
            receipt=receipt,
        )
        self.assertEqual(
            binding["observed_model_id"],
            "model-other",
        )


    def test_233_valid_gemini_live_execution_prep(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        self.assertEqual(
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            ),
            prep,
        )

    def test_234_valid_claude_live_execution_prep(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        self.assertEqual(
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            ),
            prep,
        )

    def test_235_execution_prep_rejects_wrong_host(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["allowed_host"] = "example.com"
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_236_execution_prep_rejects_wrong_operation(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["allowed_operation"] = "OTHER"
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_237_execution_prep_forbids_credential_material_in_repo(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["credential_material_in_repository"] = True
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_238_execution_prep_requires_single_attempt(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["max_attempts"] = 2
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_239_execution_prep_token_ceilings_are_bounded(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        for key, value in (
            ("max_input_tokens", 32769),
            ("max_output_tokens", 4097),
        ):
            broken = copy.deepcopy(prep)
            broken[key] = value
            with self.assertRaises(ResearchContractError):
                validate_live_execution_prep(
                    task=bound_task,
                    assignments=assignments,
                    fanout_plan=plan,
                    assignment=bound_assignment,
                    model_target_policy=target_policy,
                    capability_policy=cap_policy,
                    prompt=prompt,
                    request_envelope=envelope,
                    smoke_profile=smoke,
                    response_schema=schema,
                    render=render,
                    prep=broken,
                )

    def test_240_execution_prep_cost_ceiling_is_under_one_dollar(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["proposed_max_cost_usd_micros"] = 1_000_001
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_241_execution_prep_requires_separate_authorities(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        for key in (
            "provider_call_authority_required",
            "credential_authority_required",
            "spend_authority_required",
        ):
            broken = copy.deepcopy(prep)
            broken[key] = False
            with self.assertRaises(ResearchContractError):
                validate_live_execution_prep(
                    task=bound_task,
                    assignments=assignments,
                    fanout_plan=plan,
                    assignment=bound_assignment,
                    model_target_policy=target_policy,
                    capability_policy=cap_policy,
                    prompt=prompt,
                    request_envelope=envelope,
                    smoke_profile=smoke,
                    response_schema=schema,
                    render=render,
                    prep=broken,
                )

    def test_242_execution_prep_network_scope_is_provider_only(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["network_scope"] = "PUBLIC_INTERNET"
        with self.assertRaises(ResearchContractError):
            validate_live_execution_prep(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                prep=prep,
            )

    def test_243_execution_prep_forbids_runtime_live_effect_and_protected_data(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        for key in (
            "runtime_activation",
            "live_business_effect",
            "protected_data",
        ):
            broken = copy.deepcopy(prep)
            broken[key] = True
            with self.assertRaises(ResearchContractError):
                validate_live_execution_prep(
                    task=bound_task,
                    assignments=assignments,
                    fanout_plan=plan,
                    assignment=bound_assignment,
                    model_target_policy=target_policy,
                    capability_policy=cap_policy,
                    prompt=prompt,
                    request_envelope=envelope,
                    smoke_profile=smoke,
                    response_schema=schema,
                    render=render,
                    prep=broken,
                )

    def test_244_execution_prep_binds_exact_smoke_and_transport(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        for key in (
            "smoke_profile_sha256",
            "transport_binding_sha256",
        ):
            broken = copy.deepcopy(prep)
            broken[key] = "0" * 64
            with self.assertRaises(ResearchContractError):
                validate_live_execution_prep(
                    task=bound_task,
                    assignments=assignments,
                    fanout_plan=plan,
                    assignment=bound_assignment,
                    model_target_policy=target_policy,
                    capability_policy=cap_policy,
                    prompt=prompt,
                    request_envelope=envelope,
                    smoke_profile=smoke,
                    response_schema=schema,
                    render=render,
                    prep=broken,
                )

    def test_245_execution_prep_digest_is_exact(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        digest = live_execution_prep_sha256(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            prep=prep,
        )
        self.assertEqual(len(digest), 64)


    def test_246_execution_prep_declares_hosts_without_network_client_code(self):
        prep_source = (
            Path(__file__).with_name("execution_prep.py")
            .read_text()
            .lower()
        )
        self.assertIn(
            "generativelanguage.googleapis.com",
            prep_source,
        )
        self.assertIn("api.anthropic.com", prep_source)
        for marker in (
            "requests.",
            "httpx.",
            "urllib.request",
            "aiohttp.",
            "socket.",
            "http.client",
            "urlopen(",
            "client.interactions.create(",
            "client.messages.create(",
        ):
            self.assertNotIn(marker, prep_source)

    def test_247_provider_adapters_remain_renderer_parser_only(self):
        root = Path(__file__).parent
        source = (
            (root / "gemini_adapter.py").read_text()
            + (root / "claude_adapter.py").read_text()
            + (root / "transport_binding.py").read_text()
            + (root / "observation_binding.py").read_text()
        ).lower()
        self.assertNotIn(
            "generativelanguage.googleapis.com",
            source,
        )
        self.assertNotIn("api.anthropic.com", source)
        for marker in (
            "requests.",
            "httpx.",
            "urllib.request",
            "aiohttp.",
            "socket.",
            "http.client",
            "urlopen(",
            "client.interactions.create(",
            "client.messages.create(",
        ):
            self.assertNotIn(marker, source)


    def test_248_build_gemini_live_readiness_report(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertEqual(
            report["provider"],
            "GOOGLE_GEMINI",
        )
        self.assertTrue(report["repository_contract_ready"])

    def test_249_build_claude_live_readiness_report(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertEqual(
            report["provider"],
            "ANTHROPIC_CLAUDE",
        )

    def test_250_readiness_state_is_separate_authority_only(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertEqual(
            report["readiness_state"],
            "READY_FOR_SEPARATE_PROVIDER_AUTHORITY",
        )

    def test_251_readiness_never_grants_provider_credential_or_spend_authority(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
        ):
            self.assertIs(report[key], False)

    def test_252_readiness_never_claims_live_execution(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertIs(
            report["live_execution_performed"],
            False,
        )

    def test_253_readiness_runtime_remains_off(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertEqual(report["runtime"], "OFF")

    def test_254_readiness_rejects_tampered_execution_prep(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        prep["allowed_host"] = "example.com"
        with self.assertRaises(ResearchContractError):
            build_live_provider_readiness_report(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=render,
                execution_prep=prep,
            )

    def test_255_readiness_report_validation_fails_if_authority_is_fabricated(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        report = build_live_provider_readiness_report(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        report["provider_call_authorized"] = True
        with self.assertRaises(ResearchContractError):
            validate_live_provider_readiness_report(report)

    def test_256_readiness_digest_is_deterministic(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_gemini_interactions_v1(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        kwargs = dict(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        self.assertEqual(
            live_provider_readiness_sha256(**kwargs),
            live_provider_readiness_sha256(**kwargs),
        )

    def test_257_readiness_digest_changes_if_exact_transport_changes(self):
        bound_task = task_v2()
        schema = response_schema()
        prompt = build_provider_neutral_prompt(
            bound_task,
            "architecture_challenge",
            sha256_json(schema),
        )
        bound_assignment = assignment(
            bound_task,
            provider="anthropic-claude",
            model="model-stable-001",
            execution_mode="LIVE_ADVISORY",
        )
        assignments = [bound_assignment]
        plan = fanout_plan(bound_task, assignments)
        target_policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        cap_policy = capability_policy(
            bound_task,
            bound_assignment,
            target_policy,
        )
        render = render_claude_messages_request(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            schema,
        )
        envelope = request_envelope(
            bound_task,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
        )
        envelope["outbound_payload_sha256"] = sha256_json(
            render["body"]
        )
        smoke = live_smoke_profile(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
        )
        prep = live_execution_prep(
            bound_task,
            assignments,
            plan,
            bound_assignment,
            target_policy,
            cap_policy,
            prompt,
            envelope,
            smoke,
            schema,
            render,
        )
        original = live_provider_readiness_sha256(
            task=bound_task,
            assignments=assignments,
            fanout_plan=plan,
            assignment=bound_assignment,
            model_target_policy=target_policy,
            capability_policy=cap_policy,
            prompt=prompt,
            request_envelope=envelope,
            smoke_profile=smoke,
            response_schema=schema,
            render=render,
            execution_prep=prep,
        )
        changed_render = copy.deepcopy(render)
        changed_render["body"]["max_tokens"] = 2048
        with self.assertRaises(ResearchContractError):
            live_provider_readiness_sha256(
                task=bound_task,
                assignments=assignments,
                fanout_plan=plan,
                assignment=bound_assignment,
                model_target_policy=target_policy,
                capability_policy=cap_policy,
                prompt=prompt,
                request_envelope=envelope,
                smoke_profile=smoke,
                response_schema=schema,
                render=changed_render,
                execution_prep=prep,
            )
        self.assertEqual(len(original), 64)


    def test_258_provider_catalog_snapshot_validates(self):
        snapshot = json.loads(
            (
                Path(__file__).with_name(
                    "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
                )
            ).read_text()
        )
        self.assertEqual(
            validate_provider_catalog(snapshot),
            snapshot,
        )

    def test_259_provider_catalog_has_exact_two_providers(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        self.assertEqual(
            {
                item["provider"]
                for item in snapshot["entries"]
            },
            {"GOOGLE_GEMINI", "ANTHROPIC_CLAUDE"},
        )

    def test_260_gemini_catalog_candidate_is_current_stable_id(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        entry = catalog_entry(snapshot, "GOOGLE_GEMINI")
        self.assertEqual(entry["model_id"], "gemini-3.8-flash")
        self.assertEqual(
            entry["classification"],
            "PINNED_OR_STABLE",
        )
        self.assertTrue(entry["structured_json"])

    def test_261_claude_catalog_candidate_is_pinned_haiku_id(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        entry = catalog_entry(snapshot, "ANTHROPIC_CLAUDE")
        self.assertEqual(
            entry["model_id"],
            "claude-haiku-4-5-20251001",
        )
        self.assertEqual(
            entry["classification"],
            "PINNED_OR_STABLE",
        )

    def test_262_catalog_evidence_refs_are_official_domains(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        validate_provider_catalog(snapshot)
        for entry in snapshot["entries"]:
            for ref in entry["official_evidence_refs"]:
                if entry["provider"] == "GOOGLE_GEMINI":
                    self.assertIn("ai.google.dev/", ref)
                else:
                    self.assertIn("platform.claude.com/", ref)

    def test_263_gemini_smoke_max_cost_estimate(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        self.assertEqual(
            estimate_smoke_cost_usd_micros(
                snapshot,
                "GOOGLE_GEMINI",
                32768,
                4096,
            ),
            39936,
        )

    def test_264_claude_smoke_max_cost_estimate(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        self.assertEqual(
            estimate_smoke_cost_usd_micros(
                snapshot,
                "ANTHROPIC_CLAUDE",
                32768,
                4096,
            ),
            53248,
        )

    def test_265_both_smoke_candidates_are_under_one_dollar_ceiling(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        for provider in (
            "GOOGLE_GEMINI",
            "ANTHROPIC_CLAUDE",
        ):
            candidate = validate_first_smoke_candidate(
                snapshot,
                provider,
            )
            self.assertLessEqual(
                candidate["estimated_max_cost_usd_micros"],
                1_000_000,
            )
            self.assertIs(candidate["spend_authority"], False)

    def test_266_unknown_catalog_provider_rejected(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(RuntimeError):
            catalog_entry(snapshot, "OTHER_PROVIDER")

    def test_267_catalog_tampered_price_changes_entry_digest(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        first = catalog_entry_sha256(
            snapshot,
            "GOOGLE_GEMINI",
        )
        changed = copy.deepcopy(snapshot)
        changed["entries"][0][
            "input_usd_micros_per_million_tokens"
        ] += 1
        second = catalog_entry_sha256(
            changed,
            "GOOGLE_GEMINI",
        )
        self.assertNotEqual(first, second)

    def test_268_catalog_candidate_evidence_sha_can_bind_model_target_policy(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        bound_task = task_v2()
        entry = catalog_entry(snapshot, "GOOGLE_GEMINI")
        bound_assignment = assignment(
            bound_task,
            provider="google-gemini",
            model=entry["model_id"],
            execution_mode="LIVE_ADVISORY",
        )
        policy = model_target_policy(
            bound_task,
            bound_assignment,
        )
        policy["classification_evidence_ref"] = (
            "provider-model-catalog-20260908:GOOGLE_GEMINI"
        )
        policy["classification_evidence_sha256"] = (
            catalog_entry_sha256(snapshot, "GOOGLE_GEMINI")
        )
        self.assertEqual(
            validate_model_target_policy(
                bound_task,
                bound_assignment,
                policy,
            ),
            policy,
        )

    def test_269_catalog_smoke_cost_ceiling_fails_closed(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            validate_first_smoke_candidate(
                snapshot,
                "ANTHROPIC_CLAUDE",
                max_cost_usd_micros=10,
            )

    def test_270_catalog_nonauthority_all_false(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        self.assertTrue(
            all(
                value is False
                for value in snapshot["nonauthority"].values()
            )
        )

    def test_271_catalog_snapshot_digest_is_deterministic(self):
        path = Path(__file__).with_name(
            "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
        )
        first = json.loads(path.read_text())
        second = json.loads(path.read_text())
        self.assertEqual(
            sha256_json(first),
            sha256_json(second),
        )


    def test_272_valid_gemini_first_provider_pilot_dry_run(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertEqual(
            validate_first_provider_pilot_dry_run(
                snapshot,
                plan,
            ),
            plan,
        )
        self.assertEqual(
            plan["model_id"],
            "gemini-3.8-flash",
        )

    def test_273_valid_claude_first_provider_pilot_dry_run(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertEqual(
            validate_first_provider_pilot_dry_run(
                snapshot,
                plan,
            ),
            plan,
        )
        self.assertEqual(
            plan["model_id"],
            "claude-haiku-4-5-20251001",
        )

    def test_274_pilot_requires_exact_prelive_head_sha(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            build_first_provider_pilot_dry_run(
                snapshot,
                "GOOGLE_GEMINI",
                prelive_candidate_head="not-a-sha",
                prelive_candidate_seal_blob=
                    "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            )

    def test_275_pilot_requires_exact_prelive_seal_blob_sha(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            build_first_provider_pilot_dry_run(
                snapshot,
                "GOOGLE_GEMINI",
                prelive_candidate_head=
                    "d354bfa274b1f6a4ba116fbfa27356ce01979677",
                prelive_candidate_seal_blob="not-a-sha",
            )

    def test_276_pilot_model_must_match_catalog(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        plan["model_id"] = "model-other"
        with self.assertRaises(ResearchContractError):
            validate_first_provider_pilot_dry_run(
                snapshot,
                plan,
            )

    def test_277_pilot_binds_exact_catalog_snapshot_digest(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        plan["catalog_snapshot_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_first_provider_pilot_dry_run(
                snapshot,
                plan,
            )

    def test_278_pilot_cost_estimate_is_exact_and_bounded(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertEqual(
            plan["estimated_max_cost_usd_micros"],
            53248,
        )
        self.assertLessEqual(
            plan["estimated_max_cost_usd_micros"],
            1_000_000,
        )

    def test_279_pilot_is_exactly_one_provider_call_attempt(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertEqual(
            plan["planned_provider_count"],
            1,
        )
        self.assertEqual(plan["planned_call_count"], 1)
        self.assertEqual(plan["max_attempts"], 1)

    def test_280_pilot_is_synthetic_json_only(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertEqual(
            plan["data_ceiling"],
            "SYNTHETIC_ONLY",
        )
        self.assertEqual(
            plan["structured_output"],
            "JSON_ONLY",
        )

    def test_281_pilot_requires_authority_without_granting_it(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        for key in (
            "provider_call_authority_required",
            "credential_authority_required",
            "spend_authority_required",
        ):
            self.assertIs(plan[key], True)

        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
        ):
            self.assertIs(plan[key], False)

    def test_282_pilot_never_claims_execution_runtime_or_adoption(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertIs(
            plan["network_execution_in_repository"],
            False,
        )
        self.assertIs(
            plan["credential_material_in_repository"],
            False,
        )
        self.assertIs(
            plan["live_execution_performed"],
            False,
        )
        self.assertIs(plan["adoption_authority"], False)
        self.assertEqual(plan["runtime"], "OFF")

    def test_283_pilot_phase_fails_closed(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        plan["phase"] = "PHASE_C_SECOND_PROVIDER"
        with self.assertRaises(ResearchContractError):
            validate_first_provider_pilot_dry_run(
                snapshot,
                plan,
            )

    def test_284_pilot_candidate_matrix_contains_both_providers(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        matrix = build_pilot_candidate_matrix(snapshot)
        self.assertEqual(
            {row["provider"] for row in matrix},
            {"GOOGLE_GEMINI", "ANTHROPIC_CLAUDE"},
        )

    def test_285_pilot_candidate_matrix_grants_no_selection_or_spend(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        matrix = build_pilot_candidate_matrix(snapshot)
        for row in matrix:
            self.assertIs(row["selection_authority"], False)
            self.assertIs(row["selected"], False)
            self.assertIs(row["spend_authority"], False)

    def test_286_pilot_digest_is_deterministic_and_provider_specific(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        first = first_provider_pilot_dry_run_sha256(
            snapshot,
            plan,
        )
        second = first_provider_pilot_dry_run_sha256(
            snapshot,
            copy.deepcopy(plan),
        )
        self.assertEqual(first, second)

        claude = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        self.assertNotEqual(
            first,
            first_provider_pilot_dry_run_sha256(
                snapshot,
                claude,
            ),
        )


    def test_287_valid_same_day_catalog_freshness_receipt(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        self.assertEqual(
            validate_catalog_freshness_receipt(snapshot, freshness),
            freshness,
        )
        self.assertLessEqual(freshness["age_seconds"], 86400)

    def test_288_catalog_snapshot_older_than_24h_is_rejected(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            build_catalog_freshness_receipt(
                snapshot,
                checked_at="2026-09-09T11:05:01Z",
            )

    def test_289_catalog_freshness_check_cannot_predate_snapshot(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            build_catalog_freshness_receipt(
                snapshot,
                checked_at="2026-09-08T11:04:59Z",
            )

    def test_290_catalog_freshness_requires_strict_utc(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        with self.assertRaises(ResearchContractError):
            build_catalog_freshness_receipt(
                snapshot,
                checked_at="2026-09-08T20:30:00+09:00",
            )

    def test_291_expired_pricing_window_is_rejected(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        changed = copy.deepcopy(snapshot)
        changed["entries"][0]["pricing_valid_through"] = "2026-09-07"
        with self.assertRaises(ResearchContractError):
            build_catalog_freshness_receipt(
                changed,
                checked_at="2026-09-08T11:30:00Z",
            )

    def test_292_catalog_mutation_invalidates_freshness_receipt(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        changed = copy.deepcopy(snapshot)
        changed["entries"][0][
            "input_usd_micros_per_million_tokens"
        ] += 1
        with self.assertRaises(ResearchContractError):
            validate_catalog_freshness_receipt(changed, freshness)

    def test_293_catalog_freshness_grants_no_authority(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "live_execution_performed",
        ):
            self.assertIs(freshness[key], False)

    def test_294_catalog_freshness_runtime_remains_off(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        self.assertEqual(freshness["runtime"], "OFF")

    def test_295_catalog_freshness_digest_is_deterministic(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        self.assertEqual(
            catalog_freshness_sha256(snapshot, freshness),
            catalog_freshness_sha256(
                snapshot,
                copy.deepcopy(freshness),
            ),
        )

    def test_296_valid_gemini_pilot_freshness_binding(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        binding = build_pilot_freshness_binding(
            snapshot,
            plan,
            freshness,
        )
        self.assertEqual(
            validate_pilot_freshness_binding(
                snapshot,
                plan,
                freshness,
                binding,
            ),
            binding,
        )

    def test_297_valid_claude_pilot_freshness_binding(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        binding = build_pilot_freshness_binding(
            snapshot,
            plan,
            freshness,
        )
        self.assertEqual(binding["provider"], "ANTHROPIC_CLAUDE")
        self.assertEqual(
            binding["model_id"],
            "claude-haiku-4-5-20251001",
        )

    def test_298_pilot_freshness_binding_rejects_plan_digest_tamper(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        binding = build_pilot_freshness_binding(
            snapshot,
            plan,
            freshness,
        )
        binding["pilot_dry_run_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_pilot_freshness_binding(
                snapshot,
                plan,
                freshness,
                binding,
            )

    def test_299_pilot_freshness_binding_rejects_receipt_digest_tamper(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "ANTHROPIC_CLAUDE",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        binding = build_pilot_freshness_binding(
            snapshot,
            plan,
            freshness,
        )
        binding["catalog_freshness_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_pilot_freshness_binding(
                snapshot,
                plan,
                freshness,
                binding,
            )

    def test_300_pilot_freshness_binding_digest_is_deterministic(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        plan = build_first_provider_pilot_dry_run(
            snapshot,
            "GOOGLE_GEMINI",
            prelive_candidate_head=
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            prelive_candidate_seal_blob=
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        binding = build_pilot_freshness_binding(
            snapshot,
            plan,
            freshness,
        )
        first = pilot_freshness_binding_sha256(
            snapshot,
            plan,
            freshness,
            binding,
        )
        second = pilot_freshness_binding_sha256(
            snapshot,
            copy.deepcopy(plan),
            copy.deepcopy(freshness),
            copy.deepcopy(binding),
        )
        self.assertEqual(first, second)


    def test_301_valid_control_time_attestation(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        self.assertEqual(
            validate_execution_time_attestation(attestation),
            attestation,
        )

    def test_302_time_attestation_requires_control_runtime_clock(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "USER_SUPPLIED_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        with self.assertRaises(ResearchContractError):
            validate_execution_time_attestation(attestation)

    def test_303_time_attestation_requires_source_digest(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "bad",
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        with self.assertRaises(ResearchContractError):
            validate_execution_time_attestation(attestation)

    def test_304_time_attestation_cannot_be_recorded_before_attested(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:29:59Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        with self.assertRaises(ResearchContractError):
            validate_execution_time_attestation(attestation)

    def test_305_time_attestation_recording_delay_is_bounded(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:31:01Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        with self.assertRaises(ResearchContractError):
            validate_execution_time_attestation(attestation)

    def test_306_time_attestation_grants_no_authority(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "live_execution_performed",
        ):
            broken = copy.deepcopy(attestation)
            broken[key] = True
            with self.assertRaises(ResearchContractError):
                validate_execution_time_attestation(broken)

    def test_307_valid_catalog_freshness_time_binding(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        binding = build_catalog_freshness_time_binding(
            snapshot,
            freshness,
            attestation,
        )
        self.assertEqual(
            validate_catalog_freshness_time_binding(
                snapshot,
                freshness,
                attestation,
                binding,
            ),
            binding,
        )

    def test_308_freshness_checked_at_must_exactly_match_attested_at(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:01Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        with self.assertRaises(ResearchContractError):
            build_catalog_freshness_time_binding(
                snapshot,
                freshness,
                attestation,
            )

    def test_309_freshness_time_binding_rejects_catalog_digest_tamper(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        binding = build_catalog_freshness_time_binding(
            snapshot,
            freshness,
            attestation,
        )
        binding["catalog_freshness_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_catalog_freshness_time_binding(
                snapshot,
                freshness,
                attestation,
                binding,
            )

    def test_310_freshness_time_binding_rejects_attestation_digest_tamper(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        binding = build_catalog_freshness_time_binding(
            snapshot,
            freshness,
            attestation,
        )
        binding["time_attestation_sha256"] = "0" * 64
        with self.assertRaises(ResearchContractError):
            validate_catalog_freshness_time_binding(
                snapshot,
                freshness,
                attestation,
                binding,
            )

    def test_311_time_attestation_digest_is_deterministic(self):
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        self.assertEqual(
            execution_time_attestation_sha256(attestation),
            execution_time_attestation_sha256(
                copy.deepcopy(attestation)
            ),
        )

    def test_312_freshness_time_binding_digest_is_deterministic(self):
        snapshot = json.loads(
            Path(__file__).with_name(
                "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
            ).read_text()
        )
        freshness = build_catalog_freshness_receipt(
            snapshot,
            checked_at="2026-09-08T11:30:00Z",
        )
        attestation = {
            "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
            "attestation_id": "control-time-001",
            "source": "CONTROL_RUNTIME_CLOCK",
            "source_ref": "control-runtime-clock-001",
            "source_observation_sha256": "c" * 64,
            "attested_at": "2026-09-08T11:30:00Z",
            "recorded_at": "2026-09-08T11:30:05Z",
            "prelive_candidate_head":
                "d354bfa274b1f6a4ba116fbfa27356ce01979677",
            "prelive_candidate_seal_blob":
                "89d17c2978749da8bd4e146c06ed16ce0fa8730e",
            "provider_call_authorized": False,
            "credential_authorized": False,
            "spend_authorized": False,
            "live_execution_performed": False,
            "runtime": "OFF",
        }
        binding = build_catalog_freshness_time_binding(
            snapshot,
            freshness,
            attestation,
        )
        first = catalog_freshness_time_binding_sha256(
            snapshot,
            freshness,
            attestation,
            binding,
        )
        second = catalog_freshness_time_binding_sha256(
            snapshot,
            copy.deepcopy(freshness),
            copy.deepcopy(attestation),
            copy.deepcopy(binding),
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
