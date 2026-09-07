from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    fetch_all_pages,
    lane_result_comment_trusted,
    latest_exact_current_owner_request,
    require,
    result_marker,
    sha256_json,
    sha40,
    validate_request,
)

JOB_SCHEMA = "MULTIVERSE_FIXED_REVIEW_JOB_v1"


def github_get(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "multiverse-fixed-review-dispatcher-v1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def _required_object(value: Any, code: str) -> dict[str, Any]:
    require(isinstance(value, dict), code)
    return value


def _required_positive_int(value: Any, code: str) -> int:
    require(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0,
        code,
    )
    return value


def _required_sha(value: Any, code: str) -> str:
    require(sha40(value), code)
    return value


def _required_nonempty_str(value: Any, code: str) -> str:
    require(isinstance(value, str) and bool(value), code)
    return value


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
    pr_number = _required_positive_int(
        summary.get("number"),
        "PR_SUMMARY_NUMBER",
    )

    full_pr_raw = fetch(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    full_pr = _required_object(full_pr_raw, "PR_RESPONSE_OBJECT")

    full_number = _required_positive_int(
        full_pr.get("number"),
        "PR_NUMBER",
    )
    require(full_number == pr_number, "PR_NUMBER_DRIFT")

    state = _required_nonempty_str(
        full_pr.get("state"),
        "PR_STATE_STRING",
    )
    require(state == "open", "PR_NOT_OPEN")

    draft = full_pr.get("draft")
    require(isinstance(draft, bool), "PR_DRAFT_BOOL")
    require(draft is True, "PR_NOT_DRAFT")

    merged = full_pr.get("merged")
    require(isinstance(merged, bool), "PR_MERGED_BOOL")
    require(merged is False, "PR_ALREADY_MERGED")

    head_obj = _required_object(
        full_pr.get("head"),
        "PR_HEAD_OBJECT",
    )
    head_sha = _required_sha(
        head_obj.get("sha"),
        "PR_HEAD_SHA",
    )
    require(head_sha == head, "PR_HEAD_DRIFT")
    head_ref = _required_nonempty_str(
        head_obj.get("ref"),
        "PR_HEAD_REF",
    )

    base_obj = _required_object(
        full_pr.get("base"),
        "PR_BASE_OBJECT",
    )
    base_sha = _required_sha(
        base_obj.get("sha"),
        "PR_BASE_SHA",
    )

    return {
        "number": pr_number,
        "state": state,
        "draft": draft,
        "merged": merged,
        "head_sha": head_sha,
        "head_ref": head_ref,
        "base_sha": base_sha,
    }


def _discover_tree_sha(repo: str, head: str, fetch=github_get) -> str:
    commit_raw = fetch(
        f"https://api.github.com/repos/{repo}/commits/{head}"
    )
    commit = _required_object(
        commit_raw,
        "COMMIT_RESPONSE_OBJECT",
    )
    commit_meta = _required_object(
        commit.get("commit"),
        "COMMIT_METADATA_OBJECT",
    )
    tree_obj = _required_object(
        commit_meta.get("tree"),
        "COMMIT_TREE_OBJECT",
    )
    return _required_sha(
        tree_obj.get("sha"),
        "COMMIT_TREE_SHA",
    )


def _discover_main_sha(repo: str, fetch=github_get) -> str:
    main_raw = fetch(
        f"https://api.github.com/repos/{repo}/branches/main"
    )
    main = _required_object(
        main_raw,
        "MAIN_RESPONSE_OBJECT",
    )
    main_commit = _required_object(
        main.get("commit"),
        "MAIN_COMMIT_OBJECT",
    )
    return _required_sha(
        main_commit.get("sha"),
        "MAIN_SHA",
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
                _required_positive_int(
                    item.get("id"),
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
