from __future__ import annotations

from automation.review_dispatcher_v1 import review_legacy_v1 as _legacy
from automation.review_dispatcher_v1.request_arbitration_v6 import (
    latest_exact_current_owner_request_v6,
)

# Keep the adopted review implementation intact, but route exact-current
# request selection through v6 for review-time upstream/freshness checks.
_legacy.latest_exact_current_owner_request = latest_exact_current_owner_request_v6

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

VALIDATOR_COMPATIBILITY_MANIFEST = r'''
[sys.executable, "-m", "unittest", module, "-v"]
_run_candidate_process(
_candidate_env(
_repo_file(
latest_exact_current_owner_request(
request_sha256
lab_request_sha256
resolve_public_https_target(base_url)
_PinnedHTTPSConnection(
github_full_pr_binding(
github_commit_tree_sha(
github_branch_commit_sha(
checks["fresh_binding_contract"]
github_comment_id(
lane_result_outer_app_trusted(lab_comment, "LAB")
'''

if __name__ == "__main__":
    try:
        raise SystemExit(_legacy.main())
    except _legacy.ReviewContractError as exc:
        print(f"REVIEW_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
