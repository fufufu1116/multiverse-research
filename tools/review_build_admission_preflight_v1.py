from __future__ import annotations

import argparse
import json
from pathlib import Path

from automation.review_dispatcher_v1.dispatcher import discover_request
from automation.review_dispatcher_v1.model import require

SCHEMA = "MULTIVERSE_BUILD_ADMISSION_PREFLIGHT_v1"


def run_preflight(*, repo: str, lane: str, head: str, expected_request_comment: int,
                  expected_request_sha256: str, expected_main: str,
                  expected_tree: str) -> dict:
    job = discover_request(repo=repo, lane=lane, head=head)
    require(job["request_comment"] == expected_request_comment,
            "ADMISSION_REQUEST_COMMENT_DRIFT")
    require(job["request_sha256"] == expected_request_sha256,
            "ADMISSION_REQUEST_SHA256_DRIFT")
    require(job["main"] == expected_main, "ADMISSION_MAIN_DRIFT")
    require(job["tree"] == expected_tree, "ADMISSION_TREE_DRIFT")
    require(job["head"] == head, "ADMISSION_HEAD_DRIFT")
    require(job["lane"] == lane, "ADMISSION_LANE_DRIFT")
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
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--lane", required=True, choices=("LAB", "AUDITOR"))
    p.add_argument("--head", required=True)
    p.add_argument("--expected-request-comment", required=True, type=int)
    p.add_argument("--expected-request-sha256", required=True)
    p.add_argument("--expected-main", required=True)
    p.add_argument("--expected-tree", required=True)
    p.add_argument("--output", default="build_admission_preflight.json")
    a = p.parse_args()
    receipt = run_preflight(
        repo=a.repo, lane=a.lane, head=a.head,
        expected_request_comment=a.expected_request_comment,
        expected_request_sha256=a.expected_request_sha256,
        expected_main=a.expected_main, expected_tree=a.expected_tree,
    )
    Path(a.output).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
