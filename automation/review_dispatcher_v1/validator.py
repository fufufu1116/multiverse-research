from __future__ import annotations

import json
from pathlib import Path

from automation.review_dispatcher_v1 import validator_legacy_v1 as _legacy

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
BASELINE = REPO_ROOT / "governance" / "MULTIVERSE_COMMON_OPERATING_BASELINE_v1.json"
CONVERGENCE = REPO_ROOT / "governance" / "MULTIVERSE_CROSS_CHAT_CAPABILITY_CONVERGENCE_v1.md"

MODEL_LEGACY_REQUIRED = (
    "supersedes_request_sha256",
    "SAME_HEAD_SUPERSESSION_CHAIN_INVALID",
    "sha256_json(request)",
    "def github_full_pr_binding(",
    "PR_DRAFT_BOOL",
    "PR_MERGED_BOOL",
    "def github_commit_tree_sha(",
    "def github_branch_commit_sha(",
    "def github_comment_id(",
)
MODEL_WRAPPER_REQUIRED = (
    "model_legacy_v1 as _legacy",
    "exact_current_owner_requests_v6",
    "latest_exact_current_owner_request_v6",
)
ARBITRATION_REQUIRED = (
    "generations.setdefault(predecessor, []).append",
    "winner = generation[0]",
    "SUPERSESSION_COMMENT_ORDER_INVALID",
    "ORPHANED_OR_LOSER_DERIVED_SUPERSESSION",
    "DUPLICATE_EXACT_REQUEST_ID",
)
PUBLISHER_LEGACY_REQUIRED = (
    "github_full_pr_binding(", "github_commit_tree_sha(",
    "github_branch_commit_sha(", "github_comment_id(",
)
PUBLISHER_WRAPPER_REQUIRED = (
    "assert_job_request_still_canonical(",
    "assert_published_result_is_canonical(",
    "recover_publish_receipt(",
)
T2_LEGACY_REQUIRED = (
    "github_full_pr_binding(", "github_commit_tree_sha(",
    "github_branch_commit_sha(", "github_comment_id(",
    "required_positive_int(",
)
T2_WRAPPER_REQUIRED = (
    "assert_referenced_result_is_canonical(",
    "assert_published_t2_is_canonical(",
    "recover_t2_receipt(",
    "_filter_noncanonical_lab_duplicates(",
    "_recover_existing_t2(",
)
LEGACY_FORBIDDEN = (
    'pr["merged"]', 'pr["draft"]', 'pr["state"]',
    'pr["head"]', 'pr["base"]', 'commit["commit"]',
    'main["commit"]', "comment['id']", 'result["id"]',
)
REQUIRED_FILES = (
    "model.py", "model_legacy_v1.py", "request_arbitration_v6.py",
    "test_request_arbitration_v6.py", "test_dispatcher.py",
    "test_dispatcher_legacy_v1.py",
    "publisher.py", "publisher_legacy_v1.py", "publisher_freshness_v1.py",
    "receipt_recovery_v1.py", "result_canonicalization_v1.py",
    "t2.py", "t2_legacy_v1.py", "t2_idempotence_v1.py",
    "t2_receipt_recovery_v1.py", "combined_fault_replay_v1.py",
    "test_integrated_resilience_convergence_v1.py",
    "lane_b_completion_matrix_v1.py", "test_lane_b_completion_matrix_v1.py",
    "test_validator_current_baseline_v1.py",
    "validator_legacy_v1.py",
)

WRAPPER_OBSOLETE_PREFIXES = (
    "model:request_identity:",
    "publisher:api_contract:", "publisher:no_raw_external_index:",
    "t2:api_contract:", "t2:no_raw_external_index:",
)
STALE_MIGRATION_CONVERGENCE_TOKENS = (
    "older chats must stop using the superseded common interface",
    "research chats do not replace Steps",
    "routine review YAML copy/paste count is zero",
)
STALE_MIGRATION_CHECK_KEYS = (
    "baseline:status",
    "baseline:baseline_version",
    "baseline:pipeline_policy",
) + tuple(f"convergence:{token[:30]}" for token in STALE_MIGRATION_CONVERGENCE_TOKENS)

