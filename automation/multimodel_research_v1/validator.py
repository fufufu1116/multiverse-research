from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

REQUIRED = [
    ROOT / "__init__.py",
    ROOT / "model.py",
    ROOT / "outcome.py",
    ROOT / "aggregator.py",
    ROOT / "assignment.py",
    ROOT / "fanout.py",
    ROOT / "model_target.py",
    ROOT / "capability.py",
    ROOT / "prompting.py",
    ROOT / "request_envelope.py",
    ROOT / "termination.py",
    ROOT / "receipt.py",
    ROOT / "smoke_profile.py",
    ROOT / "gemini_adapter.py",
    ROOT / "claude_adapter.py",
    ROOT / "transport_binding.py",
    ROOT / "observation_binding.py",
    ROOT / "execution_prep.py",
    ROOT / "readiness.py",
    ROOT / "provider_catalog.py",
    ROOT / "pilot_matrix.py",
    ROOT / "pilot_dry_run.py",
    ROOT / "catalog_freshness.py",
    ROOT / "time_attestation.py",
    ROOT / "pre_execution_bundle.py",
    ROOT / "launch_evidence.py",
    ROOT / "pilot_roundtrip.py",
    ROOT / "pilot_roundtrip_v2.py",
    ROOT / "provider_result_schema.py",
    ROOT / "provider_result_ingestion.py",
    ROOT / "rehearsal_convergence.py",
    ROOT / "dual_provider_research.py",
    ROOT / "dual_provider_fanout.py",
    ROOT / "federation_rehearsal.py",
    ROOT / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json",
    ROOT / "synthetic_adapter.py",
    ROOT / "test_phase_a.py",
    ROOT / "README.md",
]

FORBIDDEN_PROVIDER_MARKERS = [
    "anthropic_api_key",
    "google_api_key",
    "gemini_api_key",
    "claude_api_key",
]

FORBIDDEN_NETWORK_EXECUTION_MARKERS = [
    "requests.",
    "httpx.",
    "urllib.request",
    "aiohttp.",
    "socket.",
    "http.client",
    "urlopen(",
    "client.interactions.create(",
    "client.messages.create(",
    "anthropic(",
    "genai.client(",
]

FORBIDDEN_EXECUTION_MARKERS = [
    "subprocess",
    "os.system",
    "eval(",
    "exec(",
]


