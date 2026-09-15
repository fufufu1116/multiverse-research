from __future__ import annotations

import argparse
import json
from typing import Any

from automation.review_dispatcher_v1.dispatcher import (
    _discover_main_sha,
    _discover_tree_sha,
    github_get,
)
from automation.review_dispatcher_v1.model import (
    ReviewContractError,
    fetch_all_pages,
    github_full_pr_binding,
    require,
    required_positive_int,
)

SCHEMA = "MULTIVERSE_REVIEW_TRANSPORT_PREFLIGHT_v1"
READY = "TRANSPORT_READY_NONAUTHORITY"
CARRIER = "REVIEW_TRANSPORT_REQUIRED"
AMBIGUOUS = "AMBIGUOUS_PR_FAIL_CLOSED"
INVALID = "TRANSPORT_INVALID_FAIL_CLOSED"


def preflight(*, repo: str, head: str, fetch=github_get) -> dict[str, Any]:
    require(bool(repo), "REPO_REQUIRED")
    require(len(head) == 40 and all(c in "0123456789abcdef" for c in head), "HEAD_40_HEX")
    try:
        tree = _discover_tree_sha(repo, head, fetch=fetch)
        main = _discover_main_sha(repo, fetch=fetch)
        pulls = fetch_all_pages(fetch, f"https://api.github.com/repos/{repo}/commits/{head}/pulls")
    except ReviewContractError:
        raise
    except Exception as exc:
        raise ReviewContractError(f"FRESH_READ_FAILED:{type(exc).__name__}") from exc

    exact: list[dict[str, Any]] = []
    for item in pulls:
        require(isinstance(item, dict), "PR_SUMMARY_ITEM_OBJECT")
        item_head = item.get("head")
        if item.get("state") == "open" and isinstance(item_head, dict) and item_head.get("sha") == head:
            exact.append(item)

    base = {
        "schema": SCHEMA, "repo": repo, "head": head, "tree": tree, "main": main,
        "package_quality_inferred": False, "authority_created": False,
        "owner_marker_created": False, "runtime_authority": False,
    }
    if len(exact) == 0:
        return {**base, "state": CARRIER, "exact_open_pr_count": 0}
    if len(exact) != 1:
        return {**base, "state": AMBIGUOUS, "exact_open_pr_count": len(exact)}

    summary = exact[0]
    pr_number = required_positive_int(summary.get("number"), "PR_SUMMARY_NUMBER")
    full_pr = github_full_pr_binding(fetch(f"https://api.github.com/repos/{repo}/pulls/{pr_number}"), expected_number=pr_number, expected_head=head)
    return {**base, "state": READY, "exact_open_pr_count": 1, "pr": pr_number,
            "branch": full_pr["head_ref"], "base": full_pr["base_sha"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="fufufu1116/multiverse-research")
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(repo=args.repo, head=args.head), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReviewContractError as exc:
        print(json.dumps({"schema": SCHEMA, "state": INVALID, "reason": str(exc),
                          "authority_created": False, "owner_marker_created": False,
                          "runtime_authority": False}, sort_keys=True))
        raise SystemExit(1)
