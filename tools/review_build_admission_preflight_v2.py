from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from automation.review_dispatcher_v1.dispatcher import discover_request, github_get
from automation.review_dispatcher_v1.model import ReviewContractError, require
from automation.review_dispatcher_v1.review import _check_auditor_upstream

SCHEMA = "MULTIVERSE_BUILD_ADMISSION_PREFLIGHT_v2"
READ_RETRYABLE = {429, 500, 502, 503, 504}


def authenticated_github_get(url: str):
    token = os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        return github_get(url)
    delays = (0.0, 0.5, 1.0, 2.0)
    last = None
    for i, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "multiverse-build-admission-preflight-v2",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in READ_RETRYABLE or i + 1 >= len(delays):
                raise
    raise last  # pragma: no cover


def run_preflight(
    *,
    repo: str,
    lane: str,
    head: str,
    expected_request_comment: int,
    expected_request_sha256: str,
    expected_main: str,
    expected_tree: str,
    fetch=authenticated_github_get,
) -> dict:
    job = discover_request(repo=repo, lane=lane, head=head, fetch=fetch)
    require(job["request_comment"] == expected_request_comment, "ADMISSION_REQUEST_COMMENT_DRIFT")
    require(job["request_sha256"] == expected_request_sha256, "ADMISSION_REQUEST_SHA256_DRIFT")
    require(job["main"] == expected_main, "ADMISSION_MAIN_DRIFT")
    require(job["tree"] == expected_tree, "ADMISSION_TREE_DRIFT")
    require(job["head"] == head, "ADMISSION_HEAD_DRIFT")
    require(job["lane"] == lane, "ADMISSION_LANE_DRIFT")

    semantic_checks: dict[str, str] = {}
    semantic_findings: list[str] = []
    if lane == "AUDITOR":
        _check_auditor_upstream(job, fetch, semantic_checks, semantic_findings)
        if semantic_findings:
            raise ReviewContractError(
                "ADMISSION_AUDITOR_UPSTREAM_REVIEW_SEMANTICS:"
                + "|".join(semantic_findings)
            )

    return {
        "schema": SCHEMA,
        "verdict": "PASS",
        "repo": repo,
        "pr": job["pr"],
        "lane": lane,
        "head": head,
        "tree": job["tree"],
        "main": job["main"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "request_id": job["request_id"],
        "auditor_upstream_review_semantics": "PASS" if lane == "AUDITOR" else "NOT_APPLICABLE",
        "publication_attempted": False,
        "owner_build_consumed": False,
        "runtime": "OFF",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--lane", required=True, choices=("LAB", "AUDITOR"))
    parser.add_argument("--head", required=True)
    parser.add_argument("--expected-request-comment", required=True, type=int)
    parser.add_argument("--expected-request-sha256", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--output", default="build_admission_preflight_v2.json")
    args = parser.parse_args()
    receipt = run_preflight(
        repo=args.repo,
        lane=args.lane,
        head=args.head,
        expected_request_comment=args.expected_request_comment,
        expected_request_sha256=args.expected_request_sha256,
        expected_main=args.expected_main,
        expected_tree=args.expected_tree,
    )
    Path(args.output).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
