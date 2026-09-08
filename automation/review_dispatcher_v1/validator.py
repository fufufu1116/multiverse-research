from __future__ import annotations

import json
from pathlib import Path

from automation.review_dispatcher_v1 import validator_legacy_v1 as _legacy

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

LEGACY_MODEL_TOKENS = (
    "supersedes_request_sha256",
    "SAME_HEAD_SUPERSESSION_CHAIN_INVALID",
    "sha256_json(request)",
    "def github_full_pr_binding(",
    "PR_DRAFT_BOOL",
    "PR_MERGED_BOOL",
    "PR_HEAD_SHA",
    "PR_BASE_SHA",
    "def github_commit_tree_sha(",
    "COMMIT_TREE_SHA",
    "def github_branch_commit_sha(",
    "BRANCH_COMMIT_SHA",
    "def github_comment_id(",
    "PAGINATED_RESPONSE_ITEM_NOT_OBJECT",
    "def lane_result_outer_app_trusted(",
    "if app is None:",
    "return lane_result_outer_app_trusted(comment, lane)",
)

WRAPPER_TOKENS = (
    "from automation.review_dispatcher_v1 import model_legacy_v1 as _legacy",
    "exact_current_owner_requests_v6",
    "latest_exact_current_owner_request_v6",
)

ARBITRATION_TOKENS = (
    "generations.setdefault(predecessor, []).append",
    "winner = generation[0]",
    "SUPERSESSION_COMMENT_ORDER_INVALID",
    "ORPHANED_OR_LOER_DERIVED_SUPERSESSION",
    "DUPLICATE_EXACT_REQUEST_ID",
)

# Backward-compatible spelling for the actual v6 source token.
ARBITRATION_REQUIRED_ALTERNATIVES = {
    "ORPHANED_OR_LOER_DERIVED_SUPERSESSION": (
        "ORPHANED_OR_LOER_DERIVED_SUPERSESSION",
        "ORPHANED_OR_LOSER_DERIVED_SUPERSESSION",
    )
}


def _record_token(
    checks: dict[str, str],
    findings: list[str],
    *,
    scope: str,
    source: str,
    token: str,
) -> None:
    name = f"{scope}:{token[:32]}"
    alternatives = ARBITRATION_REQUIRED_ALTERNATIVES.get(token, (token,))
    if any(item in source for item in alternatives):
        checks[name] = "PASS"
    else:
        checks[name] = "FIX_REQUIRED"
        findings.append(f"{name}: missing")


def validate() -> dict:
    result = _legacy.validate()
    checks = dict(result.get("checks") or {})
    findings = [
        item
        for item in (result.get("findings") or [])
        if not item.startswith("model:request_identity:")
    ]
    for name in list(checks):
        if name.startswith("model:request_identity:"):
            del checks[name]

    required_files = (
        ROOT / "model_legacy_v1.py",
        ROOT / "request_arbitration_v6.py",
        ROOT / "test_request_arbitration_v6.py",
        ROOT / "test_dispatcher_legacy_v1.py",
        ROOT / "validator_legacy_v1.py",
    )
    for path in required_files:
        name = f"v6:file:{path.name}"
        if path.is_file():
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: missing")

    for path in (
        ROOT / "model.py",
        ROOT / "model_legacy_v1.py",
        ROOT / "request_arbitration_v6.py",
        ROOT / "test_request_arbitration_v6.py",
        ROOT / "test_dispatcher.py",
        ROOT / "test_dispatcher_legacy_v1.py",
        ROOT / "validator.py",
        ROOT / "validator_legacy_v1.py",
    ):
        name = f"v6:compile:{path.name}"
        try:
            compile(path.read_text(), str(path), "exec")
            checks[name] = "PASS"
        except Exception as exc:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {exc!r}")

    legacy_source = (ROOT / "model_legacy_v1.py").read_text()
    for token in LEGACY_MODEL_TOKENS:
        _record_token(
            checks,
            findings,
            scope="model_legacy:request_identity",
            source=legacy_source,
            token=token,
        )

    wrapper_source = (ROOT / "model.py").read_text()
    for token in WRAPPER_TOKENS:
        _record_token(
            checks,
            findings,
            scope="model_wrapper:v6",
            source=wrapper_source,
            token=token,
        )

    arbitration_source = (ROOT / "request_arbitration_v6.py").read_text()
    for token in ARBITRATION_TOKENS:
        _record_token(
            checks,
            findings,
            scope="request_arbitration_v6",
            source=arbitration_source,
            token=token,
        )

    test_wrapper = (ROOT / "test_dispatcher.py").read_text()
    for token in (
        "class HardeningTests(_legacy.HardeningTests)",
        "self.assertEqual(cid, 10)",
        'self.assertEqual(request["request_id"], "first-chain")',
    ):
        _record_token(
            checks,
            findings,
            scope="test_dispatcher:v6_compat",
            source=test_wrapper,
            token=token,
        )

    result = dict(result)
    result["checks"] = checks
    result["findings"] = findings
    result["verdict"] = "PASS" if not findings else "FIX_REQUIRED"
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
