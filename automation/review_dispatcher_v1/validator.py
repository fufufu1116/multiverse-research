from __future__ import annotations

import json
from pathlib import Path

from automation.review_dispatcher_v1 import validator_legacy_v1 as _legacy

ROOT = Path(__file__).resolve().parent

PUBLISHER_LEGACY_REQUIRED = (
    "github_full_pr_binding(",
    "github_commit_tree_sha(",
    "github_branch_commit_sha(",
    "github_comment_id(",
)

PUBLISHER_LEGACY_FORBIDDEN = (
    'pr["merged"]',
    'pr["draft"]',
    'pr["state"]',
    'pr["head"]',
    'pr["base"]',
    'commit["commit"]',
    'main["commit"]',
    "comment['id']",
    'result["id"]',
)

WRAPPER_REQUIRED = (
    "from automation.review_dispatcher_v1 import publisher_legacy_v1 as _legacy",
    "assert_job_request_still_canonical",
    "recover_publish_receipt",
    "assert_published_result_is_canonical",
    "canonical_result_comment_id",
    "_original_publish = _legacy.publish",
    "def _validate_recovery_artifact(job, artifact):",
    '"reviewed_base": job["base"]',
    "RECOVERY_LEGACY_BINDING_PRODUCER_LOGIN",
    "CURRENT_REQUEST_RESULT_ALREADY_EXISTS:",
    "EXISTING_RESULT_RACE_WITHOUT_CANONICAL_RECOVERY",
    "_legacy._fresh_verify = _fresh_verify",
    "_legacy.publish = publish",
)


def _required(checks, findings, scope, source, token):
    name = f"{scope}:required:{token[:32]}"
    if token in source:
        checks[name] = "PASS"
    else:
        checks[name] = "FIX_REQUIRED"
        findings.append(f"{name}: missing")


def _forbidden(checks, findings, scope, source, token):
    name = f"{scope}:forbidden:{token}"
    if token not in source:
        checks[name] = "PASS"
    else:
        checks[name] = "FIX_REQUIRED"
        findings.append(f"{name}: found")


def validate() -> dict:
    result = _legacy.validate()
    checks = dict(result.get("checks") or {})
    findings = [
        item
        for item in (result.get("findings") or [])
        if not item.startswith("publisher:api_contract:")
        and not item.startswith("publisher:no_raw_external_index:")
    ]
    for name in list(checks):
        if name.startswith("publisher:api_contract:") or name.startswith(
            "publisher:no_raw_external_index:"
        ):
            del checks[name]

    required_files = (
        ROOT / "publisher_legacy_v1.py",
        ROOT / "publisher_freshness_v1.py",
        ROOT / "result_canonicalization_v1.py",
        ROOT / "receipt_recovery_v1.py",
        ROOT / "test_publisher_freshness_v1.py",
        ROOT / "test_result_canonicalization_v1.py",
        ROOT / "test_receipt_recovery_v1.py",
        ROOT / "test_publisher_resilience_integration_v1.py",
        ROOT / "validator_legacy_v1.py",
    )
    for path in required_files:
        name = f"publisher_resilience:file:{path.name}"
        if path.is_file():
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    for path in (
        ROOT / "publisher.py",
        *required_files,
        ROOT / "validator.py",
    ):
        name = f"publisher_resilience:compile:{path.name}"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[name] = "PASS"
        except Exception as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc!r}")

    legacy_source = (ROOT / "publisher_legacy_v1.py").read_text()
    for token in PUBLISHER_LEGACY_REQUIRED:
        _required(checks, findings, "publisher_legacy", legacy_source, token)
    for token in PUBLISHER_LEGACY_FORBIDDEN:
        _forbidden(checks, findings, "publisher_legacy", legacy_source, token)

    wrapper_source = (ROOT / "publisher.py").read_text()
    for token in WRAPPER_REQUIRED:
        _required(checks, findings, "publisher_resilience_wrapper", wrapper_source, token)

    helper_requirements = {
        "publisher_freshness_v1.py": (
            "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT",
            "PUBLISH_REQUEST_NO_LONGER_CANONICAL_SHA256",
            "PUBLISH_REQUEST_NO_LONGER_CANONICAL_BODY",
        ),
        "result_canonicalization_v1.py": (
            "return min(matching)",
            "NONCANONICAL_DUPLICATE_RESULT",
        ),
        "receipt_recovery_v1.py": (
            "RECOVERY_RESULT_ARTIFACT_DRIFT",
            '"recovered": True',
        ),
        "test_publisher_resilience_integration_v1.py": (
            "existing_canonical_result_recovers_without_republish",
            "later_duplicate_cannot_emit_successful_receipt",
            "post_publish_request_supersession_fails_closed",
            "recovery_rechecks_legacy_base_binding",
        ),
    }
    for filename, tokens in helper_requirements.items():
        source = (ROOT / filename).read_text()
        for token in tokens:
            _required(checks, findings, filename, source, token)

    result = dict(result)
    result["checks"] = checks
    result["findings"] = findings
    result["verdict"] = "PASS" if not findings else "FIX_REQUIRED"
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
