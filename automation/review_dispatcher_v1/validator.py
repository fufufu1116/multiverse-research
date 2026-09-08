from __future__ import annotations

from pathlib import Path

from automation.review_dispatcher_v1 import validator_legacy_v1 as _legacy

ROOT = Path(__file__).resolve().parent

LEGACY_T2_REQUIRED = (
    "github_full_pr_binding(",
    "github_commit_tree_sha(",
    "github_branch_commit_sha(",
    "github_comment_id(",
    "required_positive_int(",
    'lane_result_outer_app_trusted(auditor_comment, "AUDITOR")',
    'lane_result_outer_app_trusted(lab_comment, "LAB")',
)

WRAPPER_REQUIRED = (
    "assert_referenced_result_is_canonical(",
    "assert_published_t2_is_canonical(",
    "recover_t2_receipt(",
    "_filter_noncanonical_lab_duplicates(",
    "_recover_existing_t2(",
    "EXISTING_T2_RACE_WITHOUT_CANONICAL_RECOVERY",
)

HELPER_FILES = (
    "t2_legacy_v1.py",
    "t2_idempotence_v1.py",
    "t2_receipt_recovery_v1.py",
)


def validate() -> dict:
    result = _legacy.validate()
    checks = dict(result.get("checks") or {})
    findings = [
        item
        for item in (result.get("findings") or [])
        if not (
            item.startswith("t2:api_contract:")
            or item.startswith("t2:no_raw_external_index:")
        )
    ]
    for key in list(checks):
        if key.startswith("t2:api_contract:") or key.startswith("t2:no_raw_external_index:"):
            checks.pop(key, None)

    for name in HELPER_FILES:
        path = ROOT / name
        key = f"t2_arch:file:{name}"
        if path.is_file():
            checks[key] = "PASS"
            try:
                compile(path.read_text(), str(path), "exec")
                checks[f"t2_arch:compile:{name}"] = "PASS"
            except Exception as exc:
                checks[f"t2_arch:compile:{name}"] = "FIX_REQUIRED"
                findings.append(f"t2_arch:compile:{name}: {exc!r}")
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")

    legacy_source = (ROOT / "t2_legacy_v1.py").read_text()
    for token in LEGACY_T2_REQUIRED:
        key = f"t2_arch:legacy:{token[:32]}"
        if token in legacy_source:
            checks[key] = "PASS"
        else:
            checks[key] = "FIX_REQUIRED"
            findings.append(f"{key}: missing")

    wrapper_source = (ROOT / "t2.py").read_text()
    for token in WRAPPER_REQUIRED:
        key = f"t2_arch:wrapper:{token[:32]}"
        if token in wrapper_source:
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
