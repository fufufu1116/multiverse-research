from __future__ import annotations

from typing import Any

from automation.review_dispatcher_v1 import publisher as _publisher
from automation.review_dispatcher_v1.main_drift_runtime_v1 import (
    assert_dispatcher_ref_on_live_chain,
    assert_job_main_binding_fresh,
    assert_job_request_latest_across_snapshots,
)


def _fresh_verify(job: dict[str, Any]) -> list[dict[str, Any]]:
    legacy = _publisher._legacy
    fetch = _publisher._bounded_public_github
    repo = job["repo"]
    pr_number = job["pr"]

    pr = legacy.github_full_pr_binding(
        fetch(f"https://api.github.com/repos/{repo}/pulls/{pr_number}"),
        expected_number=pr_number,
        expected_head=job["head"],
    )
    live_main = legacy.github_branch_commit_sha(
        fetch(f"https://api.github.com/repos/{repo}/branches/main")
    )
    tree_sha = legacy.github_commit_tree_sha(
        fetch(f"https://api.github.com/repos/{repo}/commits/{job['head']}")
    )
    request_comment = legacy.required_object(
        fetch(
            f"https://api.github.com/repos/{repo}/issues/comments/"
            f"{job['request_comment']}"
        ),
        "REQUEST_COMMENT_RESPONSE_OBJECT",
    )

    legacy.require(pr["base_sha"] == job["base"], "BASE_DRIFT")
    legacy.require(tree_sha == job["tree"], "TREE_DRIFT")

    assert_job_main_binding_fresh(
        job,
        live_main=live_main,
        fetch=fetch,
    )
    assert_dispatcher_ref_on_live_chain(
        job,
        live_main=live_main,
        fetch=fetch,
    )

    parsed = legacy.extract_request_from_comment(
        request_comment.get("body") or ""
    )
    legacy.require(parsed is not None, "REQUEST_COMMENT_NOT_PARSEABLE")
    legacy.validate_request(parsed)
    legacy.require(parsed == job["request"], "REQUEST_COMMENT_DRIFT")
    legacy.require(
        job.get("request_sha256") == legacy.sha256_json(parsed),
        "REQUEST_SHA256_DRIFT",
    )
    legacy.require(
        legacy.issue_comment_owner_trusted(request_comment, repo),
        "REQUEST_COMMENT_PRODUCER_NOT_OWNER",
    )

    comments = legacy.fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )
    assert_job_request_latest_across_snapshots(
        job,
        comments,
        live_main=live_main,
    )
    return comments


# The current publisher wrapper calls its own global `_fresh_verify`, while its
# saved legacy publish function resolves `_legacy._fresh_verify` dynamically.
# Patch both edges so every pre-write and post-write freshness pass uses the
# same fail-closed main-drift semantics.
_publisher._fresh_verify = _fresh_verify
_publisher._legacy._fresh_verify = _fresh_verify


def main() -> int:
    return _publisher.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        _publisher._legacy.ReviewContractError,
        _publisher._legacy.GitHubAppError,
    ) as exc:
        print(f"PUBLISH_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
