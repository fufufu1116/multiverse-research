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
    "_original_fresh_verify = _legacy._fresh_verify",
    "_legacy._fresh_verify = _fresh_verify",
)

FRESHNESS_REQUIRED = (
    "latest_exact_current_owner_request(",
    'request_comment == job["request_comment"]',
    'request_sha256 == job["request_sha256"]',
    'request == job["request"]',
    "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT",
    "PUBLISH_REQUEST_NO_LONGER_CANONICAL_SHA256",
    "PUBLISH_REQUEST_NO_LONGER_CANONICAL_BODY",
)


def _required(
    checks: dict[str, str],
    findings: list[str],
    scope: str,
    source: str,
    token: str,
) -> None:
    name = f"{scope}:required:{token[:32]}"
    if token in source:
        checks[name] = "PASS"
    else:
        checks[name] = "FIX_REQUIRED"
        findings.append(f"{name}: missing")


def _forbidden(
    checks: dict[str, str],
    findings: list[str],
    scope: str,
    source: str,
    token: str,
) -> None:
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
        ROOT / "validator_legacy_v1.py",
    )
    for path in required_files:
        name = f"publisher_freshness:file:{path.name}"
        if path.is_file():
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    for path in (
        ROOT / "publisher.py",
        ROOT / "publisher_legacy_v1.py",
        ROOT / "publisher_freshness_v1.py",
        ROOT / "test_publisher_freshness_v1.py",
        ROOT / "validator.py",
        ROOT / "validator_legacy_v1.py",
    ):
        name = f"publisher_freshness:compile:{path.name}"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[name] = "PASS"
        except Exception as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc!r}")

    legacy_source = (ROOT / "publisher_legacy_v1.py").read_text()
    for token in PUBLISHER_LEGACY_REQUIRED:
        _required(
            checks,
            findings,
            "publisher_legacy",
            legacy_source,
            token,
        )
    for token in PUBLISHER_LEGACY_FORBIDDEN:
        _forbidden(
            checks,
            findings,
            "publisher_legacy",
            legacy_source,
            token,
        )

    wrapper_source = (ROOT / "publisher.py").read_text()
    for token in WRAPPER_REQUIRED:
        _required(checks, findings, "publisher_wrapper", wrapper_source, token)

    freshness_source = (ROOT / "publisher_freshness_v1.py").read_text()
    for token in FRESHNESS_REQUIRED:
        _required(checks, findings, "publisher_freshness", freshness_source, token)

    result = dict(result)
    result["checks"] = checks
    result["findings"] = findings
    result["verdict"] = "PASS" if not findings else "FIX_REQUIRED"
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
