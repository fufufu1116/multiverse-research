from __future__ import annotations

from typing import Any, Callable

from automation.review_dispatcher_v1 import review as _review
from automation.review_dispatcher_v1.main_drift_runtime_v1 import (
    assert_job_main_binding_fresh,
    assert_job_request_latest_across_snapshots,
)


def _fresh_binding(
    job: dict[str, Any],
    fetch: Callable[[str], Any],
    checks: dict[str, str],
    findings: list[str],
) -> None:
    repo = job["repo"]
    pr_number = job["pr"]
    head = job["head"]
    tree = job["tree"]
    base = job["base"]

    pr_raw = fetch(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    )
    commit_raw = fetch(
        f"https://api.github.com/repos/{repo}/commits/{head}"
    )
    main_raw = fetch(
        f"https://api.github.com/repos/{repo}/branches/main"
    )

    def check(name: str, condition: bool, detail: str) -> None:
        if condition:
            checks[name] = "PASS"
        else:
            checks[name] = "FIX_REQUIRED"
            findings.append(f"{name}: {detail}")

    try:
        pr = _review.github_full_pr_binding(
            pr_raw,
            expected_number=pr_number,
            expected_head=head,
        )
        fresh_tree = _review.github_commit_tree_sha(commit_raw)
        fresh_main = _review.github_branch_commit_sha(main_raw)
    except _review.ReviewContractError as exc:
        checks["fresh_binding_contract"] = "FIX_REQUIRED"
        findings.append(f"fresh_binding_contract: {exc}")
        return

    checks["fresh_binding_contract"] = "PASS"
    check("fresh_pr_head", pr["head_sha"] == head, repr(pr["head_sha"]))
    check("fresh_pr_tree", fresh_tree == tree, repr(fresh_tree))
    check("fresh_pr_base", pr["base_sha"] == base, repr(pr["base_sha"]))
    check("pr_open", pr["state"] == "open", repr(pr["state"]))
    check("pr_draft", pr["draft"] is True, repr(pr["draft"]))
    check("pr_unmerged", pr["merged"] is False, repr(pr["merged"]))

    try:
        binding = assert_job_main_binding_fresh(
            job,
            live_main=fresh_main,
            fetch=fetch,
        )
    except _review.ReviewContractError as exc:
        checks["fresh_main_binding"] = "FIX_REQUIRED"
        findings.append(f"fresh_main_binding: {exc}")
    else:
        checks["fresh_main_binding"] = "PASS"
        checks[f"fresh_main_binding_mode:{binding['mode']}"] = "PASS"

    try:
        comments = _review.fetch_all_pages(
            fetch,
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
        )
        assert_job_request_latest_across_snapshots(
            job,
            comments,
            live_main=fresh_main,
        )
    except _review.ReviewContractError as exc:
        checks["fresh_request_authority"] = "FIX_REQUIRED"
        findings.append(f"fresh_request_authority: {exc}")
    else:
        checks["fresh_request_authority"] = "PASS"


_review._fresh_binding = _fresh_binding


def main() -> int:
    return _review.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except _review.ReviewContractError as exc:
        print(f"REVIEW_FIX_REQUIRED:{exc}")
        raise SystemExit(1)
