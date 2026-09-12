from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from automation.review_dispatcher_v1.github_read_resilience_v1 import (
    github_json_read,
)
from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    fetch_all_pages,
    github_branch_commit_sha,
    github_comment_id,
    github_commit_tree_sha,
    github_full_pr_binding,
    lane_result_comment_trusted,
    latest_exact_current_owner_request,
    require,
    required_positive_int,
    result_marker,
    sha256_json,
    validate_request,
)

JOB_SCHEMA = "MULTIVERSE_FIXED_REVIEW_JOB_v1"


def github_get(url: str) -> Any:
    return github_json_read(
        url,
        user_agent="multiverse-fixed-review-dispatcher-v1",
    )


def discover_pr(repo: str, head: str, fetch=github_get) -> dict[str, Any]:
    pulls = fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/commits/{head}/pulls",
    )

    exact: list[dict[str, Any]] = []
    for item in pulls:
        require(isinstance(item, dict), "PR_SUMMARY_ITEM_OBJECT")
        item_head = item.get("head")
        if (
            item.get("state") == "open"
            and isinstance(item_head, dict)
            and item_head.get("sha") == head
        ):
            exact.append(item)

    require(len(exact) == 1, f"EXACT_OPEN_PR_COUNT:{len(exact)}")

    summary = exact[0]
    pr_number = required_positive_int(
        summary.get("number"),
        "PR_SUMMARY_NUMBER",
    )

    full_pr_raw = fetch(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    return github_full_pr_binding(
        full_pr_raw,
        expected_number=pr_number,
        expected_head=head,
    )


def _discover_tree_sha(repo: str, head: str, fetch=github_get) -> str:
    return github_commit_tree_sha(
        fetch(f"https://api.github.com/repos/{repo}/commits/{head}")
    )


def _discover_main_sha(repo: str, fetch=github_get) -> str:
    return github_branch_commit_sha(
        fetch(f"https://api.github.com/repos/{repo}/branches/main")
    )


def discover_request(
    *,
    repo: str,
    lane: str,
    head: str,
    fetch=github_get,
) -> dict[str, Any]:
    pr = discover_pr(repo, head, fetch=fetch)
    pr_number = pr["number"]
    tree = _discover_tree_sha(repo, head, fetch=fetch)
    main_sha = _discover_main_sha(repo, fetch=fetch)

    comments = fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )
    require(
        all(isinstance(item, dict) for item in comments),
        "COMMENTS_ITEM_OBJECT",
    )

    request_comment, request, comment = latest_exact_current_owner_request(
        comments,
        repo=repo,
        pr=pr_number,
        lane=lane,
        head=head,
        tree=tree,
        base=pr["base_sha"],
        main=main_sha,
    )
    validate_request(request)
    request_sha256 = sha256_json(request)

    marker = result_marker(
        request["request_id"],
        head,
        request_comment,
        request_sha256,
    )

    duplicate_ids: list[int] = []
    for item in comments:
        if (
            marker in (item.get("body") or "")
            and lane_result_comment_trusted(item, lane)
        ):
            duplicate_ids.append(
                github_comment_id(
                    item,
                    "RESULT_COMMENT_ID",
                )
            )

    require(
        not duplicate_ids,
        "CURRENT_REQUEST_RESULT_ALREADY_EXISTS:"
        + ",".join(str(i) for i in duplicate_ids),
    )

    return {
        "schema": JOB_SCHEMA,
        "repo": repo,
        "pr": pr_number,
        "branch": pr["head_ref"],
        "head": head,
        "tree": tree,
        "base": pr["base_sha"],
        "main": main_sha,
        "lane": lane,
        "request_id": request["request_id"],
        "request_comment": request_comment,
        "request_sha256": request_sha256,
        "request_comment_author": (comment.get("user") or {}).get("login"),
        "request": request,
        "dispatcher_ref": os.environ.get(
            "MULTIVERSE_DISPATCHER_REF",
            "",
        ),
    }


def write_job(job: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(
            job,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lane",
        required=True,
        choices=("LAB", "AUDITOR"),
    )
    parser.add_argument(
        "--repo",
        default="fufufu1116/multiverse-research",
    )
    parser.add_argument(
        "--head",
        default=None,
    )
    parser.add_argument(
        "--output",
        default="review_job.json",
    )
    args = parser.parse_args()

    head = (
        args.head
        or os.environ.get("BUILDKITE_COMMIT")
        or ""
    )
    require(bool(head), "BUILD_COMMIT_REQUIRED")

    job = discover_request(
        repo=args.repo,
        lane=args.lane,
        head=head,
    )
    write_job(job, args.output)

    print(
        json.dumps(
            {
                "schema": JOB_SCHEMA,
                "request_id": job["request_id"],
                "request_comment": job["request_comment"],
                "request_sha256": job["request_sha256"],
                "lane": job["lane"],
                "pr": job["pr"],
                "head": job["head"],
                "tree": job["tree"],
                "main": job["main"],
                "dispatcher_ref": job["dispatcher_ref"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewContractError as exc:
        print(f"DISPATCHER_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