CURRENT_BASELINE_TOP_LEVEL = {
    "schema": "MULTIVERSE_COMMON_OPERATING_BASELINE_v1",
    "status": "FIXED_REQUEST_ONLY_REVIEW_BASELINE_ACTIVE",
    "baseline_version": "2026-09-07.review-dispatcher-v1.request-only-baseline-active",
    "migration_issue": 152,
    "convergence_issue": 93,
    "runtime": "OFF",
}
CURRENT_COMMON_INTERFACES = {
    "candidate_intake": "single_adoption_intake",
    "review_submission": "durable_machine_readable_request",
    "independent_lab": "fixed_shared_request_only_dispatcher",
    "independent_auditor": "fixed_shared_request_only_dispatcher",
    "review_chain": "LAB_TO_T1_TO_AUDITOR_TO_T2_TO_SEPARATE_ADOPTION",
    "owner_courier": "not_required_for_routine_review_yaml",
    "self_adoption": False,
}
CURRENT_SHARED_PIPELINE_POLICY = {
    "migration_state": "COMPLETE",
    "installation_state": "FIXED_REINSTALLED_AND_REQUEST_ONLY_ROUTING_PROVEN",
    "research_lane_may_edit_steps": False,
    "shared_steps_are_common_infrastructure": True,
    "per_chat_step_replacement": "PROHIBITED",
    "future_shared_steps_change_requires_reviewed_adopted_infrastructure_repair_and_owner_authority": True,
    "per_job_binding_source": "exact_github_review_request_plus_request_sha256",
}
CURRENT_REVIEW_REQUEST = {
    "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
    "arbitrary_shell_allowed": False,
    "arbitrary_yaml_allowed": False,
    "arbitrary_python_allowed": False,
    "provider_credentials_allowed": False,
    "database_credentials_allowed": False,
    "exact_repo_pr_head_tree_base_main_required": True,
    "request_sha256_required": True,
    "same_head_supersession": "explicit_immediate_predecessor_sha256_chain",
    "silent_newest_wins": False,
    "auditor_upstream_lab_request_sha256_required": True,
}
CURRENT_CONVERGENCE_REQUIRED = (
    "Status: FIXED REQUEST-ONLY REVIEW BASELINE ACTIVE / DISPATCHER MIGRATION COMPLETE.",
    "Use durable machine-readable GitHub review requests for review routing.",
    "Never edit shared Independent Lab/Auditor Steps for a Candidate or job.",
    "`MULTIVERSE Independent Lab` and `MULTIVERSE Independent Auditor` are fixed shared infrastructure.",
    "Routine per-job review YAML couriering is obsolete under the fixed request-only baseline.",
    "Runtime remains OFF.",
)


def _record_tokens(checks, findings, scope, source, tokens):
    for token in tokens:
        key = f"{scope}:{token[:32]}"
        if token in source:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")


def _record_forbidden(checks, findings, scope, source, tokens):
    for token in tokens:
        key = f"{scope}:no_raw:{token[:32]}"
        if token not in source:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: found")


def _is_obsolete_legacy_finding(item: str) -> bool:
    if item.startswith(WRAPPER_OBSOLETE_PREFIXES):
        return True
    return any(item.startswith(f"{key}:") for key in STALE_MIGRATION_CHECK_KEYS)


def _is_obsolete_legacy_check(key: str) -> bool:
    return key.startswith(WRAPPER_OBSOLETE_PREFIXES) or key in STALE_MIGRATION_CHECK_KEYS


def _record_mapping_contract(checks, findings, scope, actual, expected):
    for field, expected_value in expected.items():
        key = f"{scope}:{field}"
        actual_value = actual.get(field)
        if actual_value == expected_value:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(
                f"{key}: expected {expected_value!r}, got {actual_value!r}"
            )


def _record_current_baseline(checks, findings, baseline):
    _record_mapping_contract(
        checks, findings, "current_baseline", baseline, CURRENT_BASELINE_TOP_LEVEL
    )
    _record_mapping_contract(
        checks,
        findings,
        "current_baseline:common_interfaces",
        baseline.get("common_interfaces") or {},
        CURRENT_COMMON_INTERFACES,
    )
    _record_mapping_contract(
        checks,
        findings,
        "current_baseline:shared_pipeline_policy",
        baseline.get("shared_pipeline_policy") or {},
        CURRENT_SHARED_PIPELINE_POLICY,
    )
    _record_mapping_contract(
        checks,
        findings,
        "current_baseline:review_request",
        baseline.get("review_request") or {},
        CURRENT_REVIEW_REQUEST,
    )


def _record_current_convergence(checks, findings, convergence):
    _record_tokens(
        checks,
        findings,
        "current_convergence",
        convergence,
        CURRENT_CONVERGENCE_REQUIRED,
    )


