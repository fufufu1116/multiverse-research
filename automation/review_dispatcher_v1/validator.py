from __future__ import annotations

import json
from pathlib import Path

from automation.review_dispatcher_v1 import validator_legacy_v1 as _legacy

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

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
    "validator_legacy_v1.py",
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


def validate() -> dict:
    result = _legacy.validate()
    checks = dict(result.get("checks") or {})
    findings = []
    obsolete_prefixes = (
        "model:request_identity:",
        "publisher:api_contract:", "publisher:no_raw_external_index:",
        "t2:api_contract:", "t2:no_raw_external_index:",
    )
    for item in result.get("findings") or []:
        if not item.startswith(obsolete_prefixes):
            findings.append(item)
    for key in list(checks):
        if key.startswith(obsolete_prefixes):
            checks.pop(key, None)

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
