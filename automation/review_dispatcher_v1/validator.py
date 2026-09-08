from __future__ import annotations

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
PUBLISHER_WRAPPER_REQUIRED = (
    "assert_job_request_still_canonical(",
    "assert_published_result_is_canonical(",
    "recover_publish_receipt(",
)
T2_LEGACY_REQUIRED = (
    "github_full_pr_binding(",
    "github_commit_tree_sha(",
    "github_branch_commit_sha(",
    "github_comment_id(",
    "required_positive_int(",
    'lane_result_outer_app_trusted(auditor_comment, "AUDITOR")',
    'lane_result_outer_app_trusted(lab_comment, "LAB")',
)
T2_LEGACY_FORBIDDEN = (
    'pr["merged"]',
    'pr["draft"]',
    'pr["state"]',
    'pr["head"]',
    'pr["base"]',
    'commit["commit"]',
    'main["commit"]',
    'int(item["id"])',
    "comment['id']",
    'result["id"]',
    'receipt["published_comment_id"]',
    "outer_app == AUDITOR_APP_SLUG",
    "lab_app == LAB_APP_SLUG",
)
T2_WRAPPER_REQUIRED = (
    "assert_referenced_result_is_canonical(",
    "assert_published_t2_is_canonical(",
    "recover_t2_receipt(",
    "_filter_noncanonical_lab_duplicates(",
    "_recover_existing_t2(",
    "EXISTING_T2_RACE_WITHOUT_CANONICAL_RECOVERY",
)
ARCH_FILES = (
    "publisher_legacy_v1.py",
    "publisher_freshness_v1.py",
    "receipt_recovery_v1.py",
    "result_canonicalization_v1.py",
    "t2_legacy_v1.py",
    "t2_idempotence_v1.py",
    "t2_receipt_recovery_v1.py",
    "combined_fault_replay_v1.py",
)


def _record_tokens(checks, findings, *, scope, source, tokens):
    for token in tokens:
        key = f"{scope}:{token[:32]}"
        if token in source:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")


def _record_forbidden(checks, findings, *, scope, source, tokens):
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
    for item in result.get("findings") or []:
        if item.startswith("publisher:api_contract:"):
            continue
        if item.startswith("publisher:no_raw_external_index:"):
            continue
        if item.startswith("t2:api_contract:"):
            continue
        if item.startswith("t2:no_raw_external_index:"):
            continue
        findings.append(item)
    for key in list(checks):
        if (
            key.startswith("publisher:api_contract:")
            or key.startswith("publisher:no_raw_external_index:")
            or key.startswith("t2:api_contract:")
            or key.startswith("t2:no_raw_external_index:")
        ):
            checks.pop(key, None)

    for name in ARCH_FILES:
        path = ROOT / name
        key = f"integrated_arch:file:{name}"
        if not path.is_file():
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")
            continue
        checks[key] = "PASS"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[f"integrated_arch:compile:{name}"] = "PASS"
        except Exception as exc:
            checks[f"integrated_arch:compile:{name}"] = "FIX_REQUIRED"
            findings.append(f"integrated_arch:compile:{name}: {exc!r}")

    publisher_legacy = (ROOT / "publisher_legacy_v1.py").read_text()
    t2_legacy = (ROOT / "t2_legacy_v1.py").read_text()

    _record_tokens(checks, findings, scope="integrated:publisher_legacy", source=publisher_legacy, tokens=PUBLISHER_LEGACY_REQUIRED)
    _record_forbidden(checks, findings, scope="integrated:publisher_legacy", source=publisher_legacy, tokens=PUBLISHER_LEGACY_FORBIDDEN)
    _record_tokens(checks, findings, scope="integrated:publisher_wrapper", source=(ROOT / "publisher.py").read_text(), tokens=PUBLISHER_WRAPPER_REQUIRED)
    _record_tokens(checks, findings, scope="integrated:t2_legacy", source=t2_legacy, tokens=T2_LEGACY_REQUIRED)
    _record_forbidden(checks, findings, scope="integrated:t2_legacy", source=t2_legacy, tokens=T2_LEGACY_FORBIDDEN)
    _record_tokens(checks, findings, scope="integrated:t2_wrapper", source=(ROOT / "t2.py").read_text(), tokens=T2_WRAPPER_REQUIRED)

    replay_source = (ROOT / "combined_fault_replay_v1.py").read_text()
    for token in ("canonical_result", "canonical_t2", "receipt"):
        key = f"integrated:replay:{token}"
        if token in replay_source:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")

    result["checks"] = checks
    result["findings"] = findings
    result["verdict"] = "PASS" if not findings else "FIX_REQUIRED"
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(validate(), sort_keys=True))
