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


def discover_pr(repo: str, head: str, fetch=github_get) -> dict[str, Any]:
    pulls = fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/commits/{head}/pulls",
    )
    exact = [
        item
        for item in pulls
        if item.get("state") == "open"
        and (item.get("head") or {}).get("sha") == head
    ]
    require(len(exact) == 1, f"EXACT_OPEN_PR_COUNT:{len(exact)}")
    return exact[0]


def discover_request(
    *,
    repo: str,
    lane: str,
    head: str,
    fetch=github_get,
) -> dict[str, Any]:
    pr = discover_pr(repo, head, fetch=fetch)
    pr_number = int(pr["number"])

    commit = fetch(
        f"https://api.github.com/repos/{repo}/commits/{head}"
    )
    tree = commit["commit"]["tree"]["sha"]

    main = fetch(
        f"https://api.github.com/repos/{repo}/branches/main"
    )
    main_sha = main["commit"]["sha"]

    comments = fetch_all_pages(
        fetch,
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
    )

    request_comment, request, comment = latest_exact_current_owner_request(
        comments,
        repo=repo,
        pr=pr_number,
        lane=lane,
        head=head,
        tree=tree,
        base=pr["base"]["sha"],
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
    duplicate_ids = [
        int(item["id"])
        for item in comments
        if marker in (item.get("body") or "")
        and lane_result_comment_trusted(item, lane)
    ]
    require(
        not duplicate_ids,
        "CURRENT_REQUEST_RESULT_ALREADY_EXISTS:"
        + ",".join(str(i) for i in duplicate_ids),
    )

    require(pr["draft"] is True, "PR_NOT_DRAFT")
    require(pr["merged"] is False, "PR_ALREADY_MERGED")
    require(pr["state"] == "open", "PR_NOT_OPEN")

    return {
        "schema": JOB_SCHEMA,
        "repo": repo,
        "pr": pr_number,
        "branch": (pr.get("head") or {}).get("ref"),
        "head": head,
        "tree": tree,
        "base": pr["base"]["sha"],
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
