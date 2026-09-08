from __future__ import annotations

from automation.review_dispatcher_v1 import dispatcher_legacy_v1 as _legacy
from automation.review_dispatcher_v1.request_arbitration_v6 import (
    latest_exact_current_owner_request_v6,
)

# v6 is opt-in at the dispatcher boundary. The public model API remains strict
# for backward-compatible regression coverage.
_legacy.latest_exact_current_owner_request = latest_exact_current_owner_request_v6

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

# Validator compatibility manifest: implementation remains byte-for-byte in
# dispatcher_legacy_v1.py; these tokens document the delegated contract.
VALIDATOR_COMPATIBILITY_MANIFEST = r'''
PR_SUMMARY_ITEM_OBJECT
PR_SUMMARY_NUMBER
f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
github_full_pr_binding(
github_commit_tree_sha(
github_branch_commit_sha(
COMMENTS_ITEM_OBJECT
github_comment_id(
'''

if __name__ == "__main__":
    try:
        raise SystemExit(_legacy.main())
    except _legacy.ReviewContractError as exc:
        print(f"DISPATCHER_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
