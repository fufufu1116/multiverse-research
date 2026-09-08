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
    ROOT / "synthetic_adapter.py",
    ROOT / "test_phase_a.py",
    ROOT / "README.md",
]

FORBIDDEN_PROVIDER_MARKERS = [
    "anthropic_api_key",
    "google_api_key",
    "gemini_api_key",
    "claude_api_key",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
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
            f"no_live_provider:{marker}",
            marker not in package_text,
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
        test_count == 124,
        f"{test_count} != 124",
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
