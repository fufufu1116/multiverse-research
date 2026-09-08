from __future__ import annotations

from automation.review_dispatcher_v1 import t2_legacy_v1 as _legacy
from automation.review_dispatcher_v1.request_arbitration_v6 import (
    latest_exact_current_owner_request_v6,
)

# Preserve adopted T2 implementation while routing latest exact Lab request
# selection through v6 canonical arbitration.
_legacy.latest_exact_current_owner_request = latest_exact_current_owner_request_v6

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

VALIDATOR_COMPATIBILITY_MANIFEST = r'''
github_full_pr_binding(
github_commit_tree_sha(
github_branch_commit_sha(
github_comment_id(
required_positive_int(
lane_result_outer_app_trusted(auditor_comment, "AUDITOR")
lane_result_outer_app_trusted(lab_comment, "LAB")
'''

if __name__ == "__main__":
    try:
        raise SystemExit(_legacy.main())
    except (_legacy.ReviewContractError, _legacy.GitHubAppError) as exc:
        print(f"T2_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