def validate() -> dict:
    checks = {}
    findings = []

    def record(name, condition, detail=""):
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    for path in REQUIRED:
        record(
            f"file:{path.name}",
            path.is_file(),
            "missing",
        )

    for path in REQUIRED:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            compile(path.read_text(), str(path), "exec")
            record(f"compile:{path.name}", True)
        except Exception as exc:
            record(
                f"compile:{path.name}",
                False,
                repr(exc),
            )

    package_text = "\n".join(
        path.read_text()
        for path in REQUIRED
        if path.is_file()
    ).lower()

    for marker in FORBIDDEN_PROVIDER_MARKERS:
        record(
            f"no_provider_credentials:{marker}",
            marker not in package_text,
            marker,
        )

    network_surface_paths = [
        path
        for path in REQUIRED
        if (
            path.suffix == ".py"
            and path.is_file()
            and path.name not in {
                "validator.py",
                "test_phase_a.py",
            }
        )
    ]
    python_text = "\n".join(
        path.read_text().lower()
        for path in network_surface_paths
    )

    for marker in FORBIDDEN_NETWORK_EXECUTION_MARKERS:
        record(
            f"no_network_execution:{marker}",
            marker not in python_text,
            marker,
        )

    for marker in FORBIDDEN_EXECUTION_MARKERS:
        record(
            f"no_dynamic_execution:{marker}",
            marker not in (
                (ROOT / "model.py").read_text()
                + (ROOT / "aggregator.py").read_text()
                + (ROOT / "synthetic_adapter.py").read_text()
            ),
            marker,
        )

    model = (ROOT / "model.py").read_text()
    aggregator = (ROOT / "aggregator.py").read_text()
    outcome = (ROOT / "outcome.py").read_text()
    assignment = (ROOT / "assignment.py").read_text()
    fanout = (ROOT / "fanout.py").read_text()
    model_target = (ROOT / "model_target.py").read_text()
    capability = (ROOT / "capability.py").read_text()
    prompting = (ROOT / "prompting.py").read_text()
    request_envelope = (ROOT / "request_envelope.py").read_text()
    termination = (ROOT / "termination.py").read_text()
    receipt = (ROOT / "receipt.py").read_text()
    smoke_profile = (ROOT / "smoke_profile.py").read_text()
    gemini_adapter = (ROOT / "gemini_adapter.py").read_text()
    claude_adapter = (ROOT / "claude_adapter.py").read_text()
    transport_binding = (ROOT / "transport_binding.py").read_text()
    observation_binding = (ROOT / "observation_binding.py").read_text()
    execution_prep = (ROOT / "execution_prep.py").read_text()
    readiness = (ROOT / "readiness.py").read_text()
    provider_catalog = (ROOT / "provider_catalog.py").read_text()
    pilot_matrix = (ROOT / "pilot_matrix.py").read_text()
    pilot_dry_run = (ROOT / "pilot_dry_run.py").read_text()
    catalog_freshness = (ROOT / "catalog_freshness.py").read_text()
    time_attestation = (ROOT / "time_attestation.py").read_text()
    pre_execution_bundle = (ROOT / "pre_execution_bundle.py").read_text()
    launch_evidence = (ROOT / "launch_evidence.py").read_text()
    pilot_roundtrip = (ROOT / "pilot_roundtrip.py").read_text()
    pilot_roundtrip_v2 = (ROOT / "pilot_roundtrip_v2.py").read_text()
    provider_result_schema = (ROOT / "provider_result_schema.py").read_text()
    provider_result_ingestion = (
        ROOT / "provider_result_ingestion.py"
    ).read_text()
    rehearsal_convergence = (ROOT / "rehearsal_convergence.py").read_text()
    dual_provider_research = (ROOT / "dual_provider_research.py").read_text()
    dual_provider_fanout = (ROOT / "dual_provider_fanout.py").read_text()
    federation_rehearsal = (ROOT / "federation_rehearsal.py").read_text()
    provider_catalog_snapshot = json.loads(
        (
            ROOT
            / "PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json"
        ).read_text()
    )

    transport_code = (
        gemini_adapter
        + claude_adapter
        + transport_binding
        + observation_binding
    ).lower()
    for host in (
        "generativelanguage.googleapis.com",
        "api.anthropic.com",
    ):
        record(
            f"host_declared_only_outside_transport_code:{host}",
            host not in transport_code,
            host,
        )

    for token in (
        "MULTIVERSE_RESEARCH_TASK_v1",
        "MULTIVERSE_RESEARCH_TASK_v2",
        "MULTIVERSE_RESEARCH_RESULT_v1",
        "MULTIVERSE_RESEARCH_AGGREGATE_v2",
        "FORBIDDEN_DYNAMIC_KEYS",
        "ALLOWED_PRIMITIVES",
        "INFRA_FAILURE",
        "nonauthority",
        "validate_result_for_task",
        "RESULT_EVIDENCE_PRIMITIVE_NOT_ALLOWED",
        "RESULT_MAX_FINDINGS_EXCEEDED",
        "RESULT_MAX_OUTPUT_BYTES_EXCEEDED",
        "RESULT_TASK_SHA256_MISMATCH",
        "DUPLICATE_CLAIM_KEY",
        "produced_at",
        "observed_at",
        "SOURCE_REF_OBSERVED_AFTER_TASK_CREATED",
        "RESULT_PRODUCED_BEFORE_TASK_CREATED",
        "NONCOMPLETED_REQUIRES_UNCERTAINTY",
        "RESULT_EVIDENCE_SOURCE_DIGEST_REQUIRED",
        "RESULT_EVIDENCE_SOURCE_SHA256_MISMATCH",
        "evidence_manifest",
        "TASK_EVIDENCE_MANIFEST_SHA256_REQUIRED",
        "TASK_EVIDENCE_MANIFEST_OBSERVED_AFTER_TASK_CREATED",
        "DUPLICATE_TASK_EVIDENCE_MANIFEST_ENTRY",
        "RESULT_EVIDENCE_MANIFEST_NOT_DECLARED",
        "RESULT_EVIDENCE_MANIFEST_SHA256_MISMATCH",
        "TASK_EVIDENCE_SOURCE_REF_NOT_DECLARED",
        "TASK_EVIDENCE_SOURCE_DIGEST_REQUIRED",
        "TASK_EVIDENCE_SOURCE_SHA256_MISMATCH",
    ):
        record(
            f"model:{token}",
            token in model,
            token,
        )

    for token in (
        "duplicate_acknowledgements",
        "UNRESOLVED_DIVERGENCE",
        "MECHANICAL_FALSIFICATION_TASK",
        "vote_confers_authority",
        "majority_confers_truth",
        "adoption_authority",
        "MODEL_IDENTITY_CONTENT_CONFLICT",
        "task_sha256",
        "noncompleted_results",
        "unique_model_identity_count",
        "SUPPORT_WITH_UNKNOWN",
        "OPPOSE_WITH_UNKNOWN",
        "status_counts",
        "requested_role_coverage",
        "missing_requested_roles",
        "roles_without_completed_result",
        "requested_role_coverage_complete",
        "DUPLICATE_SUBMISSION_ID",
        "aggregate_results_v2",
        "observed_unique_advisory_identity_count",
        "completed_unique_advisory_identity_count",
        "observed_unique_provider_model_count",
        "completed_unique_provider_model_count",
        "observed_unique_provider_count",
        "completed_unique_provider_count",
        "provider_model_position_presence_counts",
        "provider_position_presence_counts",
        "role_conditioned_divergence",
        "cross_model_divergence",
        "cross_provider_divergence",
        "descriptive_label_scope",
    ):
        record(
            f"aggregator:{token}",
            token in aggregator,
            token,
        )

    for token in (
        "MULTIVERSE_RESEARCH_ASSIGNMENT_v1",
        "MULTIVERSE_RESEARCH_RESULT_v2",
        "validate_assignment",
        "ASSIGNMENT_REQUIRES_TASK_V2",
        "ASSIGNMENT_TASK_SHA256_MISMATCH",
        "ASSIGNMENT_ROLE_NOT_REQUESTED",
        "ASSIGNMENT_RESEARCH_NETWORK_WIDENED",
        "ASSIGNMENT_MAX_COMPUTE_WIDENED",
        "ASSIGNMENT_MAX_OUTPUT_WIDENED",
        "SYNTHETIC_ASSIGNMENT_PROVIDER_TRANSPORT_FORBIDDEN",
        "LIVE_ASSIGNMENT_PROVIDER_TRANSPORT_REQUIRED",
        "LIVE_ASSIGNMENT_ATTESTATION_REQUIRED",
        "validate_result_v2_for_assignment",
        "RESULT_V2_ASSIGNMENT_SHA256_MISMATCH",
        "RESULT_V2_PROVIDER_MISMATCH",
        "RESULT_V2_MODEL_MISMATCH",
        "RESULT_V2_ROLE_MISMATCH",
        "RESULT_V2_PRODUCED_BEFORE_ASSIGNMENT",
        "result_v2_content_digest",
    ):
        record(
            f"assignment:{token}",
            token in assignment,
            token,
        )

    for token in (
        "MULTIVERSE_RESEARCH_FANOUT_PLAN_v1",
        "MULTIVERSE_RESEARCH_BATCH_SUMMARY_v1",
        "validate_fanout_plan",
        "DUPLICATE_FANOUT_ASSIGNMENT_ID",
        "DUPLICATE_FANOUT_LOGICAL_TARGET",
        "FANOUT_PLAN_ASSIGNMENT_SET_MISMATCH",
        "FANOUT_PLAN_CREATED_BEFORE_ASSIGNMENT",
        "summarize_fanout_results",
        "FANOUT_RESULT_NOT_PLANNED",
        "DUPLICATE_FANOUT_RESULT_FOR_ASSIGNMENT",
        "missing_assignment_sha256s",
        "all_planned_observed",
        "all_planned_completed",
        "fanout_plan_sha256",
    ):
        record(
            f"fanout:{token}",
            token in fanout,
            token,
        )

    for token in (
        "MULTIVERSE_MODEL_TARGET_POLICY_v1",
        "validate_model_target_policy",
        "MODEL_TARGET_ASSIGNMENT_SHA256_MISMATCH",
        "MODEL_TARGET_PROVIDER_MISMATCH",
        "MODEL_TARGET_MODEL_ID_MISMATCH",
        "MODEL_TARGET_ALIAS_FORBIDDEN",
        "MODEL_TARGET_PREVIEW_FORBIDDEN",
        "MODEL_TARGET_EXPERIMENTAL_FORBIDDEN",
        "MODEL_TARGET_RESOLVED_ID_REQUIRED",
        "MODEL_TARGET_STABLE_API_REQUIRED",
        "MODEL_TARGET_NOT_PINNED_OR_STABLE",
        "classification_evidence_sha256",
        "validate_resolved_model_id",
        "OBSERVED_MODEL_ID_MISMATCH",
        "model_target_policy_sha256",
    ):
        record(
            f"model_target:{token}",
            token in model_target,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_CAPABILITY_POLICY_v1",
        "validate_capability_policy",
        "CAPABILITY_ASSIGNMENT_SHA256_MISMATCH",
        "CAPABILITY_MODEL_TARGET_SHA256_MISMATCH",
        "CAPABILITY_TOOLS_FORBIDDEN",
        "CAPABILITY_PROVIDER_RETRIEVAL_FORBIDDEN",
        "CAPABILITY_CODE_EXECUTION_FORBIDDEN",
        "CAPABILITY_FILE_ACCESS_FORBIDDEN",
        "CAPABILITY_PROVIDER_MEMORY_FORBIDDEN",
        "CAPABILITY_FUNCTION_CALLING_FORBIDDEN",
        "CAPABILITY_STRUCTURED_OUTPUT_JSON_REQUIRED",
        "CAPABILITY_STREAMING_FORBIDDEN",
        "capability_policy_sha256",
    ):
        record(
            f"capability:{token}",
            token in capability,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_NEUTRAL_PROMPT_v1",
        "build_provider_neutral_prompt",
        "PROMPT_REQUIRES_TASK_V2",
        "PROMPT_ROLE_NOT_REQUESTED",
        "PROMPT_EXACT_BINDING_MISMATCH",
        "provider_neutral_prompt_sha256",
    ):
        record(
            f"prompting:{token}",
            token in prompting,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_REQUEST_ENVELOPE_v1",
        "validate_request_envelope",
        "REQUEST_REQUIRES_LIVE_ASSIGNMENT",
        "REQUEST_ASSIGNMENT_SHA256_MISMATCH",
        "REQUEST_MODEL_TARGET_SHA256_MISMATCH",
        "REQUEST_CAPABILITY_SHA256_MISMATCH",
        "REQUEST_PROMPT_SHA256_MISMATCH",
        "REQUEST_PROVIDER_TRANSPORT_POLICY_MISMATCH",
        "REQUEST_OBJECTIVE_NOT_SYNTHETIC",
        "REQUEST_CLASSIFICATION_EVIDENCE_SHA256",
        "REQUEST_EGRESS_MANIFEST_MISMATCH",
        "REQUEST_OUTBOUND_PAYLOAD_SHA256",
        "request_envelope_sha256",
    ):
        record(
            f"request_envelope:{token}",
            token in request_envelope,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_TERMINATION_RECORD_v1",
        "validate_termination_record",
        "TERMINATION_REQUEST_SHA256_MISMATCH",
        "TRANSPORT_FAILURE",
        "TERMINATION_USAGE_METADATA_SHA256",
        "TERMINATION_RESPONSE_BEFORE_REQUEST",
        "termination_record_sha256",
    ):
        record(
            f"termination:{token}",
            token in termination,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1",
        "validate_execution_receipt",
        "LIVE_ATTESTED",
        "LIVE_PROVIDER_ID_UNVERIFIED",
        "RECEIPT_RESULT_SHA256_MISMATCH",
        "RECEIPT_PROVIDER_RESPONSE_SHA256",
        "RECEIPT_ADAPTER_SHA256_MISMATCH",
        "RECEIPT_RESPONSE_TIME_MISMATCH",
        "RECEIPT_TERMINATION_RESULT_STATUS_MISMATCH",
        "execution_receipt_sha256",
    ):
        record(
            f"receipt:{token}",
            token in receipt,
            token,
        )

    for token in (
        "MULTIVERSE_LIVE_PROVIDER_SMOKE_PROFILE_v1",
        "validate_live_smoke_profile",
        "SMOKE_EXACTLY_ONE_ASSIGNMENT_REQUIRED",
        "SMOKE_EXACTLY_ONE_PROVIDER_REQUIRED",
        "SMOKE_SINGLE_ATTEMPT_REQUIRED",
        "SMOKE_SYNTHETIC_ONLY_REQUIRED",
        "SMOKE_JSON_ONLY_REQUIRED",
        "SMOKE_STREAMING_FORBIDDEN",
        "SMOKE_PROTECTED_DATA_FORBIDDEN",
        "SMOKE_LIVE_BUSINESS_EFFECT_FORBIDDEN",
        "SMOKE_RUNTIME_ACTIVATION_FORBIDDEN",
        "SMOKE_ADOPTION_AUTHORITY_FORBIDDEN",
        "live_smoke_profile_sha256",
    ):
        record(
            f"smoke_profile:{token}",
            token in smoke_profile,
            token,
        )

    for token in (
        "MULTIVERSE_GEMINI_INTERACTIONS_V1_RENDER_v1",
        "MULTIVERSE_GEMINI_INTERACTIONS_V1_OBSERVATION_v1",
        "render_gemini_interactions_v1",
        '"api_version": "v1"',
        '"sdk_surface": "interactions.create"',
        '"store": False',
        '"stream": False',
        '"background": False',
        "GEMINI_RESPONSE_SCHEMA_SHA256_MISMATCH",
        "parse_gemini_interactions_v1_response",
        "PROVIDER_EMPTY",
        "PROVIDER_TRUNCATED",
        "TRANSPORT_FAILURE",
        "provider_response_sha256",
        "usage_metadata_sha256",
    ):
        record(
            f"gemini_adapter:{token}",
            token in gemini_adapter,
            token,
        )

    for token in (
        "MULTIVERSE_CLAUDE_MESSAGES_RENDER_v1",
        "MULTIVERSE_CLAUDE_MESSAGES_OBSERVATION_v1",
        "render_claude_messages_request",
        '"sdk_surface": "messages.create"',
        '"stateless": True',
        '"stream": False',
        '"type": "json_schema"',
        "CLAUDE_RESPONSE_SCHEMA_SHA256_MISMATCH",
        "parse_claude_messages_response",
        "PROVIDER_REFUSED",
        "PROVIDER_EMPTY",
        "PROVIDER_TRUNCATED",
        "CLAUDE_UNEXPECTED_SERVER_TOOL_USE",
        "provider_response_sha256",
        "usage_metadata_sha256",
    ):
        record(
            f"claude_adapter:{token}",
            token in claude_adapter,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_TRANSPORT_BINDING_v1",
        "validate_transport_binding",
        "TRANSPORT_RENDER_EXACT_MISMATCH",
        "TRANSPORT_CREDENTIAL_MATERIAL_FORBIDDEN",
        "TRANSPORT_OUTBOUND_PAYLOAD_SHA256_MISMATCH",
        "transport_binding_sha256",
        "GOOGLE_GEMINI",
        "ANTHROPIC_CLAUDE",
    ):
        record(
            f"transport_binding:{token}",
            token in transport_binding,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_OBSERVATION_BINDING_v1",
        "validate_provider_observation_binding",
        "OBSERVATION_RESPONSE_ID_TERMINATION_MISMATCH",
        "OBSERVATION_RESPONSE_ID_RECEIPT_MISMATCH",
        "OBSERVATION_NORMALIZED_STATE_MISMATCH",
        "OBSERVATION_INPUT_TOKENS_MISMATCH",
        "OBSERVATION_OUTPUT_TOKENS_MISMATCH",
        "OBSERVATION_USAGE_SHA256_MISMATCH",
        "OBSERVATION_RESPONSE_SHA256_MISMATCH",
        "OBSERVATION_MODEL_ID_RECEIPT_MISMATCH",
        "provider_observation_binding_sha256",
    ):
        record(
            f"observation_binding:{token}",
            token in observation_binding,
            token,
        )

    for token in (
        "MULTIVERSE_LIVE_PROVIDER_EXECUTION_PREP_v1",
        "validate_live_execution_prep",
        "generativelanguage.googleapis.com",
        "api.anthropic.com",
        "EXECUTION_PREP_HOST_MISMATCH",
        "EXECUTION_PREP_OPERATION_MISMATCH",
        "EXECUTION_PREP_CREDENTIAL_MATERIAL_FORBIDDEN",
        "EXECUTION_PREP_SINGLE_ATTEMPT_REQUIRED",
        "EXECUTION_PREP_INPUT_TOKEN_CEILING",
        "EXECUTION_PREP_OUTPUT_TOKEN_CEILING",
        "EXECUTION_PREP_COST_CEILING",
        "EXECUTION_PREP_AUTHORITY_REQUIRED",
        "EXECUTION_PREP_RUNTIME_FORBIDDEN",
        "live_execution_prep_sha256",
    ):
        record(
            f"execution_prep:{token}",
            token in execution_prep,
            token,
        )

    for token in (
        "MULTIVERSE_LIVE_PROVIDER_READINESS_REPORT_v1",
        "READY_FOR_SEPARATE_PROVIDER_AUTHORITY",
        "build_live_provider_readiness_report",
        "validate_live_provider_readiness_report",
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "READINESS_FORBIDDEN_TRUE",
        "READINESS_RUNTIME_NOT_OFF",
        "live_provider_readiness_sha256",
    ):
        record(
            f"readiness:{token}",
            token in readiness,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_MODEL_CATALOG_SNAPSHOT_v1",
        "validate_provider_catalog",
        "catalog_entry_sha256",
        "estimate_smoke_cost_usd_micros",
        "validate_first_smoke_candidate",
        "CATALOG_SMOKE_COST_EXCEEDS_CEILING",
    ):
        record(
            f"provider_catalog:{token}",
            token in provider_catalog,
            token,
        )

    for provider, model_id in (
        ("GOOGLE_GEMINI", "gemini-3.8-flash"),
        ("ANTHROPIC_CLAUDE", "claude-haiku-4-5-20251001"),
    ):
        matches = [
            item
            for item in provider_catalog_snapshot["entries"]
            if item["provider"] == provider
        ]
        record(
            f"provider_catalog_snapshot:{provider}:one_entry",
            len(matches) == 1,
            provider,
        )
        if matches:
            record(
                f"provider_catalog_snapshot:{provider}:model_id",
                matches[0]["model_id"] == model_id,
                matches[0]["model_id"],
            )

    for token in (
        "MULTIVERSE_FIRST_PROVIDER_PILOT_DRY_RUN_v1",
        "PHASE_B_FIRST_PROVIDER_PILOT_PREPARATION_ONLY",
        "build_first_provider_pilot_dry_run",
        "validate_first_provider_pilot_dry_run",
        "PILOT_CATALOG_SNAPSHOT_SHA256_MISMATCH",
        "PILOT_MODEL_ID_MISMATCH",
        "PILOT_CATALOG_ENTRY_SHA256_MISMATCH",
        "PILOT_COST_ESTIMATE_MISMATCH",
        "PILOT_EXACTLY_ONE_PROVIDER",
        "PILOT_EXACTLY_ONE_CALL",
        "PILOT_EXACTLY_ONE_ATTEMPT",
        "PILOT_SYNTHETIC_ONLY",
        "PILOT_JSON_ONLY",
        "PILOT_NETWORK_EXECUTION_FORBIDDEN",
        "PILOT_CREDENTIAL_MATERIAL_FORBIDDEN",
        "PILOT_AUTHORITY_REQUIRED",
        "PILOT_FORBIDDEN_TRUE",
        "PILOT_RUNTIME_NOT_OFF",
        "build_pilot_candidate_matrix",
        "first_provider_pilot_dry_run_sha256",
    ):
        record(
            f"pilot_dry_run:{token}",
            token in pilot_dry_run,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_CATALOG_FRESHNESS_v1",
        "MULTIVERSE_FIRST_PROVIDER_PILOT_FRESHNESS_BINDING_v1",
        "MAX_EXECUTION_CATALOG_AGE_SECONDS = 86400",
        "build_catalog_freshness_receipt",
        "validate_catalog_freshness_receipt",
        "CATALOG_FRESHNESS_CHECK_BEFORE_SNAPSHOT",
        "CATALOG_SNAPSHOT_STALE",
        "CATALOG_PRICING_WINDOW_EXPIRED",
        "CATALOG_FRESHNESS_SNAPSHOT_SHA256_MISMATCH",
        "CATALOG_FRESHNESS_FORBIDDEN_TRUE",
        "build_pilot_freshness_binding",
        "validate_pilot_freshness_binding",
        "PILOT_FRESHNESS_PLAN_SHA256_MISMATCH",
        "PILOT_FRESHNESS_RECEIPT_SHA256_MISMATCH",
        "PILOT_FRESHNESS_FORBIDDEN_TRUE",
        "pilot_freshness_binding_sha256",
    ):
        record(
            f"catalog_freshness:{token}",
            token in catalog_freshness,
            token,
        )

    for token in (
        "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
        "MULTIVERSE_CATALOG_FRESHNESS_TIME_BINDING_v1",
        "CONTROL_RUNTIME_CLOCK",
        "MAX_RECORDING_DELAY_SECONDS = 60",
        "validate_execution_time_attestation",
        "TIME_ATTESTATION_RECORDED_BEFORE_ATTESTED",
        "TIME_ATTESTATION_RECORDING_DELAY_EXCEEDED",
        "TIME_ATTESTATION_FORBIDDEN_TRUE",
        "build_catalog_freshness_time_binding",
        "validate_catalog_freshness_time_binding",
        "FRESHNESS_TIME_NOT_EXACT",
        "FRESHNESS_TIME_CATALOG_SHA256_MISMATCH",
        "FRESHNESS_TIME_ATTESTATION_SHA256_MISMATCH",
        "FRESHNESS_TIME_FORBIDDEN_TRUE",
        "catalog_freshness_time_binding_sha256",
    ):
        record(
            f"time_attestation:{token}",
            token in time_attestation,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_PILOT_MATRIX_v1",
        "build_provider_pilot_matrix",
        "validate_provider_pilot_matrix",
        "provider_pilot_matrix_sha256",
        "catalog_entry_sha256",
        "adapter_source_sha256",
        "outbound_payload_sha256",
        "build_live_provider_readiness_report",
        "validate_live_provider_readiness_report",
        "live_execution_prep_sha256",
        "transport_binding_sha256",
    ):
        record(
            f"pilot_matrix:{token}",
            token in pilot_matrix,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_PRE_EXECUTION_BUNDLE_v1",
        "build_provider_pre_execution_bundle",
        "validate_provider_pre_execution_bundle",
        "PRE_EXECUTION_PRELIVE_HEAD_MISMATCH",
        "PRE_EXECUTION_PRELIVE_SEAL_MISMATCH",
        "PRE_EXECUTION_CATALOG_SNAPSHOT_SHA256_MISMATCH",
        "PRE_EXECUTION_PILOT_SHA256_MISMATCH",
        "PRE_EXECUTION_FRESHNESS_SHA256_MISMATCH",
        "PRE_EXECUTION_PILOT_FRESHNESS_SHA256_MISMATCH",
        "PRE_EXECUTION_TIME_ATTESTATION_SHA256_MISMATCH",
        "PRE_EXECUTION_FRESHNESS_TIME_SHA256_MISMATCH",
        "PRE_EXECUTION_FORBIDDEN_TRUE",
        "PRE_EXECUTION_RUNTIME_NOT_OFF",
        "provider_pre_execution_bundle_sha256",
    ):
        record(
            f"pre_execution_bundle:{token}",
            token in pre_execution_bundle,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_LAUNCH_EVIDENCE_v1",
        "build_provider_launch_evidence",
        "validate_provider_launch_evidence",
        "LAUNCH_EVIDENCE_PROVIDER_MISMATCH",
        "LAUNCH_EVIDENCE_MODEL_MISMATCH",
        "LAUNCH_EVIDENCE_INPUT_CEILING_MISMATCH",
        "LAUNCH_EVIDENCE_OUTPUT_CEILING_MISMATCH",
        "LAUNCH_EVIDENCE_COST_CEILING_MISMATCH",
        "REPOSITORY_EVIDENCE_ALIGNED_AUTHORITY_ABSENT",
        "LAUNCH_EVIDENCE_FORBIDDEN_TRUE",
        "LAUNCH_EVIDENCE_RUNTIME_NOT_OFF",
        "provider_launch_evidence_sha256",
    ):
        record(
            f"launch_evidence:{token}",
            token in launch_evidence,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_PILOT_ROUNDTRIP_v1",
        "build_provider_pilot_roundtrip",
        "validate_provider_pilot_roundtrip",
        "parse_gemini_interactions_v1_response",
        "parse_claude_messages_response",
        "validate_termination_record",
        "validate_result_v2_for_assignment",
        "validate_execution_receipt",
        "validate_provider_observation_binding",
        "LIVE_ATTESTED",
        "PILOT_ROUNDTRIP_EXACT_MISMATCH",
        "provider_pilot_roundtrip_sha256",
    ):
        record(
            f"pilot_roundtrip:{token}",
            token in pilot_roundtrip,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_PILOT_ROUNDTRIP_v2",
        "build_provider_pilot_roundtrip_v2",
        "validate_provider_pilot_roundtrip_v2",
        "provider_pilot_roundtrip_v2_sha256",
        "result_from_provider_output",
        "provider_result_ingestion_sha256",
        "PILOT_ROUNDTRIP_V2_RESULT_NOT_FROM_PROVIDER_OUTPUT",
    ):
        record(
            f"pilot_roundtrip_v2:{token}",
            token in pilot_roundtrip_v2,
            token,
        )

    for token in (
        "build_result_v2_response_schema",
        "validate_result_v2_response_schema",
        "result_v2_response_schema_sha256",
        "RESULT_V2_RESPONSE_SCHEMA_EXACT_MISMATCH",
        "assignment_sha256",
        "additionalProperties",
        "model_identity",
        "assignment_sha256",
    ):
        record(
            f"provider_result_schema:{token}",
            token in provider_result_schema,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_RESULT_INGESTION_v1",
        "build_provider_result_ingestion",
        "validate_provider_result_ingestion",
        "provider_result_ingestion_sha256",
        "PROVIDER_RESULT_JSON_DUPLICATE_KEY",
        "PROVIDER_RESULT_JSON_NONFINITE",
        "PROVIDER_RESULT_JSON_INVALID",
        "PROVIDER_RESULT_ASSIGNMENT_OUTPUT_LIMIT_EXCEEDED",
        "PROVIDER_RESULT_OBSERVED_MODEL_MISMATCH",
        "validate_result_v2_for_assignment",
        "result_v2_content_digest",
    ):
        record(
            f"provider_result_ingestion:{token}",
            token in provider_result_ingestion,
            token,
        )

    for token in (
        "MULTIVERSE_PROVIDER_REHEARSAL_CONVERGENCE_v1",
        "build_provider_rehearsal_convergence",
        "validate_provider_rehearsal_convergence",
        "REHEARSAL_PROVIDER_MISMATCH",
        "REHEARSAL_MODEL_MISMATCH",
        "REHEARSAL_MATRIX_SHA256_MISMATCH",
        "estimate_smoke_cost_usd_micros",
        "REHEARSAL_INPUT_TOKENS_EXCEED_PREFLIGHT",
        "REHEARSAL_OUTPUT_TOKENS_EXCEED_PREFLIGHT",
        "REHEARSAL_SIMULATED_COST_EXCEEDS_PREFLIGHT",
        "FULL_OFFLINE_REHEARSAL_ALIGNED_AUTHORITY_ABSENT",
        "REHEARSAL_FORBIDDEN_TRUE",
        "REHEARSAL_RUNTIME_NOT_OFF",
        "provider_rehearsal_convergence_sha256",
    ):
        record(
            f"rehearsal_convergence:{token}",
            token in rehearsal_convergence,
            token,
        )

    for token in (
        "MULTIVERSE_DUAL_PROVIDER_OFFLINE_RESEARCH_v1",
        "build_dual_provider_offline_research",
        "validate_dual_provider_offline_research",
        "aggregate_results_v2",
        "DIVERGENT",
        "cross_model_divergence",
        "cross_provider_divergence",
        "UNRESOLVED_DIVERGENCE",
        "MECHANICAL_FALSIFICATION_TASK",
        "SUPPORT_ONLY",
        "DUAL_PROVIDER_AGREEMENT_LABEL",
        "DUAL_PROVIDER_AGREEMENT_CROSS_MODEL",
        "DUAL_PROVIDER_AGREEMENT_CROSS_PROVIDER",
        "DUAL_PROVIDER_AGREEMENT_UNRESOLVED",
        "DUAL_PROVIDER_REFUSAL_LABEL",
        "DUAL_PROVIDER_REFUSAL_CROSS_MODEL",
        "DUAL_PROVIDER_REFUSAL_CROSS_PROVIDER",
        "DUAL_PROVIDER_REFUSAL_OBSERVED_PROVIDER_COUNT",
        "DUAL_PROVIDER_REFUSAL_COMPLETED_PROVIDER_COUNT",
        "DUAL_PROVIDER_REFUSAL_STATUS_COUNT",
        "DUAL_PROVIDER_REFUSAL_UNRESOLVED",
        "DUAL_PROVIDER_FORBIDDEN_TRUE",
        "DUAL_PROVIDER_RUNTIME_NOT_OFF",
        "dual_provider_offline_research_sha256",
    ):
        record(
            f"dual_provider_research:{token}",
            token in dual_provider_research,
            token,
        )

    for token in (
        "MULTIVERSE_DUAL_PROVIDER_FANOUT_REHEARSAL_v1",
        "build_dual_provider_fanout_rehearsal",
        "validate_dual_provider_fanout_rehearsal",
        "validate_fanout_plan",
        "summarize_fanout_results",
        "DUAL_FANOUT_FULL_PLANNED_COUNT",
        "DUAL_FANOUT_MISSING_ASSIGNMENT_COUNT",
        "DUAL_FANOUT_MISSING_OBSERVED_FLAG",
        "DUAL_FANOUT_MISSING_COMPLETED_FLAG",
        "DUAL_FANOUT_FAILURE_OBSERVED_COUNT",
        "DUAL_FANOUT_FAILURE_COMPLETED_COUNT",
        "DUAL_FANOUT_FAILURE_NONCOMPLETED_COUNT",
        "DUAL_FANOUT_FAILURE_REFUSED_COUNT",
        "DUAL_FANOUT_FAILURE_COMPLETED_FLAG",
        "DUAL_FANOUT_FORBIDDEN_TRUE",
        "DUAL_FANOUT_RUNTIME_NOT_OFF",
        "dual_provider_fanout_rehearsal_sha256",
    ):
        record(
            f"dual_provider_fanout:{token}",
            token in dual_provider_fanout,
            token,
        )

    for token in (
        "MULTIVERSE_DUAL_PROVIDER_FEDERATION_REHEARSAL_v1",
        "build_dual_provider_federation_rehearsal",
        "validate_dual_provider_federation_rehearsal",
        "FEDERATION_PRELIVE_HEAD_MISMATCH",
        "FEDERATION_PRELIVE_SEAL_MISMATCH",
        "FEDERATION_CHECKED_AT_MISMATCH",
        "FEDERATION_GEMINI_MATRIX_MISMATCH",
        "FEDERATION_CLAUDE_MATRIX_MISMATCH",
        "FEDERATION_PROMPT_SHA256_MISMATCH",
        "FEDERATION_FULL_BATCH_NOT_COMPLETE",
        "FEDERATION_MISSING_PROVIDER_ACCEPTED",
        "FEDERATION_FAILURE_NOT_OBSERVED",
        "FEDERATION_FAILED_PROVIDER_ACCEPTED",
        "FEDERATION_DISAGREEMENT_NOT_DETECTED",
        "FEDERATION_AGREEMENT_MISLABELED",
        "FEDERATION_REFUSAL_LABEL",
        "FEDERATION_REFUSAL_MISLABELED_DIVERGENT",
        "FEDERATION_REFUSAL_COMPLETED_PROVIDER_COUNT",
        "MECHANICAL_FALSIFICATION_TASK",
        "FEDERATION_FORBIDDEN_TRUE",
        "FEDERATION_RUNTIME_NOT_OFF",
        "dual_provider_federation_rehearsal_sha256",
    ):
        record(
            f"federation_rehearsal:{token}",
            token in federation_rehearsal,
            token,
        )

    for token in (
        '"PASS"',
        '"FIX_REQUIRED"',
        '"INFRA_FAILURE"',
        "authoritative_pass",
    ):
        record(
            f"outcome:{token}",
            token in outcome,
            token,
        )

    test_text = (ROOT / "test_phase_a.py").read_text()
    test_count = len(
        re.findall(
            r"^\s+def test_\d+_",
            test_text,
            re.M,
        )
    )
    record(
        "exact_test_count",
        test_count == 478,
        f"{test_count} != 478",
    )

    return {
        "schema": "MULTIVERSE_MULTIMODEL_PHASE_A_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "checks": checks,
        "findings": findings,
        "live_provider_execution": False,
        "provider_credentials": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