def validate() -> dict:
    result = _legacy.validate()
    checks = dict(result.get("checks") or {})
    findings = []
    for item in result.get("findings") or []:
        if not _is_obsolete_legacy_finding(item):
            findings.append(item)
    for key in list(checks):
        if _is_obsolete_legacy_check(key):
            checks.pop(key, None)

    try:
        baseline = json.loads(BASELINE.read_text())
        _record_current_baseline(checks, findings, baseline)
    except Exception as exc:
        checks["current_baseline:load"] = "FIX_REQUIRED"
        findings.append(f"current_baseline:load: {exc!r}")

    try:
        convergence = CONVERGENCE.read_text()
        _record_current_convergence(checks, findings, convergence)
    except Exception as exc:
        checks["current_convergence:load"] = "FIX_REQUIRED"
        findings.append(f"current_convergence:load: {exc!r}")

    for name in REQUIRED_FILES:
        path = ROOT / name
        key = f"final:file:{name}"
        if not path.is_file():
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")
            continue
        checks[key] = "PASS"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[f"final:compile:{name}"] = "PASS"
        except Exception as exc:
            checks[f"final:compile:{name}"] = "FIX_REQUIRED"
            findings.append(f"final:compile:{name}: {exc!r}")

    model_legacy = (ROOT / "model_legacy_v1.py").read_text()
    model_wrapper = (ROOT / "model.py").read_text()
    arbitration = (ROOT / "request_arbitration_v6.py").read_text()
    publisher_legacy = (ROOT / "publisher_legacy_v1.py").read_text()
    publisher_wrapper = (ROOT / "publisher.py").read_text()
    t2_legacy = (ROOT / "t2_legacy_v1.py").read_text()
    t2_wrapper = (ROOT / "t2.py").read_text()

    _record_tokens(checks, findings, "final:model_legacy", model_legacy, MODEL_LEGACY_REQUIRED)
    _record_tokens(checks, findings, "final:model_wrapper", model_wrapper, MODEL_WRAPPER_REQUIRED)
    _record_tokens(checks, findings, "final:request_arbitration", arbitration, ARBITRATION_REQUIRED)
    _record_tokens(checks, findings, "final:publisher_legacy", publisher_legacy, PUBLISHER_LEGACY_REQUIRED)
    _record_forbidden(checks, findings, "final:publisher_legacy", publisher_legacy, LEGACY_FORBIDDEN)
    _record_tokens(checks, findings, "final:publisher_wrapper", publisher_wrapper, PUBLISHER_WRAPPER_REQUIRED)
    _record_tokens(checks, findings, "final:t2_legacy", t2_legacy, T2_LEGACY_REQUIRED)
    _record_forbidden(checks, findings, "final:t2_legacy", t2_legacy, LEGACY_FORBIDDEN)
    _record_tokens(checks, findings, "final:t2_wrapper", t2_wrapper, T2_WRAPPER_REQUIRED)

    dispatcher_test = (ROOT / "test_dispatcher.py").read_text()
    _record_tokens(checks, findings, "final:dispatcher_compat", dispatcher_test, (
        "class HardeningTests(_legacy.HardeningTests)",
        "self.assertEqual(cid, 10)",
    ))

    replay_test = (ROOT / "test_integrated_resilience_convergence_v1.py").read_text()
    _record_tokens(checks, findings, "final:actual_public_path_replay", replay_test, (
        "from automation.review_dispatcher_v1 import model, publisher, t2",
        "model.latest_exact_current_owner_request(",
        "publisher.publish(",
        "t2.publish_t2(",
        "mock.patch.object(publisher",
        "mock.patch.object(t2",
    ))

    matrix_path = REPO_ROOT / "docs" / "lane_b_completion_matrix_v1.json"
    exit_path = REPO_ROOT / "docs" / "lane_b_completion_exit_gate_v1.md"
    for path in (matrix_path, exit_path):
        key = f"final:completion:{path.name}"
        if path.is_file():
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")
    if matrix_path.is_file():
        try:
            matrix = json.loads(matrix_path.read_text())
            if (
                matrix.get("schema") == "MULTIVERSE_LANE_B_COMPLETION_MATRIX_v1"
                and len(matrix.get("rows") or []) == 11
                and any(row.get("id") == "combined_fault_replay" for row in matrix.get("rows") or [])
            ):
                checks["final:completion:matrix_contract"] = "PASS"
            else:
                raise ValueError("matrix contract")
        except Exception as exc:
            checks["final:completion:matrix_contract"] = "FIX_REQUIRED"
            findings.append(f"final:completion:matrix_contract: {exc!r}")

    result = dict(result)
    result["checks"] = checks
    result["findings"] = findings
    result["verdict"] = "PASS" if not findings else "FIX_REQUIRED"
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
